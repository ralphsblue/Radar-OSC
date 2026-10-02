# Fixtures do TCU (Consulta Consolidada de Pessoa Jurídica)

Respostas reais de `GET https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false`, usadas por `tests/contrato/test_normalizacao_tcu.py`, `tests/unit/test_fonte_tcu.py` e pelo replay dos testes E2E (`tests/e2e/replay.py`).
No replay, CNPJ sem fixture aqui recebe HTTP 503: o teste trata a ausência de forma explícita, sem inventar NADA_CONSTA.

## Origem e fidelidade

Há duas origens na Fase 0, e as duas gravaram o sha256 dos bytes originais.

- `fase0/tcu/respostas/apf_certidoes_<cnpj>.json`: corpo cru, com os metadados (incluindo `sha256`) em `apf_certidoes_<cnpj>.meta.json`.
Essas fixtures são cópia sem alteração do arquivo da Fase 0.
- `fase0/casos/respostas/<cnpj>/tcu.json` e `fase0/casos/respostas/cnia_busca/tcu_<cnpj>.json`: corpo já decodificado dentro de um envelope `{"meta": ..., "corpo": ...}`.
Cada fixture foi regravada com `json.dumps(corpo, ensure_ascii=False, separators=(",", ":"))` em UTF-8 e só foi aceita quando o sha256 conferiu com o `meta.sha256` da coleta.

Nos dois casos os arquivos são byte a byte o corpo HTTP que o TCU devolveu (JSON compacto, UTF-8, sem quebra de linha final).
O teste `test_fixtures_sao_os_bytes_da_coleta` confere o sha256 de cada arquivo contra a tabela abaixo.

## Arquivos

| Arquivo | Origem | Coletado em (UTC) | HTTP | sha256 | Caso |
|---|---|---|---|---|---|
| `19131243000197.json` | `casos/respostas/19131243000197/tcu.json` | 2026-10-01 03:06:25 | 200 | `757622ba7b54f1950c20cde4c3af3a99338f0f9349b4fc3b7ec6f964e08b07fa` | Open Knowledge Brasil, quatro certidões NADA_CONSTA |
| `28025673000115.json` | `tcu/respostas/apf_certidoes_28025673000115.json` | 2026-10-01 01:07:20 | 200 | `130f20384b61eb7cd50b2ec14a5e129d7932bbd82e0295cf6ffd46661e9d0987` | ALFATEC, Inidôneos e CEIS com registro |
| `21145289000107.json` | `casos/respostas/21145289000107/tcu.json` | 2026-10-01 03:12:04 | 200 | `31329cfefe010208ae1b85f52890d1bc0e6730a1cf458ab11138ff3f949ddbdd` | IMDC, Inidôneos e CEIS com três registros separados por `<br/>` |
| `53524534000183.json` | `casos/respostas/53524534000183/tcu.json` | 2026-10-01 03:11:53 | 200 | `5d8c02f7eea28409ec27601440b67ddaad37c91d09c774d70de134887ae7321e` | Santa Casa de Pacaembu, CEIS e CNEP, todos "(Sem informação)" |
| `03126200000183.json` | `casos/respostas/03126200000183/tcu.json` | 2026-10-01 03:10:49 | 200 | `6a58172447bb072ddeab9c12316d08d416b9f226b40cd8fa4f77e3863d9e971c` | Associação Plural, CEIS expirado com data (18/11/2021) e espaço final |
| `05051898000140.json` | `casos/respostas/05051898000140/tcu.json` | 2026-10-01 03:23:51 | 200 | `6804e54144783336446db0d9c42be1118810eb6c72f005b20e810c57150aaee8` | C35, CNIA com um processo e CEIS |
| `43337682000135.json` | `casos/respostas/43337682000135/tcu.json` | 2026-10-01 03:11:48 | 200 | `d88d61d34eb4ca4bb070d26e0d5f0074961936933750d4beccd43044ebffc1d2` | AVAPE, CNIA com dois processos e CEIS com quatro registros |
| `25705450000100.json` | `casos/respostas/cnia_busca/tcu_25705450000100.json` | 2026-10-01 03:05:06 | 200 | `121966fb4e9fb269bce5fe551117c36397ed6cdfadfd19122ad8ad1ea0f87b77` | CNIA com processo de 13 dígitos, fora do padrão CNJ de 20 |
| `98765432000198.json` | `tcu/respostas/apf_certidoes_98765432000198.json` | 2026-10-01 01:07:24 | 200 | `41facde86d53d0e0dd3dbee1d8ac6d5cafc910cf59f05eef2523bbb133a7b0c4` | DV válido, inexistente: `seCnpjEncontradoNaBaseTcu: false`, tudo NADA_CONSTA |
| `12ABC34501DE35.json` | `tcu/respostas/apf_certidoes_12ABC34501DE35.json` | 2026-10-01 01:07:31 | 200 | `7a517abbdac8a8188355765b7134c3c50d80803eb61fe6b87b5f1ddb82403b56` | Alfanumérico: CNIA `ALFANUMERICO_NAO_SUPORTADO`, fora da base do TCU |
| `24006302000488.json` | `casos/respostas/24006302000488/tcu.json` | 2026-10-01 03:23:17 | 200 | `191bc7331f532ef092a6a5330296a23636e00544577f4467b15e65654061229a` | C26, E2E de sanções |
| `24006302000135.json` | `casos/respostas/24006302000135/tcu.json` | 2026-10-01 03:23:28 | 200 | `15ff34ca0bdfdd74905ab8b10ef85cbd9b2b21c43849cc956148bf667ea4139e` | C27, E2E de sanções |
| `02203539000173.json` | `casos/respostas/02203539000173/tcu.json` | 2026-10-01 03:22:55 | 200 | `973afb2e2f1c5089b3b476518b967190945edaebe64c5ebb05e6d1c51a532e5a` | C28, E2E de sanções |
| `00688001000170.json` | `casos/respostas/00688001000170/tcu.json` | 2026-10-01 03:10:14 | 200 | `3b03d11faeb665aecb8f71cc1801b302cc3c2fe54e001cdf0153cb180f00a7b8` | C29, E2E de sanções |
| `30994499000160.json` | `casos/respostas/30994499000160/tcu.json` | 2026-10-01 03:23:06 | 200 | `7c3468245970d24b650559cda3f35a855fbfd71e74e85ddd3a0749e09c15c4dc` | C30, E2E de sanções |
| `02393242000118.json` | `casos/respostas/02393242000118/tcu.json` | 2026-10-01 03:10:38 | 200 | `09300d894759aba84d3296af86cf0cf43deda32890ae4ec8040d8231976e41b9` | C31, E2E de sanções |
| `07408449000132.json` | `casos/respostas/07408449000132/tcu.json` | 2026-10-01 03:11:01 | 200 | `1cbc405c99aa459841354622f7cac22739bf2391b2345cc279654f17929aebef` | C32, E2E de sanções |
| `09058351000128.json` | `casos/respostas/09058351000128/tcu.json` | 2026-10-01 03:11:12 | 200 | `be647a47de3e5c722305c4483a991a6d7d54b4642f14b263d7265017e6d1636b` | C33, E2E de sanções |
| `13144375000177.json` | `casos/respostas/13144375000177/tcu.json` | 2026-10-01 03:23:40 | 200 | `1bcc7e33fe97f8774e6eed9c3e3e36bcf38c428f446311d6a207396d0de61ac8` | C34, E2E de sanções |
| `01081476000167.json` | `casos/respostas/01081476000167/tcu.json` | 2026-10-01 03:24:02 | 200 | `69b33cf6b6f5ba9ac3c26affef979006f8cd8767fe4cf40655ee9eb6055ee12b` | C36, E2E de sanções |
| `44551605000570.json` | `casos/respostas/44551605000570/tcu.json` | 2026-10-01 03:12:16 | 200 | `cb193c6df7394798e58af58f0171874c831d4e2003d55db22eea6a26e689a8ff` | C37, E2E de sanções |
| `44551605000146.json` | `casos/respostas/44551605000146/tcu.json` | 2026-10-01 03:12:27 | 200 | `73de097c2e079d61a9097bfb0a0801d2203a9fcfa9c8be201b3032f9e8562234` | C38, E2E de sanções |
| `06287661000126.json` | `casos/respostas/06287661000126/tcu.json` | 2026-10-01 03:10:26 | 200 | `afae308e9b6d5056431d6b2783b91eaf0ade756548f006d22811102599326825` | C39, E2E de sanções |
| `03463763000167.json` | `casos/respostas/03463763000167/tcu.json` | 2026-10-01 03:11:36 | 200 | `fbf06f8f1e449bf02358c32e425b6ba9425d3d5681fb679d90321957c2efe7e2` | C40, E2E de sanções |
| `14112015000156.json` | `casos/respostas/14112015000156/tcu.json` | 2026-10-01 03:10:06 | 200 | `098d11191978478760138793125290e3eddb880f06ede67e612956c927123b61` | C43, E2E de sanções |
| `08928169000118.json` | `casos/respostas/08928169000118/tcu.json` | 2026-10-01 03:11:24 | 200 | `a6b56a460ab5fe49dca65b33fbadd7f1822cb4f8a90dd7292241f238d9440d04` | C45, E2E de sanções |
| `412_19131243000198.json` | `tcu/respostas/apf_certidoes_19131243000198.json` | 2026-10-01 01:07:22 | 412 | `cec1950ae167504773c8f9db4f88093d87173b587d7bddee811a1e5eae983f85` | DV inválido, corpo `violacoes[]` |

As situações `ERRO`, `SISTEMA_INDISPONIVEL` e `CNPJ_NAO_ENCONTRADO_NO_TCU` nunca foram observadas (só aparecem no código do frontend) e por isso não têm fixture; os testes as cobrem alterando a fixture da Open Knowledge Brasil.

## Como renovar

Prefira o comando de gravação de fixtures do projeto (T13) quando existir.
Ao trocar um arquivo, mantenha os bytes exatos da resposta HTTP e atualize esta tabela, o dicionário `SHA256` de `tests/contrato/test_normalizacao_tcu.py` e os valores esperados nos testes.
