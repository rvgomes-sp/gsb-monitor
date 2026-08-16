# Documentação PNCP 2.5

Fontes locais usadas para construir e auditar o GSB Monitor V2.5.

- `manual/`: Manual de Integração PNCP 2.5 completo.
- `AUDITORIA_PACOTES_ENDPOINTS.md`: integridade, cobertura e decisões de arquivamento.

O Manual completo é a única autoridade documental PNCP ativa e versionada.
Recortes HTML por número de seção foram removidos porque duplicavam essa fonte e
permitiam regressão para uma visão parcial da API. O OpenAPI antes mantido nesta
pasta declarava `info.version: 1.0`, não continha todas as operações documentadas
no Manual 2.5 e foi retirado do conjunto canônico.

Toda consulta deve passar pelo resolvedor local `tools/pncp_local.py`. Se a
informação não estiver no Manual local ou se o hash divergir, a operação falha
sem consultar a internet.
