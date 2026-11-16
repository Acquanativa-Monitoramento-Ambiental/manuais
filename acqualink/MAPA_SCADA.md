# AcquaLink — Mapa de Registros SCADA (versão 7)

Para integradores: como ler o AcquaLink a partir de um CLP, SCADA ou
supervisório.

## 1. Comunicação

| Parâmetro | Valor |
|---|---|
| Protocolo | Modbus RTU, **escravo** |
| Porta | RS-485 **SCADA** (separada da porta de sensores) |
| Endereço | 1 (padrão; ajustável no painel, menu SCADA) |
| Velocidade | 9600 (padrão), 19200, 38400, 57600 ou 115200 |
| Formato | 8N1 |
| Tipo de registro | Holding registers — leitura com a função **03** |
| Endereçamento | Base zero (HR 0 = 40001 na notação Modicon) |
| Faixa exposta | HR 0 a HR 431 |

Leia no máximo 100 registros por requisição.

## 2. Como ler

1. Leia **HR 201** e confira que vale **7**. Se o valor for outro, este mapa
   não se aplica ao firmware do equipamento.
2. Leia o **manifesto** (HR 203–250) para saber quais sensores existem e em
   qual bloco/posição cada um está.
3. Leia o bloco de cada sensor. Confira o **registro de estado** antes de usar
   os valores.

Cada sensor tem uma posição (slot) **fixa**: ela não muda quando outro sensor
é adicionado, removido ou fica fora do ar. As tags do seu supervisório podem
apontar direto para os registros.

## 3. Formato dos valores

- Medições: **inteiro com sinal (int16) × 100**. Ex.: pH 7,85 → 785;
  temperatura −1,50 → −150. Valores fora da faixa ficam em ±32767.
- **Exceções:** CO₂ vem em **ppm, sem fator** (× 1). Cor (Hazen) e R, G, B
  vêm **× 10**.
- Textos (nomes, ID): 2 caracteres ASCII por registro, primeiro caractere no
  byte alto, completado com zeros.

## 4. Registro de estado do slot

O primeiro registro de cada slot:

| Valor | Significado |
|---|---|
| 0 | Vazio — nenhum sensor nesta posição |
| bit 0 = 1 | Sensor atribuído |
| bit 1 = 1 | **Sem comunicação** — o sensor está cadastrado mas não responde; os valores ficam em 0 |

Ou seja: **1** = normal; **3** = sensor fora do ar. Nunca use os valores de
um slot com o bit 1 ligado.

## 5. Blocos de medição

O slot *n* (0 a 7) de um bloco começa em `início + n × passo`.

| Tipo | Código | Início | Passo | Registros do slot |
|---|---|---|---|---|
| OD | 4 | 1 | 4 | estado, OD sat (%), OD (mg/L), temperatura |
| pH | 1 | 33 | 3 | estado, pH, temperatura |
| Condutividade | 2 | 57 | 6 | estado, CE (µS/cm), TDS (ppm), salinidade (ppt), gravidade específica, temperatura |
| ORP | 3 | 105 | 3 | estado, ORP (mV), temperatura |
| Turbidez | 5 | 129 | 2 | estado, turbidez (NTU) |
| Sonda (AcquaProbe-AQ) | 6 | 145 | 7 | estado, pH, temperatura, OD sat, OD mg/L, CE, turbidez |
| Temperatura | 7 | 300 | 2 | estado, temperatura |
| Amônio | 8 | 316 | 5 | estado, NH₄ (mg/L), NH₄⁺ (mg/L), pH, temperatura |
| CO₂ | 9 | 356 | 4 | estado, CO₂ (**ppm, × 1**), temperatura do ar, umidade relativa (%) |
| Cor | 10 | 392 | 5 | estado, cor (Hazen **× 10**), R, G, B (**× 10**) |

Um canal que o sensor não mede lê 0 com o slot normal (ex.: um sensor de CO₂
que não mede umidade).

**Exemplo:** o segundo sensor de pH (slot 1): estado em HR 36, pH em HR 37,
temperatura em HR 38.

## 6. Região de sistema

| Registro | Conteúdo |
|---|---|
| HR 0 | **Habilitar**: escrever 1 coloca todos os relés em AUTO (comando único) |
| HR 201 | Versão do mapa = **7** |
| HR 202 | Quantidade de sensores no manifesto |
| HR 203–250 | Manifesto: 8 entradas de 6 registros — `[código do tipo, slot, nome (4 registros, 8 caracteres)]`. Código 0 = entrada vazia |
| HR 251–258 | ID do equipamento (16 caracteres) |
| HR 259 | Estado do sistema: byte baixo = estado geral (0 escrita, 1 leitura, 2 salvando, 3 inicializando, 8 falha); **bit 8** = algum sensor sem comunicação |

**Exemplo de manifesto:** entrada 0 em HR 203–208 = `[1, 0, "PHT0_3"]` → o
sensor `PHT0_3` está no bloco pH, slot 0 (HR 33–35).

## 7. Relés

| Registro | Conteúdo |
|---|---|
| HR 288–291 | Estado das saídas R1–R4 |
| HR 388–391 | Estado das saídas SD1–SD4 (módulo de expansão) |

Em cada registro: **bit 0** = saída ligada; **bit 1** = saída no estado de
segurança (falha de sensor ou emergência).

Os registros HR 260–287 existem por compatibilidade, mas **não alteram** as
regras dos relés. Configure os relés pelo painel ou pelo portal web.

## 8. Reposicionar um sensor (avançado)

Para mover um sensor para outro slot ou renomeá-lo:

1. HR 292 = índice da entrada no manifesto (0–7).
2. HR 294–297 = novo nome (8 caracteres) ou zeros para manter o atual.
3. HR 293 = novo slot (0–7), ou **255 para apagar** a entrada. **Esta escrita
   aplica o comando.**

Um slot já ocupado por outro sensor do mesmo tipo é recusado.

## 9. Exemplo em Python

Veja `python/acqualink_ler_scada.py`.
