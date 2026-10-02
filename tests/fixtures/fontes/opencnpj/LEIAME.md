# Fixtures do OpenCNPJ

Respostas reais de `https://api.opencnpj.org`, usadas pelos testes de contrato em `tests/contrato/test_normalizacao_opencnpj.py` e pelo replay dos testes E2E (`tests/e2e/replay.py`).

## Origem e fidelidade

As respostas de CNPJ vêm de `fase0/casos/respostas/<cnpj>/opencnpj.json` (coleta de `fase0/casos/coletar.py`).
Esses arquivos guardam o corpo já decodificado dentro de um envelope `{"meta": ..., "corpo": ...}`, junto com o sha256 dos bytes originais.
Cada fixture foi regravada com `json.dumps(corpo, ensure_ascii=False, separators=(",", ":"))` e só foi aceita quando o sha256 conferiu com o `meta.sha256` gravado na coleta.
Ou seja, os arquivos são byte a byte o corpo HTTP que o OpenCNPJ devolveu (JSON compacto, UTF-8, sem quebra de linha final).

`info.json` é cópia sem alteração de `fase0/brasilapi/respostas/extras/opencnpj_info.json`, que já foi salvo com os bytes crus.

O QSA do OpenCNPJ vem mascarado (`***123456**`); nenhuma fixture contém CPF completo.

## Arquivos

| Arquivo | URL | Coletado em (UTC) | HTTP | sha256 | Caso |
|---|---|---|---|---|---|
| `19131243000197.json` | `/19131243000197` | 2026-10-01 03:06:23 | 200 | `ebec160e4b4e1ff587505dc8c6575c22b58e35928734d00461aeacb232dbf3ba` | Open Knowledge Brasil, associação ativa |
| `00000000000191.json` | `/00000000000191` | 2026-10-01 03:07:15 | 200 | `dc606782ae4945759a5b25666424bed760573af4d60c8893626e4a55a3cfc2d5` | Banco do Brasil, natureza não elegível, QSA grande |
| `08942107000160.json` | `/08942107000160` | 2026-10-01 03:06:44 | 200 | `927edd6dc572b64659586311fe8fe9527216c3a932dfd3ccf3d0ec299311d65a` | Associação baixada com motivo 01 |
| `62779145000270.json` | `/62779145000270` | 2026-10-01 03:09:22 | 200 | `2fba40b769c2add56abcbc564e5261d45cd44b2cabd33e4bb1cebf34ba710df8` | Filial ativa |
| `62779145000190.json` | `/62779145000190` | 2026-10-01 03:09:33 | 200 | `f6ee880ec0199ec962dcb0360f23f47c8868450016c583ac0114d5f103d2359b` | Matriz da filial acima, nome fantasia vazio |
| `00108217000110.json` | `/00108217000110` | 2026-10-01 03:07:23 | 200 | `73dfdaae98597c84bf5f4530ecf7446ca62cb31af80b11ba5755aaf3972c23ba` | Organização religiosa, sem CNAE secundário |
| `04311762000160.json` | `/04311762000160` | 2026-10-01 03:07:45 | 200 | `b2e97f91847a755cc0067affbca15c37d2ef20d3d34663b12b5545528f036f37` | Cooperativa, CNAE `0220903` com zero à esquerda |
| `65478551000100.json` | `/65478551000100` | 2026-10-01 03:08:27 | 200 | `fab469e025d4cfb96cdf29df5310626433845a64a4baf919b05c2e8d60d51582` | Associação aberta em 2026-02-03 |
| `03126200000183.json` | `/03126200000183` | 2026-10-01 03:10:47 | 200 | `84da63b1c5ec370a4a84e5a2d10e6f5312972c8014e3d7e47735cdb540c6286d` | Associação inapta, motivo 63 |
| `03728829000101.json` | `/03728829000101` | 2026-10-01 03:07:04 | 200 | `4aacdf81f444abbef0adf27890678aad6882cd24bd2a40549410f2d802ae01f8` | Associação suspensa, motivo 21 |
| `04955882000108.json` | `/04955882000108` | 2026-10-01 03:09:52 | 200 | `f6a1d1413569fc0d2710d0253bd41bb18147ade8333f484c73a48c326b489291` | Instituto GRPCOM, `data_situacao_cadastral` = `"0"` |
| `04955882000523.json` | `/04955882000523` | 2026-10-01 03:09:45 | 200 | `816c57981c0bd5ba006c3d9f1689d7b0cddb271b0bd72b85490905a65f451fc5` | Filial baixada do Instituto GRPCOM, matriz ativa (C24) |
| `24006302000488.json` | `/24006302000488` | 2026-10-01 03:23:15 | 200 | `ad711534cd2c15207e4396838307316c475b3c14e38143d5f7b07089f8b286eb` | IDEAS, matriz com ordem 0004 (C26) |
| `24006302000135.json` | `/24006302000135` | 2026-10-01 03:23:27 | 200 | `7feb6ede1b9901381effde3a77ac022d4747fed8fc335ab7f1a98fca675ac311` | IDEAS, filial com ordem 0001 (C27) |
| `44551605000570.json` | `/44551605000570` | 2026-10-01 03:12:14 | 200 | `194c0b2286379a274d95d3eb3ee1bd35493882f7d1585f8b0a41372dbf2b91e4` | Instituto Global, filial ativa (C37) |
| `44551605000146.json` | `/44551605000146` | 2026-10-01 03:12:25 | 200 | `d630e8190179b73c50a87c3c4d5b6a45e95ee3b0f160d7d34f4700899ceb47cb` | Instituto Global, matriz da filial acima (C38) |
| `02203539000173.json` | `casos/respostas/02203539000173/opencnpj.json` | 2026-10-01 03:22:53 | 200 | `adf10b4d8819259d9b1d66379fe80594953843ecbc600abe3fa5fffafb0cf4a1` | C28, E2E de sanções |
| `00688001000170.json` | `casos/respostas/00688001000170/opencnpj.json` | 2026-10-01 03:10:12 | 200 | `468497746d8803740d02ef5e9d3de123a7aa952088ef183161a29e64c1359b9e` | C29, E2E de sanções |
| `30994499000160.json` | `casos/respostas/30994499000160/opencnpj.json` | 2026-10-01 03:23:04 | 200 | `a17fe896c3c70a72e9d7743d23ad8e5ad5767df80582b953d8a85081cb39107d` | C30, E2E de sanções |
| `02393242000118.json` | `casos/respostas/02393242000118/opencnpj.json` | 2026-10-01 03:10:35 | 200 | `a31b7c4573e639a96283d11dcaa87a884b5468a32d85dd8cebbca7582b6f5d12` | C31, E2E de sanções |
| `07408449000132.json` | `casos/respostas/07408449000132/opencnpj.json` | 2026-10-01 03:10:58 | 200 | `fd5c824ce3130d2d3fffa7c23835e0198947268bd178a82c7956eac942f4d4ec` | C32, E2E de sanções |
| `09058351000128.json` | `casos/respostas/09058351000128/opencnpj.json` | 2026-10-01 03:11:10 | 200 | `290f1cf4b2878b70245a750714c259eea05dba2e78c862844093c54af7b85a5a` | C33, E2E de sanções |
| `13144375000177.json` | `casos/respostas/13144375000177/opencnpj.json` | 2026-10-01 03:23:38 | 200 | `c7d3b85d09d275fdd66bd589f0b72f9a7154fcb882118166c7c3e259fcec6c64` | C34, E2E de sanções |
| `01081476000167.json` | `casos/respostas/01081476000167/opencnpj.json` | 2026-10-01 03:24:00 | 200 | `de682889cd7b06b5f48c0c720d3ac8b34fe598d538b226e376b785de08861f7b` | C36, E2E de sanções |
| `06287661000126.json` | `casos/respostas/06287661000126/opencnpj.json` | 2026-10-01 03:10:23 | 200 | `2fcdc0f63947f9f959104dcd624702286667359ddc7de36a6ca93417da0c5efe` | C39, E2E de sanções |
| `03463763000167.json` | `casos/respostas/03463763000167/opencnpj.json` | 2026-10-01 03:11:33 | 200 | `0386b13aeaea8789b7e9c9489920baef47ee60cf5344793e97ac7aeb73a04c3f` | C40, E2E de sanções |
| `14112015000156.json` | `casos/respostas/14112015000156/opencnpj.json` | 2026-10-01 03:10:03 | 200 | `ea2853f394bbcd14e3c22ee8cf27263f068be53b9a91484d945b6622547e9528` | C43, E2E de sanções |
| `08928169000118.json` | `casos/respostas/08928169000118/opencnpj.json` | 2026-10-01 03:11:22 | 200 | `d7f4e14d8335eb0092effd0499eeb3dee3afd7d0e416f246cbead3a5c3fabcc5` | C45, E2E de sanções |
| `53524534000183.json` | `casos/respostas/53524534000183/opencnpj.json` | 2026-10-01 03:11:51 | 200 | `67a57fc9ca59be3cdfbc62e2a353d626bfa63eca59878a0f60e5eafc0a0eadbd` | C41, E2E de sanções |
| `21145289000107.json` | `casos/respostas/21145289000107/opencnpj.json` | 2026-10-01 03:12:02 | 200 | `7c8c8667d6fb95b87382d9296bf0cf414485bf443dbf68211f96c1cc0589d168` | C42, E2E de sanções |
| `05051898000140.json` | `casos/respostas/05051898000140/opencnpj.json` | 2026-10-01 03:23:49 | 200 | `2aa0c954c4e9888b3829c9bbc5e08d33f027031f112be71e0eeb8490b97158e8` | C35, E2E de sanções |
| `43337682000135.json` | `casos/respostas/43337682000135/opencnpj.json` | 2026-10-01 03:11:45 | 200 | `45c5d1f0e6fc4a3e389fc52d189c811e7ad98e8e4563c1d25d3c11b3dd6d8868` | C46, E2E de sanções |
| `404_94580730000152.json` | `/94580730000152` | 2026-10-01 03:06:37 | 404 | `51d0a9e3bd9ffc25483790aaffe7a3597e642edd040dddb16aafc324e6e922ed` | CNPJ inexistente, corpo `{"error":"not found"}` |
| `19131243000197_datasets.json` | `/19131243000197?datasets=ceis,cepim,cnep` | 2026-10-01 03:06:24 | 200 | `4fad8b2da01058e89fd8484d58ef755b41c5dce404c155a9e85437a5b045f7d3` | Resposta de `?datasets=`: só as chaves pedidas, sem o cadastro |
| `info.json` | `/info` | 2026-10-01 01:15:24 (data do arquivo) | 200 | `c943a02b664c749d91086d9477da99d32b4b7aa82b2c7dd317403a10aa804d45` | Data do espelho: `last_updated` 2026-09-15T00:54:41.4550104Z |

A coluna sha256 é o hash dos bytes do arquivo; nas respostas de CNPJ ele é igual ao `meta.sha256` gravado na coleta.

## Como renovar

Prefira o comando de gravação de fixtures do projeto (T13) quando existir.
Ao trocar um arquivo, mantenha os bytes exatos da resposta HTTP e atualize esta tabela e os valores esperados nos testes de contrato.
