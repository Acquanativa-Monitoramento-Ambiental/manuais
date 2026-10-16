# Exemplos em Python

Scripts curtos e comentados para as tarefas básicas com os equipamentos
Acquanativa: procurar, ler, mudar o endereço e calibrar. Servem para usar
direto e como ponto de partida para o seu próprio sistema: o comentário no
início de cada arquivo descreve os registros e os comandos usados.

## Download

- **Tudo de uma vez:** [baixar .zip](https://github.com/Acquanativa-Monitoramento-Ambiental/manuais/archive/refs/heads/main.zip)
  e use a pasta `python/`.
- **Só alguns arquivos:** abra o arquivo aqui no GitHub e clique em
  *Download raw file*. Baixe sempre também o `acquanativa.py` (todos os
  scripts usam) e o `requirements.txt`.

## Instalação

1. Instale o Python 3.9 ou mais novo ([python.org](https://www.python.org/downloads/)).
   No Windows, marque **Add Python to PATH**.
2. Na pasta `python/`, abra um terminal e rode:

   ```
   pip install -r requirements.txt
   ```

3. Descubra a porta do conversor USB–RS485:
   - **Windows:** Gerenciador de Dispositivos > Portas (COM e LPT) → ex.: `COM3`.
   - **Linux:** `ls /dev/ttyUSB*` → ex.: `/dev/ttyUSB0`. Se der "permissão
     negada": `sudo usermod -aG dialout $USER` e entre de novo na sessão.

Feche o AcquaSmart, o ModScan e qualquer outro programa que use a porta antes
de rodar um script. Todos os scripts aceitam `--help`.

> **Atenção:** os scripts de calibração e de mudança de endereço gravam no
> equipamento. Confira o endereço antes de rodar.

## Scripts

| Equipamento | Arquivos |
|---|---|
| AcquaSensor (todos) | `acquasensor_procurar.py`, `acquasensor_ler.py`, `acquasensor_mudar_endereco.py` |
| AcquaSensor AS-TP (pH) | `acquasensor_calibrar_ph.py` |
| AcquaSensor AS-TE / AS-TE4P (condutividade) | `acquasensor_calibrar_ec.py` |
| AcquaSensor AS-TT (turbidez) | `acquasensor_calibrar_turb.py` |
| AcquaSensor AS-TD (oxigênio dissolvido) | `acquasensor_calibrar_od.py` |
| AcquaSensor AS-TO (ORP) | `acquasensor_calibrar_orp.py` |
| Sonda de OD óptico | `odo_ler.py`, `odo_calibrar.py` |
| AcquaProbe-AQ | `acquaprobe_ler.py`, `acquaprobe_calibrar_ph.py` |
| AcquaLink (porta SCADA) | `acqualink_ler_scada.py` |
| Todos | `acquanativa.py` (módulo comum), `requirements.txt` |

## Exemplos

```
python acquasensor_procurar.py --porta COM3
python acquasensor_ler.py --porta COM3 --endereco 3
python acquasensor_calibrar_ph.py --porta COM3 --endereco 3
python acquasensor_mudar_endereco.py --porta COM3 --atual 3 --novo 13
python odo_ler.py --porta COM3 --csv leituras.csv
python acquaprobe_ler.py --porta COM3
python acqualink_ler_scada.py --porta COM4
```

## Como funciona, em 10 linhas

Ler o pH e a temperatura de um AS-TP no endereço 3:

```python
import struct
from pymodbus.client import ModbusSerialClient

client = ModbusSerialClient(port="COM3", baudrate=9600, parity="N",
                            stopbits=1, bytesize=8, timeout=2)
client.connect()
rr = client.read_holding_registers(0x2607, count=4, device_id=3)
temp, ph = [struct.unpack("<f", struct.pack(">HH", a, b))[0]
            for a, b in zip(rr.registers[0::2], rr.registers[1::2])]
print(f"pH {ph:.2f}  temperatura {temp:.1f} °C")
```

O mapa completo de registros está no manual de cada equipamento.

Suporte: suporte@acquanativa.com.br
