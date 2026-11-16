# AcquaSensor

Sensores digitais AcquaSensor (RS-485, Modbus RTU): pH, OD, condutividade,
ORP, turbidez, temperatura, CO₂, cor e clorofila.

## Manuais

- [AcquaSensor](AcquaSensor.pdf) — 12 páginas
- [AcquaSensor Clorofila](AcquaSensor-Clorofila.pdf) — 13 páginas
- [AcquaSensor CO2](AcquaSensor-CO2.pdf) — 13 páginas
- [AcquaSensor Cor](AcquaSensor-Cor.pdf) — 15 páginas
- [AcquaSensor Turbidez](AcquaSensor-Turbidez.pdf) — 13 páginas
- [AcquaSensor Turbidez Autolimpante](AcquaSensor-Turbidez-Autolimpante.pdf) — 10 páginas

## Exemplos

| Sensor | Arquivos |
|---|---|
| Todos | [`acquasensor_procurar.py`](exemplos/acquasensor_procurar.py), [`acquasensor_ler.py`](exemplos/acquasensor_ler.py), [`acquasensor_mudar_endereco.py`](exemplos/acquasensor_mudar_endereco.py) |
| AS-TP (pH) | [`acquasensor_calibrar_ph.py`](exemplos/acquasensor_calibrar_ph.py) |
| AS-TE / AS-TE4P (condutividade) | [`acquasensor_calibrar_ec.py`](exemplos/acquasensor_calibrar_ec.py) |
| AS-TT (turbidez) | [`acquasensor_calibrar_turb.py`](exemplos/acquasensor_calibrar_turb.py) |
| AS-TD (oxigênio dissolvido) | [`acquasensor_calibrar_od.py`](exemplos/acquasensor_calibrar_od.py) |
| AS-TO (ORP) | [`acquasensor_calibrar_orp.py`](exemplos/acquasensor_calibrar_orp.py) |

```
python acquasensor_procurar.py --porta COM3
python acquasensor_ler.py --porta COM3 --endereco 3
python acquasensor_calibrar_ph.py --porta COM3 --endereco 3
python acquasensor_mudar_endereco.py --porta COM3 --atual 3 --novo 13
```

### Como funciona, em 10 linhas

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

O mapa completo de registros está no manual de cada sensor.

### Instalação dos exemplos em Python

Os scripts ficam na pasta [`exemplos/`](exemplos/). Cada pasta `exemplos/`
traz o `acquanativa.py` (módulo comum, usado por todos os scripts) e o
`requirements.txt`: baixe sempre os dois junto com o script.

1. Instale o Python 3.9 ou mais novo ([python.org](https://www.python.org/downloads/)).
   No Windows, marque **Add Python to PATH**.
2. Na pasta `exemplos/`, abra um terminal e rode:

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

Suporte: suporte@acquanativa.com.br
