# AcquaProbe

Sondas multiparâmetros AcquaProbe (RS-485, Modbus RTU).

## Manuais

- [AcquaProbe-APE](AcquaProbe-APE.pdf) — 12 páginas
- [AcquaProbe-AQ](AcquaProbe-AQ.pdf) — 15 páginas

## Exemplos

| Equipamento | Arquivos |
|---|---|
| AcquaProbe-AQ | [`acquaprobe_ler.py`](exemplos/acquaprobe_ler.py), [`acquaprobe_calibrar_ph.py`](exemplos/acquaprobe_calibrar_ph.py) |
| Sonda de OD óptico (ODO) | [`odo_ler.py`](exemplos/odo_ler.py), [`odo_calibrar.py`](exemplos/odo_calibrar.py) |

```
python acquaprobe_ler.py --porta COM3
python acquaprobe_calibrar_ph.py --porta COM3 --pontos 7,4
python odo_ler.py --porta COM3 --csv leituras.csv
```

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
