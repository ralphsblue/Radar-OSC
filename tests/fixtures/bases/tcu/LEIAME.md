# Fixtures das listas do TCU (inidôneos, contas irregulares, inabilitados)

Usadas por `tests/unit/test_listas_tcu.py` e `tests/integracao/test_listas_tcu.py`.

## Origem

Recortes do JSON oficial da Plataforma de Certidões do TCU (`POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-*` com corpo `{}`).
Inidôneos baixados em 02/10/2026; contas irregulares e inabilitados vêm de `fase0/dirigentes/downloads/` (01/10/2026).
O nome segue o padrão `AAAAMMDD_<fonte>.json`, de onde a ingestão local tira a data da base.

## Pessoas físicas

Nenhuma fixture contém CPF completo nem nome real de pessoa física.
Os registros de PF mantêm processo, acórdão e datas reais, mas o nome é fictício e o CPF vem mascarado (`***.XXX.XXX-**`) com 6 dígitos inventados.
Os testes que precisam de CPF completo geram CPFs sintéticos em tempo de execução.

## Casos cobertos

- Inidôneos: registro sem `numeroRegistro` (empresa estrangeira) e uma filial sintética `0002` de ADRIANY R RODRIGUES, mesma raiz da matriz.
- Contas irregulares: nome entre aspas simples, acórdão nulo, acórdãos de 1ª e 2ª Câmara e PF sem CPF.
- Inabilitados: nome com acentos e espaços repetidos e PF sem CPF.
