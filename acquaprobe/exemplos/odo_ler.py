"""
Lê a sonda de oxigênio dissolvido óptico (ODO) e mostra os valores continuamente.

Uso:
    python odo_ler.py --porta COM3
    python odo_ler.py --porta /dev/ttyUSB0 --endereco 1 --csv leituras.csv

Comunicação de fábrica: 9600 baud, 8N1, endereço 1, função 03.

Bloco de leitura 0x2600, 6 registros = 3 floats (mesmo formato DCBA dos
AcquaSensors): temperatura °C, saturação de OD como FRAÇÃO (0,83 = 83 %) e OD
em mg/L.

⚠️ Não leia o registro 0x2E00 desta sonda: essa leitura é o comando que PARA a
medição.
"""
import argparse
import csv
import time

import acquanativa as an

REG_READ = 0x2600


def read_odo(client, device):
    """(temperatura °C, saturação %, OD mg/L) ou None."""
    regs = an.read_retry(client, device, REG_READ, 6)
    if regs is None:
        return None
    temp, fraction, mgl = an.floats_from_regs(regs)
    return temp, fraction * 100.0, mgl


def main():
    p = argparse.ArgumentParser(description="Leitura da sonda de OD óptico")
    p.add_argument("--porta", required=True, help="COM3, /dev/ttyUSB0, ...")
    p.add_argument("--endereco", type=int, default=1, help="padrão de fábrica: 1")
    p.add_argument("--intervalo", type=float, default=2.0)
    p.add_argument("--csv", help="grava as leituras neste arquivo CSV")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=9600)
    csv_file = writer = None
    if args.csv:
        csv_file = open(args.csv, "a", newline="", encoding="utf-8")
        writer = csv.writer(csv_file, delimiter=";")
        if csv_file.tell() == 0:
            writer.writerow(["data_hora", "temperatura (°C)", "OD saturação (%)", "OD (mg/L)"])
    try:
        while True:
            values = read_odo(client, args.endereco)
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if values is None:
                print(f"{stamp}  sem resposta")
            else:
                temp, sat, mgl = values
                print(f"{stamp}  Temperatura: {temp:.2f} °C   OD: {sat:.1f} %   OD: {mgl:.2f} mg/L")
                if writer:
                    writer.writerow([stamp, f"{temp:.3f}", f"{sat:.2f}", f"{mgl:.3f}"])
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
