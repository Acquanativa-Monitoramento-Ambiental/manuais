"""
Calibra um AcquaSensor de turbidez (AS-TT, família TURB) com padrões de formazina.

Uso:
    python acquasensor_calibrar_turb.py --porta COM3 --endereco 6 --ponto alto --padrao 1000
    python acquasensor_calibrar_turb.py --porta COM3 --endereco 6 --ponto baixo --padrao 0
    python acquasensor_calibrar_turb.py --porta COM3 --endereco 6 --restaurar-fabrica

Pontos (registro 0x110C, função 16). O valor do padrão vai em NTU, como float
em 2 registros logo depois do comando:
    alto   [0x0100, float]   padrão de 100 ou 1000 NTU
    baixo  [0x0200, float]   padrão de 0 ou 100 NTU
    fábrica [0x0000]

Faça primeiro o ponto ALTO e depois o BAIXO.
"""
import argparse
import sys
import time

import acquanativa as an

REG_CAL = 0x110C
POINTS = {"alto": 0x0100, "baixo": 0x0200}
STATUS_TEXT = {0: "não calibrado", 1: "ponto alto calibrado",
               2: "ponto baixo calibrado", 3: "pontos alto e baixo calibrados"}
STABLE_FRACTION = 0.02   # variação máxima: 2 % do padrão (mínimo 0,5 NTU)


def read_status(client, address):
    regs = an.read_retry(client, address, REG_CAL, 1)
    if regs is None:
        return "não foi possível ler"
    value = an.swap16(regs[0])
    return STATUS_TEXT.get(value, f"código {value}")


def read_turb(client, address):
    values = an.read_acquasensor(client, address, "TURB")
    return values[1][1] if values else None     # [temperatura, turbidez]


def main():
    p = argparse.ArgumentParser(description="Calibração do AcquaSensor de turbidez")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, required=True, help="endereço Modbus do sensor")
    p.add_argument("--ponto", choices=POINTS)
    p.add_argument("--padrao", type=float, help="valor do padrão em NTU")
    p.add_argument("--restaurar-fabrica", action="store_true")
    args = p.parse_args()
    if not args.ponto and not args.restaurar_fabrica:
        p.error("informe --ponto alto|baixo ou --restaurar-fabrica")
    if args.ponto and args.padrao is None:
        p.error("informe --padrao (NTU)")

    client = an.connect(args.porta, baudrate=9600)
    try:
        if an.identify_acquasensor(client, args.endereco) != "TURB":
            sys.exit(f"O endereço {args.endereco} não é um sensor de turbidez.")
        print(f"Sensor de turbidez no endereço {args.endereco}. "
              f"Estado atual: {read_status(client, args.endereco)}")

        if args.restaurar_fabrica:
            payload = [0x0000]
            if not an.ask("Apagar a calibração e voltar à de fábrica? [s/N] "):
                return
        else:
            # O AcquaSmart envia 0,1 NTU no lugar de 0: fazemos o mesmo.
            value = args.padrao if args.padrao > 0 else 0.1
            payload = [POINTS[args.ponto]] + an.regs_from_float(value)
            input(f"Coloque o sensor no padrão de {args.padrao:g} NTU (sem bolhas na "
                  "janela óptica) e tecle Enter...")
            limit = max(0.5, args.padrao * STABLE_FRACTION)
            if not an.wait_until_stable(lambda: read_turb(client, args.endereco),
                                        limit, "NTU"):
                print("Cancelado, nada foi enviado.")
                return

        if not an.write_regs(client, args.endereco, REG_CAL, payload):
            sys.exit("ERRO: o sensor não confirmou o comando.")
        time.sleep(1.0)
        print(f"Enviado. Estado do sensor: {read_status(client, args.endereco)}")
    except KeyboardInterrupt:
        print("\nCancelado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
