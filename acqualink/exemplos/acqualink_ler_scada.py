"""
Lê as medições de um AcquaLink pela porta SCADA (Modbus RTU escravo, RS-485).

Uso:
    python acqualink_ler_scada.py --porta COM4
    python acqualink_ler_scada.py --porta /dev/ttyUSB1 --endereco 1 --baud 9600

Padrão de fábrica da porta SCADA: endereço 1, 9600 baud, 8N1 (ajustável no
painel em SCADA). Use os bornes SCADA do AcquaLink, não os do barramento de
sensores.

O script:
  1. lê a região de sistema (HR 201-259): versão do mapa, lista de sensores
     (manifesto) e ID do equipamento;
  2. para cada sensor do manifesto, lê o bloco dele e converte os valores.

Todos os valores são inteiros com sinal multiplicados por 100 (7,85 -> 785),
exceto CO2 (ppm, sem fator) e cor (Hazen, R, G, B: fator 10).
"""
import argparse
import sys
import time

import acquanativa as an

SUPPORTED_VERSION = 7

# código do tipo -> (nome, 1º registro do bloco, registros por sensor, canais)
# Cada canal é (nome, unidade, fator de escala).
X100, X10, X1 = 100, 10, 1
BLOCKS = {
    4:  ("OD",  1,   4, [("OD sat", "%", X100), ("OD", "mg/L", X100), ("Temp", "°C", X100)]),
    1:  ("pH",  33,  3, [("pH", "", X100), ("Temp", "°C", X100)]),
    2:  ("CE",  57,  6, [("CE", "µS/cm", X100), ("TDS", "ppm", X100),
                         ("Sal", "ppt", X100), ("GE", "", X100), ("Temp", "°C", X100)]),
    3:  ("ORP", 105, 3, [("ORP", "mV", X100), ("Temp", "°C", X100)]),
    5:  ("Turbidez", 129, 2, [("Turb", "NTU", X100)]),
    6:  ("Sonda", 145, 7, [("pH", "", X100), ("Temp", "°C", X100), ("OD sat", "%", X100),
                           ("OD", "mg/L", X100), ("CE", "µS/cm", X100), ("Turb", "NTU", X100)]),
    7:  ("Temperatura", 300, 2, [("Temp", "°C", X100)]),
    8:  ("NH4", 316, 5, [("NH4", "mg/L", X100), ("NH4+", "mg/L", X100),
                         ("pH", "", X100), ("Temp", "°C", X100)]),
    9:  ("CO2", 356, 4, [("CO2", "ppm", X1), ("Temp ar", "°C", X100), ("UR", "%", X100)]),
    10: ("Cor", 392, 5, [("Cor", "Hazen", X10), ("R", "", X10), ("G", "", X10), ("B", "", X10)]),
}


def signed(value):
    return value - 0x10000 if value & 0x8000 else value


def read_system(client, device):
    regs = an.read_retry(client, device, 201, 59)       # HR 201..259
    if regs is None:
        return None
    version, count = regs[0], regs[1]
    manifest = []
    for i in range(8):
        entry = regs[2 + i * 6: 8 + i * 6]
        kind, slot = entry[0], entry[1]
        if kind:
            manifest.append((kind, slot, an.text_from_regs(entry[2:6])))
    device_id = an.text_from_regs(regs[50:58])
    status = regs[58]
    return version, count, manifest, device_id, status


def read_sensor(client, device, kind, slot):
    name, base, stride, channels = BLOCKS[kind]
    regs = an.read_retry(client, device, base + slot * stride, stride)
    if regs is None:
        return None, None
    state = regs[0]
    values = [(label, signed(raw) / scale, unit)
              for (label, unit, scale), raw in zip(channels, regs[1:])]
    return state, values


def main():
    p = argparse.ArgumentParser(description="Leitura do AcquaLink via SCADA (Modbus RTU)")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=1)
    p.add_argument("--baud", type=int, default=9600)
    p.add_argument("--intervalo", type=float, default=5.0)
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=args.baud, timeout=1.0)
    try:
        system = read_system(client, args.endereco)
        if system is None:
            sys.exit("O AcquaLink não respondeu. Confira endereço, baud e os fios A/B "
                     "da porta SCADA.")
        version, count, manifest, device_id, _ = system
        print(f"AcquaLink {device_id} — mapa SCADA versão {version} — {count} sensor(es)")
        if version != SUPPORTED_VERSION:
            print(f"ATENÇÃO: este script foi escrito para a versão {SUPPORTED_VERSION} "
                  "do mapa. Confira o manual do AcquaLink antes de confiar nos valores.")

        while True:
            print(f"\n{time.strftime('%H:%M:%S')}")
            for kind, slot, label in manifest:
                if kind not in BLOCKS:
                    print(f"  {label:10s} tipo {kind} desconhecido")
                    continue
                state, values = read_sensor(client, args.endereco, kind, slot)
                if state is None:
                    print(f"  {label:10s} sem resposta")
                elif state & 0x0002:
                    print(f"  {label:10s} SEM COMUNICAÇÃO com o sensor")
                else:
                    text = "  ".join(f"{n} {v:.2f} {u}".rstrip() for n, v, u in values)
                    print(f"  {label:10s} {text}")
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
