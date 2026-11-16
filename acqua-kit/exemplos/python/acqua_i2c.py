"""
Fala com os módulos I²C Acquanativa (ACQUA-OD, ACQUA-pH, ACQUA-ORP; módulos
AcquaKit, firmware 1.1) a partir de um Raspberry Pi ou outro Linux com I²C.

Uso:
    python3 acqua_i2c.py --procurar
    python3 acqua_i2c.py --endereco 64 Info
    python3 acqua_i2c.py --endereco 64 Cal,mid
    python3 acqua_i2c.py --endereco 64 --ler                (1 leitura por segundo)
    python3 acqua_i2c.py --endereco 32 --ler --temperatura 23.5 --csv od.csv
    python3 acqua_i2c.py --endereco 96                      (terminal interativo)

Endereços de fábrica: ACQUA-OD 32, ACQUA-pH 64, ACQUA-ORP 96.

Preparação do Raspberry Pi:
  1. sudo raspi-config > Interface Options > I2C > Enable, e reinicie.
  2. pip install -r requirements.txt   (instala o smbus2)
  3. Ligação: J1 pino 1 VCC -> 3V3 (pino 1 do Pi), pino 2 SCL -> GPIO3/SCL
     (pino 5), pino 3 SDA -> GPIO2/SDA (pino 3), pino 4 GND -> GND (pino 6).
     O Pi já tem pull-ups em SDA e SCL.
  ⚠️ O ACQUA-ORP precisa de 5 V: com o Pi, use um conversor de nível de I²C.
     Nunca ligue 5 V direto nos pinos de I²C do Pi.

Como funciona (o mesmo em qualquer mestre I²C):
  1. escreva o texto do comando no endereço do módulo;
  2. espere 450 ms;
  3. leia 32 bytes; a resposta termina no primeiro byte 0.
  Respostas: "*OK" aceito, "*ER" recusado, ou o dado pedido.
"""
import argparse
import csv
import sys
import time

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    sys.exit("Falta o smbus2: pip install -r requirements.txt")

WAIT_S = 0.45      # tempo de processamento do módulo
FACTORY = {32: "ACQUA-OD", 64: "ACQUA-pH", 96: "ACQUA-ORP"}


def send(bus, address, command):
    """Envia um comando e devolve a resposta em texto ('' se vier vazia)."""
    bus.i2c_rdwr(i2c_msg.write(address, command.encode("ascii")))
    time.sleep(WAIT_S)
    msg = i2c_msg.read(address, 32)
    bus.i2c_rdwr(msg)
    data = bytes(msg)
    return data.split(b"\0", 1)[0].decode("ascii", "replace")


def find(bus):
    found = []
    for address in range(8, 120):
        try:
            info = send(bus, address, "Info")
        except OSError:
            continue    # ninguém neste endereço
        found.append(address)
        print(f"  endereço {address}: {info or '(não respondeu ao Info)'}")
    if not found:
        print("  nenhum módulo. Confira VCC, GND, SDA e SCL e se o I²C está ativado.")
    return found


def read_loop(bus, address, temperature, csv_path):
    """Lê uma vez por segundo até Ctrl+C."""
    info = send(bus, address, "Info")
    print(f"{info}  (Ctrl+C encerra)")
    kind = info.split(",", 1)[0].upper()
    if temperature is not None and kind in ("OD", "PH"):
        command = f"RT,{temperature:.1f}"
    else:
        command = "R"

    f = writer = None
    if csv_path:
        f = open(csv_path, "a", newline="", encoding="utf-8")
        writer = csv.writer(f, delimiter=";")
    try:
        while True:
            start = time.monotonic()
            answer = send(bus, address, command)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{stamp}  {answer}")
            if f:
                writer.writerow([stamp] + answer.split(","))
                f.flush()
            time.sleep(max(0.0, 1.0 - (time.monotonic() - start)))
    except KeyboardInterrupt:
        pass
    finally:
        if f:
            f.close()


def terminal(bus, address):
    print(f"Módulo no endereço {address}: {send(bus, address, 'Info')}")
    print("Digite um comando (ex.: R, Cal,?, Status). Linha vazia encerra.")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        if len(line) > 31:
            print("comando longo demais (máximo 31 caracteres)")
            continue
        print(send(bus, address, line) or "(resposta vazia: leia de novo ou confira o endereço)")
        low = line.lower()
        if low.startswith("i2c,") and low != "i2c,?" and low[4:].isdigit():
            address = int(low[4:])     # o módulo já responde no endereço novo
            print(f"agora no endereço {address}")


def main():
    p = argparse.ArgumentParser(description="Módulos I²C Acquanativa (ACQUA-OD, -pH, -ORP)")
    p.add_argument("comando", nargs="?", help="comando a enviar (ex.: Info, R, Cal,mid)")
    p.add_argument("--barramento", type=int, default=1, help="nº do barramento I²C (Pi: 1)")
    p.add_argument("--endereco", type=int, help="endereço do módulo, em decimal")
    p.add_argument("--procurar", action="store_true", help="procura módulos de 8 a 119")
    p.add_argument("--ler", action="store_true", help="lê uma vez por segundo")
    p.add_argument("--temperatura", type=float, help="temperatura da água (°C) para OD e pH")
    p.add_argument("--csv", help="grava as leituras neste arquivo")
    args = p.parse_args()

    with SMBus(args.barramento) as bus:
        if args.procurar or args.endereco is None:
            find(bus)
            return
        try:
            if args.ler:
                read_loop(bus, args.endereco, args.temperatura, args.csv)
            elif args.comando:
                print(send(bus, args.endereco, args.comando))
            else:
                terminal(bus, args.endereco)
        except OSError:
            name = FACTORY.get(args.endereco, "módulo")
            sys.exit(f"Nada respondeu no endereço {args.endereco} ({name}). "
                     "Rode com --procurar.")


if __name__ == "__main__":
    main()
