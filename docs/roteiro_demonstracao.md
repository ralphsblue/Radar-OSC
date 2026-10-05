# Roteiro de demonstração

Duração sugerida: 10 minutos.
Antes de começar: Docker Desktop aberto, `uv run validador-osc atualizar-bases` no mesmo dia e `uv run validador-osc servir`.

## 1. O problema (1 minuto)

Para firmar parceria com a administração pública, a organização precisa ser OSC (Lei 13.019/2014, art. 2º) e não pode estar impedida (art. 39).
Hoje essa checagem é manual, em sites diferentes.
O validador faz a triagem em segundos, mostra de onde veio cada dado e nunca aprova quando uma fonte essencial não respondeu.

## 2. Uma OSC apta (2 minutos)

CNPJ `19.131.243/0001-97` (Open Knowledge Brasil).

- Status APTA.
- Mostrar os cartões: situação, natureza, CNAE, tempo, sanções, TCU, CNJ, dirigentes, Mapa das OSCs.
- Mostrar o bloco "Fontes consultadas" e o link "Consultar na fonte".
- Repetir com a esfera "União" para mostrar o art. 33 (tempo de existência por esfera).

## 3. Entidades impedidas (3 minutos)

| CNPJ | O que mostra |
|---|---|
| `02.203.539/0001-73` | Fundação Assis Gurgacz: INAPTA pelo CEPIM |
| `30.994.499/0001-60` | Instituto Rafael Arcanjo: INAPTA pelo CEIS, vigente até 2028 |
| `05.051.898/0001-40` | Associação de Hip Hop de Laguna: CEIS e improbidade (CNJ) |
| `00.000.000/0001-91` | Banco do Brasil: natureza jurídica incompatível com OSC |

## 4. Casos que exigem atenção (2 minutos)

| CNPJ | O que mostra |
|---|---|
| `07.408.449/0001-32` | Instituto Atuar: sanção já encerrada aparece como histórico e não reprova |
| `13.144.375/0001-77` | Multa da Lei Anticorrupção: ALERTA, não reprovação (regra provisória do orientador) |
| `01.081.476/0001-67` | Dirigente com sanção: ALERTA, com o nome oculto para o público |
| `62.779.145/0002-70` | Filial: a entidade é avaliada pela matriz |
| `00108217000110` | Mitra Arquidiocesana: alerta de organização religiosa (art. 2º, I, c) |

## 5. Honestidade do sistema (1 minuto)

- Abrir `/fontes`: data de cada base, idade máxima e fontes online.
- Mostrar o bloco "O que esta triagem não verifica".
- Explicar que um CNPJ com dígito errado (`19.131.243/0001-98`) é tratado como erro de digitação, sem consultar nada.

## 6. Engenharia (1 minuto, se perguntarem)

- Motor de regras puro, separado das fontes, com regras do orientador em arquivos de parâmetros.
- Toda resposta de fonte é guardada com hash SHA-256 como evidência.
- Mais de 1.200 testes automatizados, inclusive de ponta a ponta com respostas reais gravadas.
