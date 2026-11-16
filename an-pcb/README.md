# Módulos I²C (AN-PCB)

Módulos de interface com saída **I²C** (placas AN-PCB), para ligar eletrodos
de OD, pH e ORP a Arduino, ESP32, Raspberry Pi e outros microcontroladores.
Todos usam os mesmos comandos de texto (`Info`, `R`, `Cal,...`, `I2C,<n>`).

| Módulo | Endereço de fábrica | Resposta ao `Info` |
|---|---|---|
| ACQUA-OD | 32 (0x20) | `OD,EZO,1.1` |
| ACQUA-pH | 64 (0x40) | `pH,EZO,1.1` |
| ACQUA-ORP | 96 (0x60) | `ORP,EZO,1.1` |

## Manuais

- [ACQUA-OD](ACQUA-OD.pdf) — 14 páginas
- [ACQUA-ORP](ACQUA-ORP.pdf) — 12 páginas
- [ACQUA-pH](ACQUA-pH.pdf) — 14 páginas

## Exemplos

### Arduino — [`exemplos/arduino/acqua_i2c/`](exemplos/arduino/acqua_i2c/acqua_i2c.ino)

Terminal pelo Monitor Serial: procura os módulos, envia qualquer comando e
mostra a resposta. Serve para conferir a ligação, calibrar e mudar o endereço
sem escrever código.

1. Abra `acqua_i2c.ino` na IDE do Arduino e envie para a placa.
2. Abra o Monitor Serial a **9600** baud, com **Nova linha**.
3. Digite `?` para procurar, `@64` para escolher o módulo no endereço 64,
   `ler` para ler a cada segundo, ou qualquer comando do manual
   (`Cal,mid`, `Status`...).

### Raspberry Pi — [`exemplos/python/acqua_i2c.py`](exemplos/python/acqua_i2c.py)

Na pasta `exemplos/python/`:

```
sudo raspi-config        # Interface Options > I2C > Enable, e reinicie
pip install -r requirements.txt
python3 acqua_i2c.py --procurar
python3 acqua_i2c.py --endereco 64 --ler --temperatura 23.5
python3 acqua_i2c.py --endereco 64 Cal,mid
python3 acqua_i2c.py --endereco 96            # terminal interativo
```

> ⚠️ O ACQUA-ORP é alimentado com **5 V**. Com mestre de 3,3 V (ESP32,
> Raspberry Pi), use um conversor de nível de I²C. Nunca ligue 5 V direto nos
> pinos do Raspberry Pi.

O exemplo mínimo em Arduino (ler um módulo) está na seção 3 de cada manual.

Suporte: suporte@acquanativa.com.br
