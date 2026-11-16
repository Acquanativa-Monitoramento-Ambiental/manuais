"""
acquanativa.py — funções comuns aos exemplos (conexão e conversão de registros).

Os exemplos desta pasta importam este arquivo. Mantenha-o na mesma pasta que
os scripts.

Todos os equipamentos Acquanativa (AcquaSensor, AcquaProbe-AQ e AcquaLink)
falam Modbus RTU sobre RS-485. Os números reais (temperatura, pH, OD, ...) vão
em pares de registros, no formato IEEE-754 de 32 bits descrito em
`float_from_regs`.

Requer: Python 3.9+ e pymodbus 3.10 ou mais novo (`pip install -r requirements.txt`).
"""
import struct
import sys
import time

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

import logging
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)


# ─── Conversão de registros ──────────────────────────────────────────────────

def float_from_regs(high, low):
    """Dois registros de 16 bits -> float.

    Os equipamentos guardam o float em little-endian: os 4 bytes, na ordem em
    que chegam pelo cabo, são os bytes do float do menos para o mais
    significativo. Exemplo real: [0x0000, 0xC841] = 25.0 °C.

    Em programas como Open ModScan ou QModMaster, escolha float de 32 bits
    com ordem de bytes DCBA (little-endian).
    """
    raw = struct.pack(">HH", high & 0xFFFF, low & 0xFFFF)
    return struct.unpack("<f", raw)[0]


def regs_from_float(value):
    """float -> dois registros, no mesmo formato de `float_from_regs`.

    Exemplo: 1413.0 -> [0x00A0, 0xB044].
    """
    raw = struct.pack("<f", value)
    return [raw[0] << 8 | raw[1], raw[2] << 8 | raw[3]]


def floats_from_regs(registers):
    """Lista de registros -> lista de floats (um float a cada 2 registros)."""
    return [float_from_regs(registers[i], registers[i + 1])
            for i in range(0, len(registers) - 1, 2)]


def swap16(register):
    """Inverte os dois bytes de um registro.

    O AcquaSensor guarda números inteiros pequenos (endereço Modbus, estado
    da calibração) com os bytes invertidos dentro do registro: o endereço 3
    chega como 0x0300. Use esta função para ler e para escrever esses valores.
    """
    register &= 0xFFFF
    return ((register & 0xFF) << 8) | (register >> 8)


def text_from_regs(registers):
    """Registros -> texto ASCII (2 caracteres por registro)."""
    raw = b"".join((r & 0xFFFF).to_bytes(2, "big") for r in registers)
    return raw.decode("ascii", errors="replace").rstrip("\x00 ")


# ─── Famílias de AcquaSensor ─────────────────────────────────────────────────
#
# Cada família tem um bloco de leitura ("ReadAll"): endereço + quantidade de
# registros. O sensor só responde se a quantidade for EXATAMENTE a da tabela.
# Os valores vêm na ordem de `channels`, um float por canal.
#
# O nome da família (4 letras) está no registro 0x1805 do próprio sensor.
# "default_address" é o endereço de fábrica de cada família.

ACQUASENSOR_FAMILIES = {
    "PHT0": dict(product="AS-TP (pH)", default_address=3,
                 read_all=(0x2607, 4),
                 channels=[("Temperatura", "°C"), ("pH", "")]),
    "ODT0": dict(product="AS-TD (oxigênio dissolvido)", default_address=2,
                 read_all=(0x2603, 6),
                 channels=[("Temperatura", "°C"), ("OD saturação", "%"),
                           ("OD", "mg/L")]),
    "ECT0": dict(product="AS-TE (condutividade)", default_address=5,
                 read_all=(0x260F, 10),
                 channels=[("Temperatura", "°C"), ("Condutividade", "µS/cm"),
                           ("TDS", "ppm"), ("Salinidade", "ppt"),
                           ("Gravidade específica", "")]),
    "ORPT": dict(product="AS-TO (ORP)", default_address=4,
                 read_all=(0x260B, 4),
                 channels=[("Temperatura", "°C"), ("ORP", "mV")]),
    "TURB": dict(product="AS-TT (turbidez)", default_address=0,
                 read_all=(0x260C, 4),
                 channels=[("Temperatura", "°C"), ("Turbidez", "NTU")]),
    "T000": dict(product="AS-T (temperatura)", default_address=8,
                 read_all=(0x260A, 2),
                 channels=[("Temperatura", "°C")]),
    "CO2T": dict(product="AS-CO2 (CO2 do ar)", default_address=1,
                 read_all=(0x2600, 6),
                 channels=[("Temperatura do ar", "°C"), ("CO2", "ppm"),
                           ("Umidade relativa", "%")]),
}

REG_NAME = 0x1805        # nome da família, 4 caracteres ASCII
REG_ADDRESS = 0x3000     # endereço Modbus do sensor (bytes invertidos)
REG_SERIAL = 0x0900      # número de série, 7 registros
REG_VERSION = 0x0700     # versão de hardware e firmware, 2 registros
BROADCAST = 255          # endereço que qualquer AcquaSensor responde


def identify_acquasensor(client, device):
    """Descobre a família do AcquaSensor no endereço `device`, ou None.

    Alguns firmwares respondem ao nome só quando se pedem 2 registros, outros
    só quando se pede 1. Tentamos os dois e, se nada servir, testamos o bloco
    de leitura da família de fábrica daquele endereço.
    """
    for count in (2, 1):
        regs = read_retry(client, device, REG_NAME, count, attempts=2)
        if regs:
            name = text_from_regs(regs)
            if name in ACQUASENSOR_FAMILIES:
                return name
    for name, fam in ACQUASENSOR_FAMILIES.items():
        if fam["default_address"] == device:
            address, count = fam["read_all"]
            if read_retry(client, device, address, count, attempts=2):
                return name
    return None


def read_acquasensor(client, device, family):
    """Lê todos os canais do sensor. Devolve [(nome, valor, unidade), ...] ou None."""
    fam = ACQUASENSOR_FAMILIES[family]
    address, count = fam["read_all"]
    regs = read_retry(client, device, address, count)
    if regs is None:
        return None
    values = floats_from_regs(regs)
    return [(label, value, unit)
            for (label, unit), value in zip(fam["channels"], values)]


# ─── Conexão ─────────────────────────────────────────────────────────────────

def connect(port, baudrate=9600, timeout=2.0):
    """Abre a porta serial (8N1). Encerra o script com uma mensagem se falhar.

    port: "COM3" no Windows, "/dev/ttyUSB0" no Linux.
    """
    client = ModbusSerialClient(port=port, baudrate=baudrate, bytesize=8,
                                parity="N", stopbits=1, timeout=timeout,
                                retries=1)
    if not client.connect():
        sys.exit(f"ERRO: não foi possível abrir a porta {port}. "
                 "Confira o conversor USB-RS485 e se outro programa "
                 "(AcquaSmart, ModScan) está usando a porta.")
    return client


def read_regs(client, device, address, count):
    """Lê `count` holding registers (função 03). Devolve a lista ou None.

    Nunca lança exceção: um tempo esgotado ou uma resposta de erro viram None,
    para o script decidir se tenta de novo.
    """
    try:
        rr = client.read_holding_registers(address, count=count, device_id=device)
    except ModbusException:
        return None
    if rr.isError():
        return None
    return rr.registers


def write_regs(client, device, address, values):
    """Escreve registros com a função 16 (Write Multiple Registers).

    Use sempre a função 16, mesmo para um só registro: o AcquaSensor não
    aceita a função 06. Devolve True se o equipamento confirmou a escrita.
    """
    try:
        rr = client.write_registers(address, values, device_id=device)
    except ModbusException:
        return False
    return not rr.isError()


def read_retry(client, device, address, count, attempts=3, pause=0.5):
    """`read_regs` com algumas tentativas — o barramento às vezes perde um quadro."""
    for _ in range(attempts):
        regs = read_regs(client, device, address, count)
        if regs is not None:
            return regs
        time.sleep(pause)
    return None


# ─── Estabilidade (usada nos scripts de calibração) ──────────────────────────

class StabilityWindow:
    """Guarda as últimas N leituras e diz quanto elas variam.

    Calibrar com a leitura ainda mudando grava um valor errado na sonda.
    Os scripts de calibração mostram esta variação e só recomendam seguir
    quando ela fica abaixo do limite.
    """

    def __init__(self, size=10, limit=0.5):
        self.size = size
        self.limit = limit
        self.values = []

    def add(self, value):
        self.values.append(value)
        if len(self.values) > self.size:
            self.values.pop(0)

    @property
    def spread(self):
        """Diferença entre a maior e a menor leitura da janela."""
        return max(self.values) - min(self.values) if self.values else float("inf")

    @property
    def stable(self):
        return len(self.values) >= self.size and self.spread <= self.limit

    def describe(self):
        if len(self.values) < self.size:
            return f"aguardando ({len(self.values)}/{self.size} leituras)"
        word = "ESTÁVEL" if self.stable else "estabilizando"
        return f"{word} (variação {self.spread:.3f})"


def ask(question):
    """Pergunta sim/não no terminal. Só 's' ou 'sim' contam como sim."""
    return input(question).strip().lower() in ("s", "sim", "y", "yes")


def wait_until_stable(read_value, limit, unit="", window=10, max_wait_s=300):
    """Mostra a leitura ao vivo até estabilizar, depois pede confirmação.

    read_value: função sem argumentos que devolve o valor atual (ou None).
    limit:      variação máxima aceita na janela, na unidade do valor.
    Devolve True se o operador confirmou o envio.
    """
    win = StabilityWindow(size=window, limit=limit)
    start = time.time()
    while True:
        value = read_value()
        if value is not None:
            win.add(value)
            shown = f"{value:10.3f} {unit}"
        else:
            shown = f"{'--':>10} {unit}"
        print(f"\r  leitura {shown}   {win.describe():34s}", end="", flush=True)
        if win.stable:
            print()
            return ask("  Leitura estável. Enviar a calibração agora? [s/N] ")
        if time.time() - start > max_wait_s:
            print()
            return ask("  A leitura não estabilizou. Enviar mesmo assim? [s/N] ")
        time.sleep(1.0)
