# Baseline dos três motores — 28/07/2026

Esta linha de base impede que alterações de portal modifiquem silenciosamente
os motores e suas regras.

## Fluxo preservado

```text
EVT-007
→ oportunidade qualificada
→ feed do monitor
→ coleta e leitura documental
→ documento + resultado de garantia
→ inteligência comercial
→ abordagem / proposta
→ histórico com operador autenticado
```

## Motor 1 — EVT-007

- Descoberta por `dataResultadoPncp`.
- Preservação factual e dos nomes oficiais da API.
- Enriquecimento e formação das oportunidades.

Arquivos-base:

- `../src/Descobrir_EVT007_D1.ps1`;
- `../src/Consolidar_EVT007_DadosAbertos.ps1`;
- `../config/comercial/regras_comerciais.json`.

## Motor 2 — Documental

- Consulta de documentos oficiais no PNCP.
- Preservação de originais e hashes.
- Expansão segura, extração de texto e OCR.
- Distinção entre garantia de proposta e garantia de execução.
- Identificação de percentual, seguro-garantia e divergências.

Arquivos-base:

- `../src/processar_documentos_evt007.py`;
- `../config/documentos/documentos_evt007.json`;
- `../config/documentos/regras_garantia.json`;
- `../src/sincronizar_monitor_nuvem.py`.

## Motor 3 — Comercial

- Cenários nominais de garantia.
- Inteligência sobre a empresa e mapa de abordagem.
- E-mail, controle operacional e proposta.

Arquivos-base:

- `public/assets/commercial_intelligence.mjs`;
- `public/data/commercial_intelligence_cases.json`;
- `public/assets/vip_monitor.js`.

## Integração em nuvem

- `POST /api/import/snapshot`: importa feed e estado operacional para D1.
- `POST /api/import/document`: importa os documentos selecionados para R2.
- As duas rotas usam `IMPORT_TOKEN`.
- O painel autenticado consome D1/R2 por suas APIs operacionais.

## Regra de preservação

1. Nenhum filtro, fórmula, percentual, rota ou padrão documental pode mudar por
   consequência de ajuste visual.
2. Mudança deliberada de regra exige decisão registrada e atualização do teste
   de preservação.
3. Coleta, documental, comercial e autenticação devem passar conjuntamente.
4. O operador gravado deve ser o usuário autenticado: Rodrigo Vazquez ou Ana
   Fonseca.

Os hashes e contratos mínimos são verificados em
`tests/integration-preservation.test.mjs`.
