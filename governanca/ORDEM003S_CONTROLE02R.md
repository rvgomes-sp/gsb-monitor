# Ordem 003-S / Controle 02-R

Destinatário: B.Mentor. Autor: Curador.

## Contrato de execução

Entrada canônica: `coletor/esteira_evt007.py`. Recebe `--date 2026-09-09`,
`--catser CAMINHO` e `--output DIRETORIO_NOVO`. `--persist` habilita o destino
factual e de identidade após preflight, mediante DATABASE_URL do destino confirmado.
Dependência somente para persistência: psycopg 3 do ambiente do coletor.

O programa coleta toda a janela permitida por `evt007_collect_comprasgov.py`.
Mantém seu filtro CNPJ preexistente, seu mapeamento e a chave de resultado.
Não equivale a todos os publicadores PNCP. O corte é estritamente por resultado
`homologated_total_value > 10000000`. Não utiliza objeto ou garantia na seleção.

Paginação inconsistente, datas divergentes e chaves factuais conflitantes param a
execução. Repetições factuais idênticas são contabilizadas. Os bytes HTTP são
preservados antes da interpretação em cada execução. Dados anteriores não são
sobrescritos por rerun.

Item: chave JSON compacta `[case_id,item_number]`; aquisição uma vez por item por
execução. `idCompra` e `idCompraItem` são extraídos do source_payload; nunca
concatenados/inventados. A rota 2.1 admite `tipo=idCompra` ou
`tipo=numeroControlePNCPCompra`, ambos documentados no contrato preservado.
O retorno deve convergir com contratação, número do item e identificadores usados.
Multiplicidade de observações é preservada e resulta em AQUISICAO_IDENTIDADE_FALHOU.

CERT-NS-001: somente S literal produz CATSER; somente M literal produz CATMAT.
Material é preservado sem consulta de catálogo. Valores fora do contrato não são
normalizados. Código inteiro JSON ou string decimal canônica é comparado por
igualdade com codigoServico. Valores como 05622, 5622.0, espaços e booleanos são
rejeitados, com bruto preservado. Código ausente não implica inexistência.

Snapshot CATSER SHA-256 obrigatório:
`f3cd884220115be97fd7782a25e799d8c64390786794d27c3fef53806e67f264`.
Carregamento verifica hash, schema, linhas e unicidade antes de qualquer lookup.
Falha bloqueia os lookups seguintes naquela execução.

## Preservação e SQL

`esteira_evt007_legacy.py` é cópia byte a byte da antiga entrada, retida somente
como histórico e nunca importada pela nova entrada. Seus efeitos históricos
continuam perigosos: não executar como parte desta ordem.
classificador_biblioteca.py, inferencia.py e tabelas antigas permanecem intactos.

`banco/evt007_item_identity_candidate.sql` é candidato não aplicado.
O Supabase CLI não estava disponível; a tentativa de obtê-lo expirou. Não foi
inventado um número de migration aplicado. Gerar uma migration com o CLI quando
o destino factual for confirmado, incorporar o candidato e validar no PostgreSQL.

O SQL exige a existência de gsb.evt007_results e cria somente a identidade,
observações imutáveis por execução e uma view de JOIN. Não cria uma tabela
factual substituta. RLS habilitada nas novas tabelas; view security_invoker;
nenhum acesso novo para anon/authenticated. Nenhuma escrita no Monitor.

A identidade base conserva a primeira observação. Novas observações ficam em
evt007_item_identity_observations por run_id e item_key. A view base não escolhe
silenciosamente uma versão nova. A auditoria da execução usa as observações do
próprio run, preservadas em JSON e CSV. Promoção de uma revisão da identidade base
exige decisão posterior; não se deve interpretar a view como "última observação".

## Testes e limites de prova

Executar da raiz do repositório:

```sh
CATSER_TEST_PATH=/caminho/catser.csv python3 -m unittest discover -s tests -v
```

Fixtures artificiais explícitas; não representam coleta factual. Os testes
usam o snapshot real certificado. Rerun/ON CONFLICT é testado em SQLite com
adaptação apenas de placeholders e cast JSON. Não é teste de migration no
PostgreSQL, de RLS remota ou de persistência real em Supabase.

Métricas de aquisição/namespace são por item único. Métricas econômicas são por
resultado. Taxas com denominador zero ficam null. Falha técnica de catálogo é
excluída do denominador de match, explicitado no relatório. Não há inferência
de garantia, B4, aprovação comercial ou cobertura nacional.

## Observação real de 11/09/2026

Uma consulta à rota 3, com início/fim 2026-09-09, página 1, tamanho 500,
retornou HTTP 200 e exatamente:

```json
{"resultado":[],"totalRegistros":0,"totalPaginas":0,"paginasRestantes":0}
```

SHA-256 dos 73 bytes:
`cdcf03a6c1a01cf872d34c16748f0850292e0b24fed460f73100562f98ada72c`.

Isso demonstra resposta vazia da fonte nessa consulta. Não demonstra inexistência
de resultados em outras fontes, funcionamento positivo da ponte nesta safra ou
aceite operacional. Não houve troca de data nem consulta de outro item.

Inspeção read-only dos dois projetos acessíveis não localizou gsb.evt007_results.
No projeto pjghkqqrbcjmcvujwunf a consulta como postgres retornou
to_regclass('gsb.evt007_results') = NULL. Portanto nenhuma migration ou escrita
remota foi executada. A ordem permanece sem aceite operacional completo.
