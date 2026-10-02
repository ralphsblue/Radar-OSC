# Fixtures dos CSVs da CGU (CEPIM, CEIS, CNEP)

Usadas por `tests/unit/test_sancoes_cgu.py` e `tests/integracao/test_bases_locais.py`.

## Origem

As 10 primeiras linhas de dados de cada arquivo vêm de `fase0/portal/amostras/amostra_<CADASTRO>.csv`, extraídas dos arquivos oficiais de 28/09/2026 (CEPIM) e 30/09/2026 (CEIS e CNEP).
Foram regravadas no formato do arquivo oficial: ISO-8859-1, separador `;`, todos os campos entre aspas e quebra de linha CRLF.
O nome segue o do arquivo oficial (`AAAAMMDD_<CADASTRO>.csv`), de onde a ingestão tira a data da base.

O CPF de pessoa física já vem mascarado das amostras (`***.XXX.XXX-**`); nenhuma fixture contém CPF completo.
Os testes que precisam de CPF completo geram CPFs sintéticos em tempo de execução.

## Linhas sintéticas (códigos de sanção 900001 a 900005)

Acrescentadas para cobrir os problemas de qualidade descritos em `fase0/portal/ficha.md`:

- 900001 (CEIS): filial `0002` da PRISMASERV, mesma raiz da matriz 06278833000103.
- 900002 (CEIS): `TIPO DE PESSOA` vazio com documento de 9 dígitos (estrangeiro) e "Sem Informação" na razão social.
- 900003 (CEIS): `TIPO DE PESSOA` vazio com CNPJ de 14 dígitos.
- 900004 (CEIS): pessoa física com acentos, apóstrofo e espaços repetidos no nome.
- 900005 (CNEP): `TIPO DE PESSOA` vazio com documento de 7 dígitos.

As amostras originais já trazem os demais casos: linhas repetidas (79114 no CEIS, 84816 no CNEP), categoria que contradiz a data final (70548 e 79114), multa com vírgula decimal, CNEP sem data final e o CEPIM sem datas, com vários convênios para o mesmo CNPJ.
