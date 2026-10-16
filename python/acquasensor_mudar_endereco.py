"""
Muda o endereço Modbus de um AcquaSensor.

Necessário quando dois sensores da mesma família vão ficar no mesmo cabo:
cada um precisa de um endereço diferente.

Uso:
    python acquasensor_mudar_endereco.py --porta COM3 --atual 3 --novo 13

Dica: ligue SÓ o sensor que vai mudar de endereço ao conversor. Se não souber
o endereço atual, use --atual 255 (difusão) com ele sozinho no cabo.
"""
import argparse
import sys
import time

import acquanativa as an


def main():
    p = argparse.ArgumentParser(description="Muda o endereço Modbus de um AcquaSensor")
    p.add_argument("--porta", required=True)
    p.add_argument("--atual", type=int, required=True, help="endereço atual (ou 255)")
    p.add_argument("--novo", type=int, required=True, help="novo endereço (1-247)")
    args = p.parse_args()

    if not 1 <= args.novo <= 247:
        sys.exit("O novo endereço deve estar entre 1 e 247.")

    client = an.connect(args.porta, baudrate=9600)
    try:
        family = an.identify_acquasensor(client, args.atual)
        if family is None and args.atual != an.BROADCAST:
            sys.exit(f"Nenhum AcquaSensor respondeu no endereço {args.atual}.")

        if an.read_regs(client, args.novo, an.REG_ADDRESS, 1) is not None:
            sys.exit(f"Já existe um equipamento respondendo no endereço {args.novo}. "
                     "Escolha outro.")

        print(f"Mudando {family or 'sensor'} de {args.atual} para {args.novo} ...")
        # O endereço vai com os bytes invertidos (3 -> 0x0300), função 16.
        # O sensor pode responder já com o novo endereço, então não confiamos
        # só na confirmação da escrita: conferimos lendo no endereço novo.
        an.write_regs(client, args.atual, an.REG_ADDRESS, [an.swap16(args.novo)])
        time.sleep(1.0)

        regs = an.read_retry(client, args.novo, an.REG_ADDRESS, 1)
        if regs is not None and an.swap16(regs[0]) == args.novo:
            print(f"OK — o sensor agora responde no endereço {args.novo}.")
        else:
            sys.exit("Não foi possível confirmar o novo endereço. "
                     "Rode acquasensor_procurar.py para ver onde o sensor está.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
