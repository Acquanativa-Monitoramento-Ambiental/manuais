"""
Calibra um AcquaSensor de pH (AS-TP, família PHT0) com soluções tampão.

Uso:
    python acquasensor_calibrar_ph.py --porta COM3 --endereco 3
    python acquasensor_calibrar_ph.py --porta COM3 --endereco 3 --pontos 7,4
    python acquasensor_calibrar_ph.py --porta COM3 --endereco 3 --restaurar-fabrica

Como funciona a calibração deste sensor:
  * No instante em que recebe o comando, o sensor guarda a tensão do eletrodo
    como sendo a do tampão (pH 7, 4 ou 10). Por isso a leitura precisa estar
    ESTÁVEL antes de enviar — o script espera por isso.
  * Calibre sempre o pH 7 primeiro, depois o 4 e, se quiser, o 10.
  * Comandos (registro 0x1107, função 16):
        0x0100 = pH 7    0x0200 = pH 4    0x0300 = pH 10    0x0000 = fábrica
  * A calibração fica gravada no sensor; não precisa repetir ao religar.
"""
import argparse
import sys
import time

import acquanativa as an

REG_CAL = 0x1107         # comando de calibração / estado da calibração

COMMANDS = {7: 0x0100, 4: 0x0200, 10: 0x0300}
STATUS_TEXT = {0: "não calibrado", 1: "só pH 7 calibrado",
               2: "pH 7 e pH 4 calibrados", 3: "calibrado (pH 7, 4 e 10)"}

STABLE_PH = 0.02         # variação máxima de pH (em 10 leituras) para "estável"


def read_status(client, address):
    """Estado da calibração guardado no sensor (registro 0x1107, bytes invertidos)."""
    regs = an.read_retry(client, address, REG_CAL, 1)
    if regs is None:
        return "não foi possível ler"
    value = an.swap16(regs[0])
    return STATUS_TEXT.get(value, f"código {value}")


def read_ph(client, address):
    values = an.read_acquasensor(client, address, "PHT0")
    return values[1][1] if values else None     # [temperatura, pH]


def calibrate_point(client, address, buffer_ph):
    print(f"\n── Ponto pH {buffer_ph} ─────────────────────────────")
    input(f"  Lave o eletrodo com água destilada, mergulhe no tampão pH {buffer_ph} "
          "e tecle Enter...")
    if not an.wait_until_stable(lambda: read_ph(client, address), STABLE_PH, "pH"):
        print("  Ponto pulado.")
        return False
    if not an.write_regs(client, address, REG_CAL, [COMMANDS[buffer_ph]]):
        print("  ERRO: o sensor não confirmou o comando.")
        return False
    time.sleep(1.0)
    print(f"  Enviado. Estado do sensor: {read_status(client, address)}")
    return True


def main():
    p = argparse.ArgumentParser(description="Calibração do AcquaSensor de pH")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=3, help="padrão de fábrica: 3")
    p.add_argument("--pontos", default="7,4,10",
                   help="tampões a usar, em ordem (padrão 7,4,10)")
    p.add_argument("--restaurar-fabrica", action="store_true",
                   help="apaga a calibração do sensor")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=9600)
    try:
        family = an.identify_acquasensor(client, args.endereco)
        if family != "PHT0":
            sys.exit(f"O equipamento no endereço {args.endereco} não é um sensor "
                     f"de pH (encontrado: {family}).")
        print(f"Sensor de pH no endereço {args.endereco}. "
              f"Estado atual: {read_status(client, args.endereco)}")

        if args.restaurar_fabrica:
            if an.ask("Apagar a calibração e voltar à de fábrica? [s/N] "):
                ok = an.write_regs(client, args.endereco, REG_CAL, [0x0000])
                time.sleep(1.0)
                print("Feito." if ok else "ERRO: sem confirmação do sensor.",
                      "Estado:", read_status(client, args.endereco))
            return

        points = [int(x) for x in args.pontos.split(",")]
        if any(pt not in COMMANDS for pt in points):
            sys.exit("Pontos válidos: 7, 4 e 10.")
        if points[0] != 7:
            sys.exit("A calibração deve começar pelo pH 7.")

        for buffer_ph in points:
            calibrate_point(client, args.endereco, buffer_ph)

        print(f"\nCalibração concluída. Estado final: {read_status(client, args.endereco)}")
    except KeyboardInterrupt:
        print("\nCancelado. Os pontos já enviados continuam gravados no sensor.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
