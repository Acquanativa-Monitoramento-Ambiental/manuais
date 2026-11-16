"""
Calibra um AcquaSensor de oxigênio dissolvido (AS-TD, família ODT0).

Uso:
    python acquasensor_calibrar_od.py --porta COM3 --endereco 2 --ponto ar
    python acquasensor_calibrar_od.py --porta COM3 --endereco 2 --ponto zero
    python acquasensor_calibrar_od.py --porta COM3 --endereco 2 --restaurar-fabrica

Pontos (registro 0x1103, função 16):
    ar    0x0100  sensor seco, no ar, fora do sol e parado (100 % de saturação)
    zero  0x0200  sensor em solução de oxigênio zero (ex.: sulfito de sódio)
    fábrica 0x0000

Na maioria dos casos basta o ponto "ar". Faça o "zero" só se precisar de
exatidão em concentrações muito baixas, e sempre depois do "ar".
"""
import argparse
import sys
import time

import acquanativa as an

REG_CAL = 0x1103
POINTS = {"ar": (0x0100, "Deixe o sensor limpo e seco, no ar, protegido de sol e vento."),
          "zero": (0x0200, "Mergulhe o sensor na solução de oxigênio zero.")}
STATUS_TEXT = {0: "não calibrado", 1: "calibrado com ar atmosférico", 2: "calibrado"}
STABLE_SAT = 0.5         # variação máxima de saturação (%) para "estável"


def read_status(client, address):
    regs = an.read_retry(client, address, REG_CAL, 1)
    if regs is None:
        return "não foi possível ler"
    value = an.swap16(regs[0])
    return STATUS_TEXT.get(value, f"código {value}")


def read_saturation(client, address):
    values = an.read_acquasensor(client, address, "ODT0")
    return values[1][1] if values else None     # [temperatura, OD %, OD mg/L]


def main():
    p = argparse.ArgumentParser(description="Calibração do AcquaSensor de OD")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=2, help="padrão de fábrica: 2")
    p.add_argument("--ponto", choices=POINTS)
    p.add_argument("--restaurar-fabrica", action="store_true")
    args = p.parse_args()
    if not args.ponto and not args.restaurar_fabrica:
        p.error("informe --ponto ar|zero ou --restaurar-fabrica")

    client = an.connect(args.porta, baudrate=9600)
    try:
        if an.identify_acquasensor(client, args.endereco) != "ODT0":
            sys.exit(f"O endereço {args.endereco} não é um sensor de OD.")
        print(f"Sensor de OD no endereço {args.endereco}. "
              f"Estado atual: {read_status(client, args.endereco)}")

        if args.restaurar_fabrica:
            command = 0x0000
            if not an.ask("Apagar a calibração e voltar à de fábrica? [s/N] "):
                return
        else:
            command, instruction = POINTS[args.ponto]
            input(f"{instruction}\nTecle Enter para começar a acompanhar a leitura...")
            if not an.wait_until_stable(lambda: read_saturation(client, args.endereco),
                                        STABLE_SAT, "%"):
                print("Cancelado, nada foi enviado.")
                return

        if not an.write_regs(client, args.endereco, REG_CAL, [command]):
            sys.exit("ERRO: o sensor não confirmou o comando.")
        time.sleep(1.0)
        print(f"Enviado. Estado do sensor: {read_status(client, args.endereco)}")
    except KeyboardInterrupt:
        print("\nCancelado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
