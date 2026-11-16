"""
Calibra um AcquaSensor de ORP (AS-TO, família ORPT) com solução padrão.

Uso:
    python acquasensor_calibrar_orp.py --porta COM3 --endereco 4
    python acquasensor_calibrar_orp.py --porta COM3 --endereco 4 --solucao 225
    python acquasensor_calibrar_orp.py --porta COM3 --endereco 4 --restaurar-fabrica

Um ponto só (registro 0x110B, função 16): o comando 0x0100 seguido do valor
da solução em mV, como float em 2 registros. Para 225 mV:
    [0x0100, 0x0000, 0x6143]
Fábrica: [0x0000].
"""
import argparse
import sys
import time

import acquanativa as an

REG_CAL = 0x110B
STATUS_TEXT = {0: "não calibrado", 1: "calibrado"}
STABLE_MV = 2.0          # variação máxima (mV) para "estável"


def read_status(client, address):
    regs = an.read_retry(client, address, REG_CAL, 1)
    if regs is None:
        return "não foi possível ler"
    value = an.swap16(regs[0])
    return STATUS_TEXT.get(value, f"código {value}")


def read_orp(client, address):
    values = an.read_acquasensor(client, address, "ORPT")
    return values[1][1] if values else None     # [temperatura, ORP]


def main():
    p = argparse.ArgumentParser(description="Calibração do AcquaSensor de ORP")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=4, help="padrão de fábrica: 4")
    p.add_argument("--solucao", type=float, default=225.0,
                   help="valor da solução padrão em mV (padrão 225)")
    p.add_argument("--restaurar-fabrica", action="store_true")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=9600)
    try:
        if an.identify_acquasensor(client, args.endereco) != "ORPT":
            sys.exit(f"O endereço {args.endereco} não é um sensor de ORP.")
        print(f"Sensor de ORP no endereço {args.endereco}. "
              f"Estado atual: {read_status(client, args.endereco)}")

        if args.restaurar_fabrica:
            payload = [0x0000]
            if not an.ask("Apagar a calibração e voltar à de fábrica? [s/N] "):
                return
        else:
            payload = [0x0100] + an.regs_from_float(args.solucao)
            input(f"Mergulhe o eletrodo na solução de {args.solucao:g} mV e tecle Enter...")
            if not an.wait_until_stable(lambda: read_orp(client, args.endereco),
                                        STABLE_MV, "mV"):
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
