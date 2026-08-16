# Auditoria documental PNCP 2.5

## Fontes canônicas

| Fonte | SHA-256 | Cobertura |
|---|---|---|
| Manual PNCP 2.5 completo | `26d5a5cff042faf28c09fd10e9edc32eaeca38f565ea8926699aab932e121449` | Documento integral |

## Incompatibilidade retirada do conjunto canônico

O antigo `openapi/api-docs.json`, de SHA-256
`dfe448f39a3d6602d688465d2159fa75233ac56aa447dee115fbbcd2eb4fe7af`,
declarava `info.version: 1.0`. Ele também não apresentava a operação `GET` da
seção 10.5 do Manual 2.5 no caminho da contratação. Em 26 de julho de 2026,
o arquivo foi removido da árvore ativa para impedir que fosse tratado como
contrato 2.5.

O histórico Git preserva a evidência. Um OpenAPI só poderá voltar ao conjunto
canônico por substituição integral, versão declarada compatível, comparação de
cobertura, hash e revisão humana.

## Decisão de consolidação

Em 22 de julho de 2026, os recortes HTML numerados das famílias de compras,
atas e órgãos foram retirados do repositório. À época, eles repetiam conteúdo
preservado no Manual completo e no OpenAPI então presente e criavam duas
referências possíveis para a mesma API.

A ausência dos antigos diretórios `endpoints/` e `openapi/` passou a ser
verificada pelos testes do repositório. A documentação PNCP somente será
atualizada pela substituição controlada de uma fonte integral, com conferência
de versão, cobertura e hash.

## Regras permanentes

- preservar uma única cópia ativa do Manual integral;
- não versionar recortes HTML, ZIPs, diretórios `_files`, CSS ou JavaScript da documentação;
- resolver endpoints e schemas somente pelo artefato local registrado;
- proibir fallback documental para internet;
- não substituir `dataResultadoPncp` por publicação ou atualização;
- ativar novas famílias em eventos posteriores apenas após regra e teste próprios.
