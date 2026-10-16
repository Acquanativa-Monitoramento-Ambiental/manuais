"""
Calibra o pH da sonda AcquaProbe-AQ com soluções tampão.

Uso:
    python acquaprobe_calibrar_ph.py --porta COM3
    python acquaprobe_calibrar_ph.py --porta COM3 --pontos 7,4
    python acquaprobe_calibrar_ph.py --porta COM3 --restaurar-fabrica

Como a sonda recebe um comando de calibração:
  1. O script escreve 3 registros a partir do HR 22:
        [palavra de comando, valor de referência (float, 2 registros)]
     A palavra é (dispositivo << 8) | função. Para o pH o dispositivo é 0x63:
        0x6304 + 7.0  = ponto médio (pH 7)  — SEMPRE o primeiro
        0x6303 + 4.0  = ponto baixo (pH 4)
        0x6305 + 10.0 = ponto alto (pH 10)
        0x6301        = volta à calibração de fábrica
  2. A sonda executa e publica o resultado no HR 20:
        (dispositivo << 8) | (estado << 4) | função, estado 2 = OK, 3 = FALHA
  3. O script escreve 0xFDFD no HR 22 para confirmar que leu o resultado.
     Sem essa confirmação a sonda IGNORA o próximo comando.
"""
import argparse
import sys
import time

import acquanativa as an

BAUDRATE = 57600
ACTIVATION = 0xFDFD
HR_STATUS, HR_COMMAND = 20, 22
DEV_PH = 0x63
FUNC_CLEAR, FUNC_LOW, FUNC_MID, FUNC_HIGH = 0x01, 0x03, 0x04, 0x05
POINTS = {7: FUNC_MID, 4: FUNC_LOW, 10: FUNC_HIGH}
STATE_OK, STATE_FAIL = 2, 3
RESULT_TIMEOUT_S = 15
STABLE_PH = 0.02


def read_ph(client, device):
    regs = an.read_retry(client, device, 6, 2, attempts=4, pause=0.3)   # HR 6-7
    return an.float_from_regs(*regs) if regs else None


def send_command(client, device, function, reference):
    """Envia um comando, espera o resultado e confirma. Devolve True se OK."""
    word = (DEV_PH << 8) | function
    payload = [word] + an.regs_from_float(reference)
    if not an.write_regs(client, device, HR_COMMAND, payload):
        print("  ERRO: a sonda não aceitou o comando.")
        return False

    deadline = time.time() + RESULT_TIMEOUT_S
    result = None
    while time.time() < deadline:
        regs = an.read_regs(client, device, HR_STATUS, 1)
        if regs:
            status = regs[0]
            # Só vale um estado que traga o NOSSO dispositivo; antes disso a
            # sonda ainda mostra o estado ocioso.
            if status >> 8 == DEV_PH and (status >> 4) & 0x0F in (STATE_OK, STATE_FAIL):
                result = (status >> 4) & 0x0F
                break
        time.sleep(0.5)

    # Confirma a leitura do resultado (libera a sonda para o próximo comando).
    for _ in range(3):
        if an.write_regs(client, device, HR_COMMAND, [ACTIVATION]):
            break
        time.sleep(0.5)

    if result == STATE_OK:
        print("  OK — a sonda confirmou a calibração.")
        return True
    if result == STATE_FAIL:
        print("  FALHA — a sonda recusou o comando (sensor de pH ausente ou com defeito?).")
    else:
        print("  Sem resposta da sonda dentro do prazo; confira a leitura antes de seguir.")
    return False


def main():
    p = argparse.ArgumentParser(description="Calibração de pH da AcquaProbe-AQ")
    p.add_argument("--porta", required=True)
    p.add_argument("--endereco", type=int, default=1)
    p.add_argument("--pontos", default="7,4,10")
    p.add_argument("--restaurar-fabrica", action="store_true")
    args = p.parse_args()

    points = [int(x) for x in args.pontos.split(",")]
    if any(pt not in POINTS for pt in points) or points[0] != 7:
        sys.exit("Use os tampões 7, 4 e 10, começando pelo 7.")

    client = an.connect(args.porta, baudrate=BAUDRATE, timeout=1.5)
    try:
        if not an.write_regs(client, args.endereco, 21, [ACTIVATION, ACTIVATION]):
            sys.exit("A sonda não respondeu à ativação. Confira a ligação.")
        time.sleep(3)

        if args.restaurar_fabrica:
            if an.ask("Apagar a calibração de pH da sonda? [s/N] "):
                send_command(client, args.endereco, FUNC_CLEAR, 0.0)
            return

        for buffer_ph in points:
            print(f"\n── Ponto pH {buffer_ph} ─────────────────────────────")
            input(f"  Lave o sensor com água destilada, mergulhe no tampão pH {buffer_ph} "
                  "e tecle Enter...")
            if not an.wait_until_stable(lambda: read_ph(client, args.endereco),
                                        STABLE_PH, "pH"):
                print("  Ponto pulado.")
                continue
            if not send_command(client, args.endereco, POINTS[buffer_ph], float(buffer_ph)):
                if not an.ask("  Continuar com os próximos pontos? [s/N] "):
                    break
        print("\nFim da calibração.")
    except KeyboardInterrupt:
        print("\nCancelado.")
        an.write_regs(client, args.endereco, HR_COMMAND, [ACTIVATION])
    finally:
        client.close()


if __name__ == "__main__":
    main()
