"""
Calibra um AcquaSensor de condutividade (AS-TE / AS-TE4P, família ECT0).

Uso:
    python acquasensor_calibrar_ec.py --porta COM3 --endereco 5 --modo seco
    python acquasensor_calibrar_ec.py --porta COM3 --endereco 5 --modo unico --padrao 1413
    python acquasensor_calibrar_ec.py --porta COM3 --endereco 5 --modo baixo --padrao 84
    python acquasensor_calibrar_ec.py --porta COM3 --endereco 5 --modo alto  --padrao 12880
    python acquasensor_calibrar_ec.py --porta COM3 --endereco 5 --restaurar-fabrica

Modos (registro 0x110F, função 16). O valor do padrão vai em µS/cm, como
float em 2 registros logo depois do comando:
    seco   [0x0100]              eletrodo limpo e SECO, no ar
    unico  [0x0200, float]       calibração de um ponto
    baixo  [0x0300, float]       ponto baixo da calibração de dois pontos
    alto   [0x0400, float]       ponto alto da calibração de dois pontos
    fábrica [0x0000]

Sequência recomendada: seco -> (unico) ou (baixo -> alto).
Escolha padrões próximos da faixa de trabalho: água doce 84 / 1413 µS/cm,
água salobra ou salgada 12880 / 80000 µS/cm.
"""
import argparse
import sys
import time

import acquanativa as an

REG_CAL = 0x110F
MODES = {"seco": 0x0100, "unico": 0x0200, "baixo": 0x0300, "alto": 0x0400}
STATUS_TEXT = {0: "não calibrado", 1: "ponto único calibrado",
               2: "ponto baixo calibrado", 3: "ponto alto calibrado",
               4: "pontos baixo e alto calibrados"}
STABLE_FRACTION = 0.01   # variação máxima: 1 % do valor lido


def read_status(client, address):
    regs = an.read_retry(client, address, REG_CAL, 1)
    if regs is None:
        return "não foi possível ler"
    value = an.swap16(regs[0])
    return STATUS_TEXT.get(value, f"código {value}")


def read_ec(client, address):
    values = an.read_acquasensor(client, address, "ECT0")
    return values[1][1] if values else None     # [temperatura, EC, TDS, sal, GE]


def main():
    p = argparse.ArgumentParser(description="Calibração do AcquaSensor de condutividade")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=5, help="padrão de fábrica: 5")
    p.add_argument("--modo", choices=MODES)
    p.add_argument("--padrao", type=float, help="valor do padrão em µS/cm")
    p.add_argument("--restaurar-fabrica", action="store_true")
    args = p.parse_args()
    if not args.modo and not args.restaurar_fabrica:
        p.error("informe --modo ou --restaurar-fabrica")
    if args.modo in ("unico", "baixo", "alto") and not args.padrao:
        p.error("este modo precisa de --padrao (µS/cm)")

    client = an.connect(args.porta, baudrate=9600)
    try:
        if an.identify_acquasensor(client, args.endereco) != "ECT0":
            sys.exit(f"O endereço {args.endereco} não é um sensor de condutividade.")
        print(f"Sensor de condutividade no endereço {args.endereco}. "
              f"Estado atual: {read_status(client, args.endereco)}")

        if args.restaurar_fabrica:
            payload = [0x0000]
            if not an.ask("Apagar a calibração e voltar à de fábrica? [s/N] "):
                return
        elif args.modo == "seco":
            payload = [MODES["seco"]]
            input("Lave o eletrodo, seque bem e deixe-o no ar. Tecle Enter...")
        else:
            payload = [MODES[args.modo]] + an.regs_from_float(args.padrao)
            input(f"Mergulhe o eletrodo no padrão de {args.padrao:g} µS/cm "
                  "(sem bolhas nas placas) e tecle Enter...")
            limit = max(1.0, args.padrao * STABLE_FRACTION)
            if not an.wait_until_stable(lambda: read_ec(client, args.endereco),
                                        limit, "µS/cm"):
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
