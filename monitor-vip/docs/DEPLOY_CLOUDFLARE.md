# Deploy no Cloudflare — GSB Monitor VIP

Este é o guia operacional para colocar o portal no ar sob controle próprio
(Cloudflare Pages + Workers + D1 + R2), sem qualquer dependência de
hospedagens de terceiros que possam sair do ar. Nenhuma regra de negócio,
motor ou hash precisa mudar — o código já é Cloudflare-nativo.

## Pré-requisitos

- Conta na Cloudflare (o plano gratuito comporta os três motores).
- Repositório `gsb-monitor-vip` no GitHub com o conteúdo desta pasta.
- Acesso ao repositório local `compras_gov` e ao diretório `monitor_v2.5_atual`
  (motores locais que alimentam o portal via `sincronizar_monitor_nuvem.py`).

## 1. Criar D1 e R2

No painel Cloudflare, em **Storage & Databases**:

1. **D1 → Create database** → nome `gsb-monitor-vip`. Guarde o `database_id`.
2. **R2 → Create bucket** → nome `gsb-monitor-vip-editais`.

## 2. Criar o projeto Pages

Em **Workers & Pages → Create → Pages → Connect to Git**:

1. Selecione `rvgomes-sp/gsb-monitor-vip` e o branch `main`.
2. Framework preset: **None**.
3. Build command: `npm run build`.
4. Build output directory: `dist/client`.
5. Root directory: `/` (o `package.json` está na raiz do repo).

## 3. Ligar D1 e R2 ao projeto

Em **Settings → Bindings → Add**:

| Tipo    | Variable name | Recurso                        |
| ------- | ------------- | ------------------------------ |
| D1      | `DB`          | database `gsb-monitor-vip`     |
| R2      | `DOCUMENTS`   | bucket `gsb-monitor-vip-editais` |

As variáveis são fixas — o código lê `env.DB` e `env.DOCUMENTS` em
`cloudflare:workers`.

## 4. Definir os três secrets

Em **Settings → Variables and Secrets**, adicione como *Secret*
(não *Variable*):

- `IMPORT_TOKEN` — token qualquer, longo e aleatório. Usado pela ponte
  local para autenticar o `POST /api/import/*`. Ex.:
  `openssl rand -hex 32`.
- `PORTAL_AUTH_SECRET` — segredo HMAC-SHA256 que assina o cookie de sessão.
  Também `openssl rand -hex 32`. Se rotacionado, as sessões vigentes caem.
- `PORTAL_ACCOUNTS` — JSON com `email → sha256(senha)`. Formato exato:

  ```json
  {
    "rvgomes.sp@gmail.com": "<hash>",
    "ana.fonseca@garantiasembarreiras.com": "<hash>"
  }
  ```

  O hash é o `sha256` da senha, codificado em base64-url sem padding — o
  mesmo cálculo usado por `lib/auth.ts:sha256`. Para gerar sem expor a
  senha em histórico de shell, use um Node interativo:

  ```bash
  node -e 'crypto.subtle.digest("SHA-256",new TextEncoder().encode(process.argv[1])).then(b=>console.log(Buffer.from(b).toString("base64url")))' "$(read -s -p senha: p; echo $p)"
  ```

  Cada perfil precisa ter seu próprio hash. Nenhuma senha é gravada no
  código nem neste guia.

## 5. Aplicar o schema no D1

O `db/schema.ts` (drizzle) descreve todas as tabelas. Rode as migrações
existentes contra o D1 remoto:

```bash
npx wrangler d1 migrations apply gsb-monitor-vip --remote
```

Confirme que as tabelas `opportunities`, `feed_metadata`, `outreach`,
`outreach_history`, `proposals`, `counters`, `documents` e `document_jobs`
existem.

## 6. Publicar

Faça `git push` para `main`. O Cloudflare Pages compila e publica
automaticamente. A URL padrão será `https://gsb-monitor-vip.pages.dev`.

Se preferir um domínio próprio, em **Custom domains** adicione o subdomínio
(ex.: `monitor.garantiasembarreiras.com`) e siga as instruções de DNS.

## 7. Reapontar a ponte local

Na máquina onde os motores locais rodam:

```powershell
$env:GSB_SITE_URL      = "https://gsb-monitor-vip.pages.dev"    # ou o domínio próprio
$env:GSB_IMPORT_TOKEN  = "<mesmo valor do secret IMPORT_TOKEN>"
$env:GSB_SITE_BEARER   = "noop"                                  # header ignorado pelo Cloudflare, mas exigido pelo script
python monitor_v2.5_atual/src/sincronizar_monitor_nuvem.py --root monitor_v2.5_atual
```

O `GSB_SITE_BEARER` foi exigência do Sites externo do workspace anterior;
no Cloudflare ele é enviado mas ignorado. Basta um valor não vazio.

## 8. Teste de fumaça

Sem sessão:

- `GET https://<url>/` → deve carregar `/monitor_vip.html` e o JS redirecionar
  para `/login`.
- `GET https://<url>/api/feed` → deve devolver **401** (guard fail-closed).
- `GET https://<url>/api/auth/session` → deve devolver **401**.
- `POST https://<url>/api/import/snapshot` sem header → deve devolver
  **401** de `IMPORT_TOKEN`.

Com sessão (após login):

- Rodrigo (`rvgomes.sp@gmail.com`) → entra → vê o feed.
- Ana (`ana.fonseca@garantiasembarreiras.com`) → entra → vê o feed.
- `POST /api/import/snapshot` com `x-import-token` correto → **200**.

Se os oito comportamentos confirmarem, o ambiente está funcional e Ana e
Rodrigo trabalham em rede sob controle próprio.

## Rollback

O deploy anterior de qualquer commit fica listado em **Deployments** com
um botão *Rollback*. Não há acoplamento a hospedagens externas. Os motores
locais e o repositório `compras_gov` permanecem intactos.

## O que este deploy **não** faz

- Não altera regra comercial, documental ou de coleta.
- Não altera os motores locais (`EVT-007`, documental, comercial).
- Não altera o script de sincronização.
- Não expõe segredo algum no repositório.
