# Ficha da fonte - TCU (Consulta Consolidada de PJ e Relação de Inidôneos)

Fase 0, verificação 9 do spec (capítulos 12 e 20).
Data dos testes: 30/09/2026, entre 22h00 e 22h10 (horário de Brasília), a partir da máquina do projeto (IP residencial).
Toda a descoberta foi feita sem navegador, lendo os bundles JS e chamando os endpoints com httpx.

## Resumo

- A Consulta Consolidada de Pessoa Jurídica tem uma API JSON pública: `GET https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}`.
- Ela é documentada oficialmente pelo TCU na página "Webservices TCU" do portal de dados abertos (https://sites.tcu.gov.br/dados-abertos/webservices-tcu/).
- Não há CAPTCHA, cookie, token nem Referer exigido: só o User-Agent do projeto bastou.
- A Relação de Inidôneos também tem API JSON pública e documentada: `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos`, além de exportação CSV da lista inteira.
- A antiga aplicação Oracle APEX (`contas.tcu.gov.br/ords/f?p=1660:...`) foi desativada pelo TCU em 22/05/2026 e não deve mais ser usada.
- A certidão individual de Licitantes Inidôneos (PDF com código de verificação) na Plataforma de Certidões usa CAPTCHA ALTCHA (prova de trabalho); não foi chamada e não é necessária.
- Selo sugerido para o capítulo 20: JSON oficial documentado, sem autenticação, testado.

## Ficha 25.2 - Fonte principal: Consulta Consolidada de Pessoa Jurídica

| Item | Definição |
|---|---|
| Fonte / etapa | TCU - Consulta Consolidada de Pessoa Jurídica (verificação 9, mais cruzamento das verificações 7 CEIS e 8 CNEP). |
| Tipo | API oficial (JSON documentado em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/ e usado pelo próprio frontend https://certidoes-apf.apps.tcu.gov.br/). |
| URL e método | `GET https://certidoes-apf.apps.tcu.gov.br/api/rest/publico/certidoes/{cnpj}?seEmitirPDF=false` |
| Parâmetros | `{cnpj}` no caminho, só letras maiúsculas e dígitos (o frontend aplica `replace(/[^A-Z0-9]+/g, "")`); não mandar pontuação, porque a barra quebra o caminho. `seEmitirPDF` opcional: `false` devolve `certidaoPDF: null`; `true` devolve o PDF da certidão em base64 no campo `certidaoPDF` (cerca de 21 KB). Alternativa usada pelo frontend para o PDF: mesmo GET com `Accept: application/pdf,application/json`, que devolve o PDF binário. |
| Autenticação | Nenhuma. Headers mínimos testados: apenas `User-Agent: validador-osc-ifsp/0.1 (projeto academico de extensao)`. Sem cookies, sem Referer, sem CSRF, sem CAPTCHA. Opcional: `Accept: application/json`. |
| Limites | Nenhum rate limit observado em cerca de 15 chamadas espaçadas de 2 s. A primeira consulta de um CNPJ leva cerca de 5,5 s (o servidor consulta TCU, CNJ e CGU na hora). Consultas repetidas do mesmo CNPJ em poucos minutos voltam em cerca de 0,04 s com o mesmo `dataHoraGeracaoInMillis`, ou seja, há cache no servidor (duração não medida, pelo menos 3 minutos). Bloqueio de IP de datacenter ainda não testado. |
| Exemplo OK | `respostas/apf_certidoes_19131243000197.json` (Open Knowledge Brasil): as quatro certidões com `situacao: "NADA_CONSTA"`, `seCnpjEncontradoNaBaseTcu: true`. |
| Exemplo RESTRICAO | `respostas/apf_certidoes_28025673000115.json` (ALFATEC SERVICOS LTDA, retirado da lista de inidôneos): `Inidôneos` e `CEIS` com `situacao: "CONSTAM_REGISTROS"` e `observacao` com processo e acórdão (ex.: `"Data da Decisão: 23/07/2025 - 024.778/2024-9 - 1610/2025-PL"`). |
| Exemplo erro / não encontrado | DV inválido: `respostas/apf_certidoes_19131243000198.json`, HTTP 412 com `{"violacoes":[{"codigo":null,"mensagem":"Dígito verificador do CNPJ é inválido","tipo":"ALERTA"}]}`. CNPJ com DV válido mas inexistente: `respostas/apf_certidoes_98765432000198.json`, HTTP 200, todas as certidões `NADA_CONSTA`, mas `seCnpjEncontradoNaBaseTcu: false` e `razaoSocial: null`. |
| Campos usados e interpretação | Ver seção "Estrutura da resposta" abaixo. |
| Aceita alfanumérico? | Parcialmente. `respostas/apf_certidoes_12ABC34501DE35.json`: TCU, CEIS e CNEP respondem; CNIA (CNJ) volta `situacao: "ALFANUMERICO_NAO_SUPORTADO"`. |
| Tempo médio de resposta | Cerca de 5,5 s sem cache, cerca de 0,05 s com cache. Usar timeout de pelo menos 30 s. |
| Problemas conhecidos | (1) CNPJ inexistente volta "nada consta": o motor precisa checar `seCnpjEncontradoNaBaseTcu` e o resultado da BrasilAPI antes de concluir OK. (2) CNIA não aceita CNPJ alfanumérico. (3) Cache do servidor: duas consultas seguidas devolvem o mesmo instante de geração. (4) Ressalva do spec 12.4: "nada consta" não cobre responsáveis não notificados, sanções vencidas ou suspensas por recurso. (5) Resposta de erro 412 usa o formato `violacoes[]` com `tipo` `ALERTA` ou `ERRO`. |
| Data do último teste | 30/09/2026 |

### Estrutura da resposta (HTTP 200)

```json
{
  "certidaoPDF": null,
  "certidoes": [
    {
      "dataHoraEmissao": "30/09/2026 22:02",
      "descricao": "Licitantes Inidôneos",
      "emissor": "TCU",
      "linkConsultaManual": "https://certidoes.apps.tcu.gov.br/lista-inidoneos",
      "observacao": null,
      "situacao": "NADA_CONSTA",
      "tempoGeracao": 16,
      "tipo": "Inidôneos"
    }
  ],
  "cnpj": "19.131.243/0001-97",
  "dataHoraGeracaoInMillis": 1790816539692,
  "nomeFantasia": null,
  "razaoSocial": "OPEN KNOWLEDGE FOUNDATION BRASIL",
  "seCnpjEncontradoNaBaseTcu": true,
  "uf": null
}
```

A lista `certidoes` traz sempre quatro itens, identificados por `tipo`: `Inidôneos` (TCU), `CNIA` (CNJ), `CEIS` e `CNEP` (Portal da Transparência).
A lista de tipos também vem de `GET /api/rest/publico/tipos-certidoes` (`respostas/apf_tipos-certidoes.json`).
`tempoGeracao` está em milissegundos.

Valores de `situacao` encontrados no código do frontend e nas respostas:

| `situacao` | Interpretação no motor |
|---|---|
| `NADA_CONSTA` | OK para aquele cadastro. |
| `CONSTAM_REGISTROS` | RESTRICAO. Mostrar `observacao` (processo, acórdão, prazo). Observado nas respostas; o frontend trata qualquer valor não listado mostrando `observacao`. |
| `SISTEMA_INDISPONIVEL` | INDISPONIVEL para aquele cadastro, com `linkConsultaManual`. |
| `ERRO` | INDISPONIVEL para aquele cadastro, com `linkConsultaManual`. |
| `ALFANUMERICO_NAO_SUPORTADO` | NAO_VERIFICADO para aquele cadastro (hoje só CNIA). |
| `CNPJ_NAO_ENCONTRADO_NO_TCU` | INDISPONIVEL (o frontend manda procurar a Ouvidoria do TCU). |
| qualquer outro | Tratar como INDISPONIVEL e registrar para revisão. |

Regras adicionais:

- `seCnpjEncontradoNaBaseTcu: false` não é restrição, mas impede concluir OK sozinho: cruzar com a BrasilAPI (verificação 2).
- HTTP 412 com `violacoes`: CNPJ inválido; o motor já barra isso antes na verificação 1.
- Timeout, 5xx ou JSON inválido: INDISPONIVEL para a verificação inteira, com link https://certidoes-apf.apps.tcu.gov.br/.
- `SISTEMA_INDISPONIVEL` e `ERRO` não foram reproduzidos; só se sabe que existem pelo código do frontend.

## Ficha 25.2 - Fonte alternativa: Relação de Licitantes Inidôneos (Plataforma de Certidões)

| Item | Definição |
|---|---|
| Fonte / etapa | TCU - Relação de Licitantes Inidôneos (verificação 9, cruzamento e fallback). |
| Tipo | API oficial (JSON documentado em https://sites.tcu.gov.br/dados-abertos/webservices-tcu/), mais endpoints do frontend https://certidoes.apps.tcu.gov.br/lista-inidoneos. |
| URL e método | Oficial: `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos`. Paginado (usado pelo frontend): `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos-com-paginacao?paginaAtual=1&tamanhoPagina=50`. CSV da lista inteira: `POST https://certidoes.apps.tcu.gov.br/api/publico/responsaveis-inidoneos/exportar-para-csv?paginaAtual=1&tamanhoPagina=50000`. |
| Parâmetros | Corpo JSON. `{}` devolve tudo. Filtros: `cnpj`, `cpf`, `nome`, `uf`, `municipio` (segundo a página oficial). `cnpj` aceita com ou sem pontuação (testado com `28.025.673/0001-15`). |
| Autenticação | Nenhuma. Só `User-Agent` e `Content-Type: application/json` (httpx põe sozinho). Sem CAPTCHA nesses endpoints. |
| Limites | Nenhum observado. Respostas em cerca de 0,05 s (2,4 s na primeira chamada da lista inteira). Lista com 129 registros em 30/09/2026 (128 CNPJs). |
| Exemplo OK | `respostas/inidoneos_oficial_cnpj_19131243000197.json`: `[]`. Paginado: `respostas/inidoneos_lista_cnpj_19131243000197.json` com `totalElementos: 0`. |
| Exemplo RESTRICAO | `respostas/inidoneos_oficial_cnpj_28025673000115.json`: um item com `nome`, `numeroRegistro`, `numeroProcessoFormatado`, `numeroAcordaoFormatado`, `dataAcordao`, `dataTransitoEmJulgado`, `dataFinalSancao`, `linkDeliberacoesProcesso`, `linkAcompanhamentoProcesso`. |
| Exemplo erro / não encontrado | Não encontrado é `[]` (HTTP 200). Erro não reproduzido. |
| Campos usados e interpretação | Lista não vazia: RESTRICAO, com processo, acórdão e `dataFinalSancao`. Lista vazia: OK para Inidôneos TCU. |
| Aceita alfanumérico? | Não testado. O frontend normaliza com `replace(/[^A-Za-z0-9]/g, "").toUpperCase()`, o que sugere suporte. |
| Tempo médio de resposta | Cerca de 0,05 s. |
| Problemas conhecidos | CSV em cp1252, separador `|`, primeira linha `sep=|`. A lista só traz sanções vigentes. |
| Data do último teste | 30/09/2026 |

### Uso sugerido no MVP

- Principal: Consulta Consolidada (uma chamada cobre Inidôneos TCU, CNIA, CEIS e CNEP).
- Alternativa e cache: baixar o CSV da lista inteira uma vez por dia (35 KB) e consultar localmente; serve de fallback se a Consulta Consolidada cair.

## Relação de Inidôneos antiga (Oracle APEX, contas.tcu.gov.br/ords)

- `https://contas.tcu.gov.br/ords/f?p=1660:5` redireciona para `f?p=1660:5:0:` com a mensagem "A aplicação foi colocada como indisponível no dia 22/05/2026 às 12:00:01, pois não está inclusa no Portfólio de Serviços de TI" (`respostas/ords/1660_5.html`).
- `https://contas.tcu.gov.br/ords/f?p=1660:2` devolve HTTP 500 para o User-Agent do projeto (`respostas/ords/1660_2.html`).
- Num único teste de diagnóstico com `User-Agent: Mozilla/5.0`, o firewall de aplicação do TCU devolveu "Requisição rejeitada" (`respostas/ords/1660_2_ua_mozilla.html`); não houve nova tentativa.
- Não foi encontrado endpoint ORDS REST nem catálogo OpenAPI (`/ords/open-api-catalog/` dá 404).
- Conclusão: a fonte alternativa do capítulo 20 deve ser trocada por `certidoes.apps.tcu.gov.br`; o fallback com Playwright do item 20.3 deixa de ser necessário.

## CAPTCHA

- `certidoes-apf.apps.tcu.gov.br`: nenhuma ocorrência de `captcha`, `recaptcha`, `grecaptcha`, `hcaptcha`, `turnstile` ou `sitekey` no bundle.
- `certidoes.apps.tcu.gov.br`: usa ALTCHA (`<altcha-widget challenge="/api/publico/captcha">`) apenas na emissão de certidões individuais (`POST /api/publico/certidoes/licitantes-inidoneos/pessoa-juridica`, `.../processos/...`, `.../inabilitados`), que mandam o campo `captcha` no corpo.
- Esses endpoints com CAPTCHA não foram chamados e o projeto não precisa deles.
- Listas, filtros por CNPJ e exportação CSV não usam CAPTCHA.

## Integrações de terceiros

- Infosimples documenta a mesma fonte (https://infosimples.com/consultas/tcu-consolidada-pj/) com parâmetros `cnpj` e `aceita_resultado_parcial` e campos `certidoes[]` (emissor, descricao, resultado_consulta, observacao, certidao_orgao_original_url, tempo_geracao), `razao_social`, `nome_fantasia`.
- Isso bate com o JSON real; `aceita_resultado_parcial` é recurso da Infosimples, não do TCU.

## Scripts e arquivos

- `baixar_frontend.py`: baixa HTML e bundle JS da Consulta Consolidada para `respostas/frontend/`.
- `testar_certidoes_apf.py [cnpj ...]`: chama tipos de certidão e a consulta consolidada, salva JSON e `.meta.json` (URL, headers, status, tempo, data, sha256).
- `testar_lista_inidoneos.py [cnpj ...]`: chama o endpoint oficial, o paginado e o CSV da lista.
- `respostas/frontend_certidoes/`: HTML e bundle JS da Plataforma de Certidões, de onde saíram os endpoints da lista.
- `respostas/apf_certidao_19131243000197.pdf`: PDF da certidão consolidada (GET com `Accept: application/pdf`).
- `respostas/apf_certidoes_19131243000197_seEmitirPDF_true.json`: mesma consulta com o PDF em base64.

## Passo a passo manual

A descoberta já foi concluída sem navegador, então o passo manual virou só uma conferência opcional, que leva uns 3 minutos.
O objetivo é confirmar que o navegador não manda nenhum header extra que o servidor passe a exigir e guardar um exemplo de CNIA com ocorrência, que não deu para obter sem navegador.

1. Abrir https://certidoes-apf.apps.tcu.gov.br/ no Chrome.
2. Pressionar F12, ir na aba **Network**, marcar **Preserve log** e escolher o filtro **Fetch/XHR**.
3. Digitar 19131243000197 no campo CNPJ e pressionar Enter.
4. Conferir que aparece uma requisição `GET .../api/rest/publico/certidoes/19131243000197` (sem `seEmitirPDF`).
5. Clicar com o botão direito nela, escolher **Copy > Copy as cURL (bash)** e colar num editor.
6. Apagar do cURL as linhas `-H 'cookie: ...'` e `-b '...'` (cookies pessoais, incluindo os do Google Analytics).
7. Colar de volta no chat: o cURL sem cookies e o conteúdo da aba **Response** dessa requisição.
8. Opcional: se souber de um CNPJ de empresa com condenação por improbidade no CNJ, repetir os passos 3 a 7 com ele e colar a resposta, para termos o exemplo RESTRICAO do CNIA.

Não precisa fazer nada na Relação de Inidôneos: os endpoints estão documentados pelo TCU e testados.
Fica pendente, fora do DevTools, testar a Consulta Consolidada a partir do servidor onde o projeto vai rodar, para saber se o IP de datacenter é bloqueado.
