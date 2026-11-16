# Deploy em EC2 com Elastic IP, DuckDNS, nginx e Let's Encrypt

Roteiro passo a passo para colocar o Radar OSC no ar numa instância EC2 da AWS, com IP fixo, domínio gratuito (DuckDNS) e HTTPS (Let's Encrypt).
Assume que você já tem conta na AWS e conta de e-mail para o DuckDNS.
Todo o deploy roda via Docker Compose, reaproveitando o `compose.yaml` e o `Dockerfile` que já existem no projeto.

## Visão geral

```
Internet -> DuckDNS (DNS) -> Elastic IP (fixo) -> EC2
                                                    |
                                       nginx (80/443, Let's Encrypt)
                                                    |
                                      app (127.0.0.1:8000, Docker)
                                            |            |
                                        worker          db/redis (127.0.0.1, Docker)
```

O nginx roda direto na EC2 (fora do Docker) e faz proxy reverso pra `127.0.0.1:8000`, onde o container `app` escuta.
`db` e `redis` ficam só acessíveis de dentro da própria máquina (`127.0.0.1`), nunca expostos à internet.

## 1. Criar o subdomínio no DuckDNS

1. Entre em https://www.duckdns.org e faça login (GitHub, Google etc).
2. Na caixa de texto do topo, escolha um nome (ex.: `validador-osc`) e clique **add domain**. Isso cria `validador-osc.duckdns.org`.
3. Anote o **token** que aparece no topo da página.
   Não precisa dele agora, mas serve se um dia você quiser automatizar atualização de IP (não é o caso aqui, porque vamos usar Elastic IP fixo).
4. Por enquanto, não precisa apontar pra nenhum IP ainda, fazemos isso depois de ter o Elastic IP.

## 2. Criar a instância EC2

1. No Console AWS, vá em **EC2 → Launch instance**.
2. **Name**: `validador-osc`.
3. **AMI**: Ubuntu Server 24.04 LTS (64-bit x86).
4. **Instance type**: `t3.micro` (free tier, 1 GB RAM) é suficiente pra um MVP com pouco tráfego; o passo 6 adiciona um swap de segurança.
   Se notar lentidão depois, trocar para `t3.small` é só parar a instância, mudar o tipo e ligar de novo.
5. **Key pair**: crie uma nova (ex.: `validador-osc-key`), baixe o `.pem` e guarde: é a única forma de entrar via SSH depois.
6. **Network settings → Security group**: crie um novo, com estas regras de entrada:
   - SSH (22): de preferência restrito ao seu IP (`Meu IP`), não `0.0.0.0/0`.
   - HTTP (80): `0.0.0.0/0` (necessário pro Let's Encrypt validar o domínio).
   - HTTPS (443): `0.0.0.0/0`.
7. **Storage**: 20 GiB gp3 (padrão) é suficiente pras bases locais (CGU/TCU/TCE-SP).
8. Clique **Launch instance**.

## 3. Elastic IP

Sem isso, o IP público da instância muda toda vez que ela reinicia, e o DuckDNS fica desatualizado.

1. **EC2 → Elastic IPs → Allocate Elastic IP address** → Allocate.
2. Selecione o IP recém-criado → **Actions → Associate Elastic IP address** → escolha a instância `validador-osc` → Associate.
3. Anote esse IP (ex.: `18.230.x.x`): ele é fixo enquanto o Elastic IP estiver associado à instância.

## 4. Apontar o DuckDNS pro Elastic IP

1. Volte em https://www.duckdns.org, logado.
2. No campo ao lado do seu subdomínio (`validador-osc`), cole o Elastic IP do passo 3 e clique **update ip**.
3. Confirme que propagou: `nslookup validador-osc.duckdns.org` (qualquer terminal) deve devolver o Elastic IP.

Como o IP é fixo (Elastic IP), não precisa de script de atualização automática do DuckDNS, só atualiza de novo se um dia desassociar/recriar o Elastic IP.

## 5. Entrar na instância e instalar o Docker

```
ssh -i validador-osc-key.pem ubuntu@validador-osc.duckdns.org
```

Dentro da instância:

```
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
```

Saia (`exit`) e entre de novo via SSH pra o grupo `docker` valer.
Confirme: `docker compose version` (o Docker Engine moderno já traz o Compose como plugin).

## 6. Swap de segurança (se for usar `t3.micro`)

```
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 7. Clonar o projeto

```
sudo apt install -y git
git clone https://github.com/ralphsblue/Radar-OSC.git validador-osc
cd validador-osc
```

## 8. Configurar o `.env` de produção

**Nunca** reaproveite o `VOSC_JWT_SEGREDO` de desenvolvimento em produção.

```
cp .env.example .env
nano .env
```

Edite pelo menos:

- `VOSC_JWT_SEGREDO`: gere um valor aleatório forte, por exemplo com `openssl rand -hex 32`, e cole o resultado.
- `VOSC_TOKEN_OPERADOR`: defina um valor se for usar o modo operador (vê nomes de dirigentes/evidências brutas); deixe vazio se não for usar agora.
- `VOSC_DATABASE_URL` e `VOSC_REDIS_URL`: **não precisa editar**: o `compose.yaml` já sobrescreve essas duas com os hosts internos do Docker (`db`, `redis`) nos serviços `app` e `worker`.
  O `.env` só é lido fora do Docker; dentro do Compose valem as variáveis declaradas em `environment:`.

Esse `.env` nunca deve ir pro git (já está no `.gitignore`).

## 9. Subir os containers

O `compose.yaml` usa o profile `completo` pros serviços `app` e `worker` (pra não subirem sem querer em `docker compose up` local, que só sobe `db`):

```
docker compose --profile completo up -d --wait
```

Isso sobe `db`, `redis`, `app` e `worker`. Confira:

```
docker compose ps
```

Rode a migração e a primeira carga de bases (demora alguns minutos, baixa arquivos grandes da CGU/TCU):

```
docker compose exec app alembic upgrade head
docker compose exec app validador-osc atualizar-bases
```

Teste local, de dentro da instância:

```
curl -I http://127.0.0.1:8000/
```

Deve devolver `HTTP/1.1 200 OK`.

## 10. Instalar e configurar o nginx

```
sudo apt install -y nginx
```

Copie o template do projeto e troque o domínio:

```
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/validador-osc
sudo sed -i 's/SEU_SUBDOMINIO.duckdns.org/validador-osc.duckdns.org/' /etc/nginx/sites-available/validador-osc
sudo ln -s /etc/nginx/sites-available/validador-osc /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Teste de fora (no seu computador): `http://validador-osc.duckdns.org` já deve mostrar o site, sem HTTPS ainda.

## 11. HTTPS com Let's Encrypt

```
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d validador-osc.duckdns.org
```

O certbot pergunta um e-mail (pra avisos de expiração) e se quer redirecionar HTTP pra HTTPS automaticamente; escolha **sim**.
Ele reescreve `/etc/nginx/sites-available/validador-osc` sozinho, adicionando os blocos de certificado e o redirecionamento.
A renovação é automática (`certbot` instala um timer do systemd); confira com:

```
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

## 12. Subir junto com o boot da instância

Os 4 serviços do `compose.yaml` já têm `restart: unless-stopped`, então o Docker reinicia tudo sozinho se a instância reiniciar ou um container cair.
O serviço `docker` já é habilitado por padrão pelo instalador do passo 5 (`sudo systemctl enable docker` se precisar confirmar).

## 13. Atualizar as bases diariamente

As bases oficiais (CGU, TCU, TCE-SP) precisam ser recarregadas uma vez por dia (mesma lógica do `scripts/agendar_atualizacao.ps1` que já existe pro Windows, aqui via cron do Linux):

```
sudo crontab -e
```

Adicione (ajuste o caminho se clonou em outro lugar):

```
0 6 * * * cd /home/ubuntu/validador-osc && docker compose exec -T app validador-osc atualizar-bases >> /var/log/validador-osc-bases.log 2>&1
```

## 14. Checklist final

- [ ] `https://validador-osc.duckdns.org` abre com cadeado (certificado válido).
- [ ] `docker compose ps` mostra `db`, `redis`, `app` e `worker` todos `Up`/`healthy`.
- [ ] Uma consulta de teste (CNPJ real) funciona de ponta a ponta.
- [ ] Um lote de teste (logado) processa e termina `CONCLUIDO`.
- [ ] `sudo certbot renew --dry-run` passa sem erro.
- [ ] O cron de `atualizar-bases` está instalado (`sudo crontab -l`).

## Problema conhecido: TCU pode bloquear o IP da EC2

Como registrado em `docs/pesquisa/tcu/ficha.md` e em `docs/produto.md` (pendências), o TCU tem um firewall de aplicação que às vezes bloqueia chamadas automatizadas vindas de IP de datacenter (devolve HTTP 200 com uma página de bloqueio em vez do JSON esperado).
Depois do deploy, faça uma consulta de teste e confira se a verificação `tcu_inidoneos`/`cnj_cnia` volta OK ou "indisponível".
Se vier sempre indisponível, é esse bloqueio, não um bug do deploy.
