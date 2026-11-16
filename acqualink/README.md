# AcquaLink e AcquaMeter

Controlador e registrador AcquaLink e medidor AcquaMeter.

Para integrar o AcquaLink a um CLP, SCADA ou supervisório, use o
[mapa de registros SCADA](MAPA_SCADA.md).

## Manuais

- [AcquaLink](AcquaLink.pdf) — 12 páginas
- [AcquaMeter](AcquaMeter.pdf) — 11 páginas
- [Mapa de registros SCADA](MAPA_SCADA.md)

## Exemplos

| Equipamento | Arquivo | O que faz |
|---|---|---|
| AcquaLink (porta SCADA) | [`acqualink_ler_scada.py`](exemplos/acqualink_ler_scada.py) | Lê a lista de sensores e as medições pela porta SCADA (Modbus RTU) |

```
python acqualink_ler_scada.py --porta COM4
python acqualink_ler_scada.py --porta /dev/ttyUSB1 --endereco 1 --baud 9600
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
