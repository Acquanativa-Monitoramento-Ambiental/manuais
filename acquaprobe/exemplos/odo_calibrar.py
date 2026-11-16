"""
Calibra a sonda de oxigênio dissolvido óptico (ODO).

Uso:
    python odo_calibrar.py --porta COM3                      (1 ponto: ar)
    python odo_calibrar.py --porta COM3 --dois-pontos        (zero + ar)
    python odo_calibrar.py --porta COM3 --restaurar-fabrica

Como a calibração funciona nesta sonda:
  * Ela guarda dois coeficientes, K e B (floats), no registro 0x1100
    (4 registros, função 16), e aplica sobre a saturação em FRAÇÃO (0 a 1):
        saturação_corrigida = K * saturação_bruta + B
    O OD em mg/L é calculado pela própria sonda a partir da saturação
    corrigida, então acompanha sozinho.
  * De fábrica: K = 1, B = 0.
  * 1 ponto (ar):       K = 1 / y,         B = 0
    2 pontos (zero+ar): K = 1 / (y - x),   B = -K * x
    x = leitura bruta na solução de oxigênio zero, y = leitura bruta no ar
    saturado de umidade (ambas em fração).
  * Se a sonda já tem uma calibração, o script lê o K e o B atuais e desfaz a
    correção para chegar à leitura bruta. Assim não é preciso restaurar a
    fábrica antes de recalibrar.
  * A sonda aplica o novo K/B em poucos segundos; a leitura ainda se acomoda
    por cerca de meio minuto.

⚠️ Não leia o registro 0x2E00 desta sonda: essa leitura PARA a medição.
"""
import argparse
import sys
import time

import acquanativa as an

REG_READ = 0x2600
REG_KB = 0x1100
STABLE_FRACTION = 0.005      # variação máxima de 0,5 % de saturação na janela


def read_fraction(client, device):
    """Saturação publicada pela sonda (fração 0-1), ou None."""
    regs = an.read_regs(client, device, REG_READ, 6)
    return an.floats_from_regs(regs)[1] if regs else None


def read_kb(client, device):
    regs = an.read_retry(client, device, REG_KB, 4)
    if regs is None:
        return None
    k, b = an.floats_from_regs(regs)
    return k, b


def write_kb(client, device, k, b):
    return an.write_regs(client, device, REG_KB, an.regs_from_float(k) + an.regs_from_float(b))


def capture_raw(client, device, k, b, instruction):
    """Espera estabilizar e devolve a leitura BRUTA (sem o K/B atual), ou None."""
    input(f"{instruction}\nTecle Enter para começar a acompanhar a leitura...")
    if not an.wait_until_stable(lambda: read_fraction(client, device),
                                STABLE_FRACTION, "(fração)"):
        return None
    published = read_fraction(client, device)
    if published is None:
        print("Sem resposta da sonda.")
        return None
    return (published - b) / k


def main():
    p = argparse.ArgumentParser(description="Calibração da sonda de OD óptico")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=1, help="padrão de fábrica: 1")
    p.add_argument("--dois-pontos", action="store_true",
                   help="zero (solução sem oxigênio) + ar")
    p.add_argument("--restaurar-fabrica", action="store_true", help="K = 1, B = 0")
    args = p.parse_args()

    client = an.connect(args.porta, baudrate=9600)
    try:
        kb = read_kb(client, args.endereco)
        if kb is None:
            sys.exit(f"A sonda não respondeu no endereço {args.endereco}.")
        k_old, b_old = kb
        print(f"Calibração atual: K = {k_old:.5f}   B = {b_old:.5f}")

        if args.restaurar_fabrica:
            k_new, b_new = 1.0, 0.0
        else:
            x = 0.0
            if args.dois_pontos:
                x = capture_raw(client, args.endereco, k_old, b_old,
                                "PONTO ZERO: mergulhe a sonda na solução de oxigênio zero "
                                "(sulfito de sódio).")
                if x is None:
                    print("Cancelado, nada foi enviado.")
                    return
                print(f"  zero bruto: {x * 100:.2f} %  — lave e seque bem a sonda.")
            y = capture_raw(client, args.endereco, k_old, b_old,
                            "PONTO AR: sonda limpa, seca, no ar saturado de umidade "
                            "(ex.: dentro do copo de calibração com uma esponja úmida), "
                            "sem sol direto.")
            if y is None:
                print("Cancelado, nada foi enviado.")
                return
            if y - x < 0.05:
                sys.exit(f"Leituras inconsistentes (zero {x * 100:.1f} %, ar {y * 100:.1f} %). "
                         "Confira as soluções e repita.")
            k_new = 1.0 / (y - x)
            b_new = -k_new * x
            print(f"  ar bruto: {y * 100:.2f} %")

        print(f"Novo K = {k_new:.5f}   B = {b_new:.5f}")
        if not an.ask("Gravar na sonda? [s/N] "):
            print("Nada foi enviado.")
            return
        if not write_kb(client, args.endereco, k_new, b_new):
            sys.exit("ERRO: a sonda não confirmou a escrita.")
        time.sleep(5)
        kb = read_kb(client, args.endereco)
        sat = read_fraction(client, args.endereco)
        if kb:
            print(f"Gravado: K = {kb[0]:.5f}   B = {kb[1]:.5f}")
        if sat is not None:
            print(f"Leitura agora: {sat * 100:.1f} % (ainda se acomoda por ~30 s)")
    except KeyboardInterrupt:
        print("\nCancelado.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
