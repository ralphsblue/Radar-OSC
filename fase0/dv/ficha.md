# Ficha - Verificação 1: dígito verificador do CNPJ

Data: 2026-09-30.
Referência: capítulo 4 e Apêndice B da especificação do MVP.

## Objetivo

Decidir se a validação do DV do CNPJ usa uma biblioteca pronta ou código próprio.
Requisitos: aceitar o formato alfanumérico (IN RFB 2.229/2024, valor do caractere = ASCII - 48), rejeitar sequências repetidas e informar o motivo da falha e o DV esperado (mensagem do 4.4: "dígito verificador não confere (esperado XX)").

## Bibliotecas avaliadas

Todas foram instaladas num ambiente virtual separado (fora do `.venv` do projeto) e testadas com os mesmos casos.
Metadados obtidos do PyPI e da API do GitHub em 2026-09-30.

| Biblioteca | Versão / última release | Mantida? | Licença | Dependências | Alfanumérico | Rejeita repetidos | Retorno |
|---|---|---|---|---|---|---|---|
| validate-docbr | 2.0.0 / 2026-04-04 | Sim (484 estrelas, commit em 2026-09) | MIT | nenhuma | Sim | Só se os 14 caracteres forem iguais | bool |
| pycpfcnpj | 1.9 / 2026-01-25 | Pouco ativa (último push 2026-01) | MIT | nenhuma | Sim | Só se os 14 caracteres forem iguais | bool |
| brazilnum | 0.10.0 / 2026-07-24 | Sim (100 estrelas) | MIT | nenhuma | Sim | Só `00000000000000` | bool; completa com zeros à esquerda por padrão (`"191"` é aceito) |
| python-stdnum | 2.2 / 2026-01-04 | Sim (598 estrelas, projeto antigo e sólido) | LGPL-2.1+ | nenhuma | Sim | Só base começando com 12 zeros | exceção por tipo de erro, sem DV esperado |
| brutils | 2.5.0 / 2026-06-30 | Sim (524 estrelas) | MIT | coverage, holidays, num2words | Sim | Só se os 14 caracteres forem iguais | bool; não aceita máscara |
| cnpj-alfanumerico (`cnpjalfa`) | 0.1.0 / 2026-07-29 | Incerta (autor único, 0 estrelas, 1 release) | MIT | nenhuma | Sim | Sim, pela base de 12 posições | bool |

Outros nomes pesquisados sem utilidade: `brazilian-utils` (abandonado em 2018, substituído pelo `brutils`), `cpf-cnpj-validator` (release única de 2021, sem alfanumérico), `docbr`, `br-validator` e `cnpj` (inexistentes no PyPI).

## Resultado dos testes nas bibliotecas

"ERRO" marca resultado diferente do esperado.

| Entrada | Esperado | validate-docbr | pycpfcnpj | brazilnum | stdnum | brutils | cnpjalfa |
|---|---|---|---|---|---|---|---|
| 19.131.243/0001-97 | válido | ok | ok | ok | ok | ERRO | ok |
| 00.000.000/0001-91 | válido | ok | ok | ok | ok | ERRO | ok |
| 12.ABC.345/01DE-35 | válido | ok | ok | ok | ok | ERRO | ok |
| 19.131.243/0001-98 | inválido | ok | ok | ok | ok | ok | ok |
| 11111111111111 | inválido | ok | ok | ok | ok | ok | ok |
| 12ABC34501DE3 | inválido | ok | ok | ok | ok | ok | ok |
| 12.abc.345/01de-35 | válido | ok | ok | ok | ok | ERRO | ok |
| " 19 131 243 0001 97 " | válido | ERRO | ERRO | ok | ok | ERRO | ERRO |
| 19.131.243.0001-97 | válido | ok | ok | ok | ok | ERRO | ERRO |
| 11111111111180 (base repetida, DV confere) | inválido | ERRO | ERRO | ERRO | ERRO | ERRO | ok |
| 12ABC34501DE + dígitos arábico-índicos | inválido | ok | ok | ok | ok | ERRO | ok |
| "19131243000197\n" | válido | ok | ERRO | ok | ok | ERRO | ok |

Todas calculam o DV corretamente, inclusive no formato alfanumérico.
As diferenças estão nas bordas: normalização da entrada, regra de sequência repetida e informação devolvida.

## Decisão: código próprio

O cálculo é curto (cerca de 20 linhas), estável (definido pela Receita) e já está escrito na especificação.
Nenhuma biblioteca devolve o que o motor de regras precisa: motivo da falha (formato, repetido ou dv) e o DV esperado para a mensagem do 4.4.
Usar uma delas exigiria repetir o cálculo para obter o DV esperado, ou seja, manter a dependência e o código próprio ao mesmo tempo.
Cinco das seis aceitam `11111111111180`, que tem base repetida e DV correto, e a especificação pede barrar sequências repetidas.
A única que acerta essa regra (`cnpj-alfanumerico`) tem um único autor, uma única release e nenhuma adoção, o que é risco de manutenção maior do que 20 linhas testadas.
`python-stdnum` é a mais madura, mas é LGPL, não informa o DV esperado e não barra base repetida.
`brutils` traz três dependências de execução sem relação com CNPJ e falha nos casos com máscara.
Uma dependência a mais só se justificaria se fosse claramente melhor, e nenhuma é.

## Implementação

Arquivo: `validador_osc/cnpj.py`.

- `normalizar(cnpj) -> str`: remove espaços, `.`, `/`, `-` e traços Unicode (texto copiado de PDF) e converte a-z para maiúsculas.
- `validar(cnpj) -> ResultadoDV`: verifica formato, depois base repetida, depois DV; devolve `cnpj` normalizado, `valido`, `motivo` (`Motivo.FORMATO`, `Motivo.REPETIDO` ou `Motivo.DV`) e `dv_esperado` quando o motivo é DV.
- `calcular_dvs(base12) -> str`: calcula os 2 DVs de uma base de 12 posições [0-9A-Z]; levanta `ValueError` se a base for inválida.
- `cnpj_da_matriz(cnpj) -> str`: monta o CNPJ da matriz (raiz + `0001` + DVs) a partir de qualquer estabelecimento.

Escolhas de robustez aprendidas na comparação:

- A regra de repetição olha a base de 12 posições, não os 14 caracteres, para barrar casos como `11111111111180`.
- Só letras ASCII são convertidas para maiúsculas, porque `str.upper()` transforma `ı` (U+0131) em `I` e deixaria passar entrada não ASCII.
- O formato usa `[0-9]` explícito em vez de `\d`, que aceitaria dígitos de outros alfabetos.

## Resultado dos testes

Arquivo: `tests/test_cnpj.py` (36 casos).
Cobre os casos da seção 4.5, minúsculas, pontuação variada, DV divergente com DV esperado, sequências repetidas, formatos inválidos, entradas Unicode enganosas, cálculo de DV e montagem da matriz a partir de uma filial (raiz `19131243` + `0001` dá `19131243000197`).

```
> .\.venv\Scripts\python -m pytest -q
....................................                                     [100%]
36 passed in 0.13s
```

Lint (`ruff`) e checagem de tipos (`mypy --strict`) passam sem avisos.
