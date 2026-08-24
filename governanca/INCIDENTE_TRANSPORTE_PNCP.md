# Incidente de transporte — PNCP (2026-08-25)

> Registro técnico. **Distinto** do problema anterior (httpx + `Accept-Encoding` gzip/br,
> que era dependente de transporte/compressão). Não misturar os dois diagnósticos.

## O que está PROVADO (evidência)
Mesma URL do primeiro GET do coletor (`/api/consulta/v1/contratacoes/atualizacao?...mod=4&pagina=1`):

| Camada | Resultado |
|---|---|
| DNS | ✅ resolve `pncp.gov.br` → 189.9.176.245 |
| TCP :443 | ✅ `Test-NetConnection` TcpTestSucceeded=True |
| Proxy de ambiente | ✅ nenhum (`HTTP(S)_PROXY` vazios) |
| Egress geral (GitHub) | ✅ HTTP 200 em ~0,2s |
| `curl -v` (Schannel) | conecta, **request enviado**, `remote party requests renegotiation` → **trava sem resposta** (http=000, 15–20s) |
| `httpx` OpenSSL (`trust_env=False`) | **ReadTimeout** ~20s (conectou, request enviado, sem resposta) |
| `urllib` | idem (pendura) |
| curl **TLS 1.2** forçado | http=000, 20s |
| curl **TLS 1.3** forçado | http=000, 20s |

**Fato objetivo:** TCP conecta, a requisição sai, e a origem **não devolve resposta HTTP utilizável nesse egress**.
Não é versão de TLS (1.2 e 1.3 falham igual), não é biblioteca (curl/Schannel E Python/OpenSSL falham),
não é proxy, não é DNS, não é porta.

## O que NÃO está provado
Que seja "bloqueio do NOSSO IP". É **compatível** com throttling/mitigação por IP na borda do PNCP
(possível WAF/anti-bot que silencia a conexão em vez de retornar HTTP 429), mas **não comprovado**.
A prova exige **A/B de egress**: mesma URL por outra rede (ex.: hotspot). Se responder na outra saída
em poucos segundos → evidência de comportamento por rota/IP/edge. Enquanto não houver esse controle,
tratamos como **degradação temporária de transporte no egress atual**.

Contexto que torna a hipótese de throttling plausível: fizemos **milhares de requests em poucas horas**
(varreduras de páginas completas + drill) durante o desenvolvimento.

## Régua de produção (conservadora — implementar no runner diário)
```
concorrência: 1 request por vez
delay base: 300–700 ms entre chamadas
jitter: +0–500 ms
tentativas: máx 3
read timeout: 20–30 s   | connect timeout: 10 s
circuit breaker: após 3–5 timeouts consecutivos -> cooldown 2–5 min
checkpoint persistente por contratação (retomar sem re-bater tudo)
log por chamada: url + attempt + elapsed  (nunca silêncio)
```
Só aumentar para concorrência 2–4 **depois** de estabilidade comprovada — nunca o contrário.
Outro IP pode resolver, mas **não é estratégia de contorno**: o correto é reduzir pressão e respeitar a origem.

## Estado congelado
- **Classificador v2:** 12/12 golden set + FPs corrigidos. Sem novo ajuste antes da prática.
- **Cliente/resiliência:** timeout curto, retry curto, progresso visível, teto de páginas. Nunca mais 3h em silêncio.
- **Validação 20/08:** ⏸ bloqueada pela falha de resposta no egress atual. Retomar só quando **um probe simples** voltar a responder.
