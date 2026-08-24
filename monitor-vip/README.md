# GSB Monitor VIP — portal

Portal web do GSB Monitor. Consome os três motores (EVT-007, documental,
comercial) via D1/R2 e apresenta o painel autenticado para Rodrigo Vazquez
(Diretor do Projeto) e Ana Fonseca (Diretora Institucional).

Executa sobre [vinext](https://github.com/cloudflare/vinext) e é publicado no
**Cloudflare Pages/Workers**. Não depende de hospedagens externas ao seu
próprio Cloudflare + GitHub.

## Deploy

Passo a passo do painel Cloudflare (Pages, D1, R2, secrets, teste de fumaça):
[docs/DEPLOY_CLOUDFLARE.md](docs/DEPLOY_CLOUDFLARE.md).

## Preservação

A linha de base dos três motores e as regras invioláveis estão em
[docs/BASELINE_TRES_MOTORES_20260728.md](docs/BASELINE_TRES_MOTORES_20260728.md).
Nenhuma alteração de portal pode mudar filtro, fórmula, percentual, rota ou
padrão documental. O teste [tests/integration-preservation.test.mjs](tests/integration-preservation.test.mjs)
verifica isso a cada commit por hash SHA-256.

## Ambiente local

```bash
npm install
npm run dev        # servidor de desenvolvimento
npm run build      # gera dist/ para o Cloudflare
npm test           # roda os testes de integração e preservação
npm run lint
```

Requer Node.js `>=22.13.0`. Em desenvolvimento local sem os secrets, as APIs
sensíveis devolvem `503` propositalmente (fail-closed). Para exercitar o
fluxo autenticado localmente, defina `PORTAL_AUTH_SECRET` e `PORTAL_ACCOUNTS`
como faria no Cloudflare (ver guia de deploy).

## Estrutura

- `app/` — App Router (Next.js 16 via vinext)
- `app/api/` — rotas D1/R2, autenticação e ponte de importação
- `lib/auth.ts` — cookies HMAC, perfis institucionais
- `lib/require-session.ts` — guard fail-closed usado em toda rota sensível
- `public/` — cliente estático do monitor (VIP e ativos)
- `db/schema.ts` — schema Drizzle das tabelas D1
- `worker/` — entrypoint Cloudflare Worker
- `tests/` — integração, motor comercial e preservação
- `docs/` — baseline, guia de deploy e demais registros

## Autenticação

Cookie HMAC assinado (`gsb_session`), validade de 12h, `httpOnly + Secure +
SameSite=Lax`. As rotas `/api/*` exceto `/api/auth/*` e `/api/import/*`
exigem sessão. `/api/import/*` é guardada apenas por `IMPORT_TOKEN` e serve
a ponte local → nuvem (`src/sincronizar_monitor_nuvem.py`).

## Repositórios relacionados

- Este repo (`gsb-monitor-vip`): apenas o portal.
- [`compras_gov`](https://github.com/rvgomes-sp/compras_gov): motores
  EVT-007, docs PNCP 2.5, tooling local.
