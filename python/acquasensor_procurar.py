"""
Procura AcquaSensors no barramento RS-485 e lista o que encontrou.

Uso:
    python acquasensor_procurar.py --porta COM3                (endereços de fábrica)
    python acquasensor_procurar.py --porta COM3 --de 1 --ate 20

Cada endereço vazio custa cerca de 1 a 2 segundos, então prefira uma faixa
pequena. Sem --de/--ate, procura só nos endereços de fábrica de cada família.
"""
import argparse

import acquanativa as an


def describe(client, address, family):
    """Texto com versão e número de série, quando o sensor informa."""
    parts = []
    regs = an.read_regs(client, address, an.REG_VERSION, 2)
    if regs:
        hw, fw = regs
        parts.append(f"HW {hw >> 8}.{hw & 0xFF}  FW {fw >> 8}.{fw & 0xFF}")
    regs = an.read_regs(client, address, an.REG_SERIAL, 7)
    if regs:
        # 14 bytes de texto ASCII. Sensores numerados por versões antigas do
        # AcquaSmart guardam um dígito por byte (0x01 = "1").
        raw = b"".join(r.to_bytes(2, "big") for r in regs).strip(b"\x00")
        if all(0x20 <= b < 0x7F for b in raw):
            serial = raw.decode("ascii")
        else:
            serial = "".join(f"{b:X}" for b in raw)
        parts.append(f"série {serial}")
    return "  ".join(parts)


def main():
    p = argparse.ArgumentParser(description="Procura AcquaSensors no barramento")
    p.add_argument("--porta", required=True)
    p.add_argument("--de", type=int, help="primeiro endereço da faixa")
    p.add_argument("--ate", type=int, help="último endereço da faixa")
    args = p.parse_args()

    if args.de is not None or args.ate is not None:
        first = args.de or 1
        last = args.ate or first
        addresses = range(max(1, first), min(247, last) + 1)
    else:
        addresses = sorted({f["default_address"]
                            for f in an.ACQUASENSOR_FAMILIES.values()
                            if f["default_address"] >= 1})

    client = an.connect(args.porta, baudrate=9600, timeout=1.0)
    found = 0
    try:
        for address in addresses:
            print(f"endereço {address:3d} ... ", end="", flush=True)
            family = an.identify_acquasensor(client, address)
            if family is None:
                print("-")
                continue
            found += 1
            product = an.ACQUASENSOR_FAMILIES[family]["product"]
            print(f"{family}  {product}  {describe(client, address, family)}")
    except KeyboardInterrupt:
        print("\nInterrompido.")
    finally:
        client.close()
    print(f"\n{found} sensor(es) encontrado(s).")


if __name__ == "__main__":
    main()
