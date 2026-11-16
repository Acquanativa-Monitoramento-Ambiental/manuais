"""
Lê um AcquaSensor (qualquer família) e mostra os valores continuamente.

Uso:
    python acquasensor_ler.py --porta COM3 --endereco 3
    python acquasensor_ler.py --porta /dev/ttyUSB0          (sensor sozinho no cabo)

Sem --endereco, o script pergunta o endereço ao sensor pelo endereço de
difusão 255. Isso só funciona com UM sensor ligado ao conversor.

Ctrl+C encerra.
"""
import argparse
import sys
import time

import acquanativa as an


def find_address(client):
    """Pergunta o endereço ao único sensor do barramento (difusão 255)."""
    regs = an.read_retry(client, an.BROADCAST, an.REG_ADDRESS, 1)
    return an.swap16(regs[0]) if regs else None


def main():
    p = argparse.ArgumentParser(description="Leitura de um AcquaSensor")
    p.add_argument("--porta", required=True, help="COM3, /dev/ttyUSB0, ...")
    p.add_argument("--endereco", type=int, help="endereço Modbus (1-247)")
    p.add_argument("--intervalo", type=float, default=2.0,
                   help="segundos entre leituras (padrão 2)")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=9600)

    address = args.endereco
    if address is None:
        address = find_address(client)
        if address is None:
            sys.exit("Nenhum sensor respondeu no endereço 255. Informe --endereco.")
        print(f"Sensor encontrado no endereço {address}")

    family = an.identify_acquasensor(client, address)
    if family is None:
        sys.exit(f"Nada respondeu no endereço {address}, ou a família não é conhecida.")
    fam = an.ACQUASENSOR_FAMILIES[family]
    print(f"Família {family} — {fam['product']} — endereço {address}\n")

    try:
        while True:
            values = an.read_acquasensor(client, address, family)
            stamp = time.strftime("%H:%M:%S")
            if values is None:
                print(f"{stamp}  sem resposta")
            else:
                text = "   ".join(f"{label}: {value:.2f} {unit}".rstrip()
                                  for label, value, unit in values)
                print(f"{stamp}  {text}")
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
