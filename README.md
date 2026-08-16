# GSB Monitor — Universo VIP

Sistema de inteligência de contratações públicas para prospecção proativa
de seguro-garantia. Monitora o ciclo de compras públicas (PNCP), classifica
oportunidades de homologação (EVT-007) e as encaminha para ação comercial.

**Vazquez & Fonseca** (corretora) · **Vieira Mendonça** (consultoria)

---

## Estrutura

```
coletor/     Coleta do PNCP (evt007_collect_pncp.py) — o motor de captura
motor/       Regras de negócio (evt007_rules_v3.py) — classifica e roteia
config/      Catálogos e parâmetros (gsb_config, familias_catalogo)
banco/       Migrações SQL do PostgreSQL/Supabase (001..005)
monitor/     Interface web v2.5 (monitor_vip.html + assets + data)
ferramentas/ Utilitários (exporta_xls.py)
docs/        Documentação técnica (manual PNCP v2.5)
governanca/  Regras de negócio, matriz dos 14 eventos, arquitetura
```

## Como rodar a coleta

```bash
# definir a conexão (use variável de ambiente, nunca senha no código)
export DATABASE_URL="postgresql://usuario:senha@host:5432/banco"

# coletar o topo (>10MM, rota Vazquez & Fonseca)
python coletor/evt007_collect_pncp.py --date 2026-08-12 --band vf

# classificar
python motor/evt007_rules_v3.py

# exportar para XLS
python ferramentas/exporta_xls.py
```

## Como abrir o monitor

O monitor lê dados via `fetch`, então precisa de um servidor local
(não abrir o arquivo direto — o navegador bloqueia por CORS):

```bash
cd monitor
python -m http.server 8080
# abrir http://localhost:8080/monitor_vip.html
```

## Regras de negócio (resumo)

- **Piso R$ 1 MM.** Rota: >10MM → Vazquez & Fonseca; 1–10MM → Vieira Mendonça
- **Elegibilidade:** porte "Demais" + naturezas SA/Ltda (2046, 2054, 2062)
- **Filtro por CASO**, não por item (contrato grande = muitos itens pequenos)
- **Gatilho 85%:** homologado/estimado do ITEM < 0,85 → adicional de garantia
- Ver `governanca/REGRAS_NEGOCIO_EVT007.md` para o detalhe

## Roadmap

- [x] EVT-007 Homologação (coleta + motor + monitor)
- [ ] Memória: backend Supabase (persistir funil, repique, contato)
- [ ] Rotina: coleta automática diária
- [ ] Proativo: sistema cobra o próximo passo
- [ ] Econodata: enriquecimento de contato (CNPJ → decisor/tel/email)
- [ ] Motor de editais: leitura automática do TR
- [ ] Demais eventos do ciclo (EVT-001 a EVT-014)
