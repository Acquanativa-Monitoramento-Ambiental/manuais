"""
Lê a sonda multiparâmetros AcquaProbe-AQ e mostra os valores continuamente.

Uso:
    python acquaprobe_ler.py --porta COM3
    python acquaprobe_ler.py --porta /dev/ttyUSB0 --endereco 1 --csv leituras.csv

Comunicação de fábrica: 57600 baud, 8N1, endereço 1.

Antes da primeira leitura a sonda precisa ser ativada: escrever 0xFDFD nos
registros HR 21 e HR 22. O script faz isso ao conectar e de novo sempre que a
sonda volta de uma falha de comunicação (ela pode ter reiniciado).
"""
import argparse
import csv
import sys
import time

import acquanativa as an

BAUDRATE = 57600
ACTIVATION = 0xFDFD

# HR 0-19: dez floats, dois registros cada.
CHANNELS = [
    ("OD saturação", "%"),         # HR 0-1
    ("OD", "mg/L"),                # HR 2-3
    ("Temperatura", "°C"),         # HR 4-5
    ("pH", ""),                    # HR 6-7
    ("ORP", "mV"),                 # HR 8-9
    ("Condutividade", "µS/cm"),    # HR 10-11
    ("TDS", "mg/L"),               # HR 12-13
    ("Salinidade", "PSU"),         # HR 14-15
    ("Gravidade específica", ""),  # HR 16-17
    ("Turbidez", "NTU"),           # HR 18-19
]


def activate(client, device):
    return an.write_regs(client, device, 21, [ACTIVATION, ACTIVATION])


def read_probe(client, device):
    """Lista de 10 floats, ou None. A sonda às vezes perde 2-3 quadros seguidos."""
    regs = an.read_retry(client, device, 0, 20, attempts=4, pause=0.3)
    return an.floats_from_regs(regs) if regs else None


def main():
    p = argparse.ArgumentParser(description="Leitura da AcquaProbe-AQ")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=1)
    p.add_argument("--intervalo", type=float, default=2.0)
    p.add_argument("--csv", help="grava as leituras neste arquivo CSV")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=BAUDRATE, timeout=1.5)
    if not activate(client, args.endereco):
        client.close()
        sys.exit("Falha na escrita de ativação (HR 21/22). Confira a ligação, "
                 "a alimentação (12-24 Vdc) e os fios A/B.")
    print("Sonda ativada. Aguardando os sensores (5 s)...")
    time.sleep(5)

    writer = None
    csv_file = None
    if args.csv:
        csv_file = open(args.csv, "a", newline="", encoding="utf-8")
        writer = csv.writer(csv_file, delimiter=";")
        if csv_file.tell() == 0:
            writer.writerow(["data_hora"] + [f"{n} ({u})" if u else n for n, u in CHANNELS])

    was_offline = False
    try:
        while True:
            values = read_probe(client, args.endereco)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if values is None:
                print(f"{stamp}  sem resposta")
                was_offline = True
            else:
                if was_offline:
                    activate(client, args.endereco)
                    was_offline = False
                print(f"\n{stamp}")
                for (name, unit), value in zip(CHANNELS, values):
                    print(f"  {name:22s} {value:12.3f} {unit}")
                if writer:
                    writer.writerow([stamp] + [f"{v:.4f}" for v in values])
                    csv_file.flush()
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        client.close()
        if csv_file:
            csv_file.close()


if __name__ == "__main__":
    main()
