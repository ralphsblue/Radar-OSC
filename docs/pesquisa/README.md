# Pesquisa das fontes (Fase 0)

Antes de escrever o validador, cada fonte de dados foi testada à mão: formato, estabilidade, limites e casos estranhos.
Esta pasta guarda o resultado dessa pesquisa.

| Pasta | Fonte |
|---|---|
| `brasilapi/` | BrasilAPI, Minha Receita e OpenCNPJ (cadastro da Receita) |
| `portal/` | Portal da Transparência e arquivos diários da CGU (CEIS, CNEP, CEPIM) |
| `tcu/` | Consulta Consolidada e listas do TCU |
| `mapa_osc/` | API do Mapa das OSCs (Ipea) |
| `cebas_dou/` | CEBAS no Diário Oficial e no SisCEBAS |
| `dirigentes/` | Cruzamento de dirigentes com bases de pessoa física |
| `cnae/`, `natureza/`, `dv/` | Tabelas de CNAE, natureza jurídica e dígito verificador |
| `casos/` | Montagem dos casos de referência |

Cada pasta tem uma `ficha.md` com o que foi testado, o resultado e a decisão tomada.
`casos_referencia.md` lista os CNPJs de referência e o resultado esperado de cada verificação.
A versão em JSON desses casos é usada pelos testes de ponta a ponta e fica em `tests/fixtures/casos_referencia.json`.

## Arquivos que não estão no repositório

As respostas cruas das fontes, os downloads oficiais e as amostras ficam fora do git, em `var/pesquisa/`, com a mesma estrutura de pastas.
Quando uma ficha ou um script cita `fase0/...`, o arquivo está aqui (fichas e scripts) ou em `var/pesquisa/` (dados brutos).
Os testes que usam os downloads reais são pulados quando `var/pesquisa/` não existe.
