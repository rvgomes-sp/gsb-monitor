# 003-S / Controle 02-R / Etapa 2

Destinatário exclusivo: B.Mentor. Destino autorizado: wpsvmrmuxdvajjumdjqp.

Esta ordem supera a premissa de existência da base factual nos projetos antigos.
O destino novo deve começar limpo. Não importar banco antigo nem estruturas comerciais.

## Contrato estrutural versionado

1. supabase/migrations/20260911040256_evt007_factual_baseline_v1.sql
   cria schema gsb, collection_runs, raw_pages e results.
2. supabase/migrations/20260911040257_evt007_catalog_bridge_v1.sql
   cria item_identity, item_identity_observations e view de JOIN com security_invoker.

Os nomes de versão foram gerados pelo relógio UTC local, em sequência no padrão
supabase/migrations. O CLI não estava disponível; a tentativa npx terminou com
cancelamento da aprovação de rede. Não se declara geração pelo CLI nem aplicação.
O arquivo candidato antigo em banco/ permanece como histórico; não o aplicar junto
às novas migrations. As migrations novas são o contrato desta etapa.

Cada CREATE TABLE falha se a relação já existir; não altera tabelas históricas.
As novas tabelas têm RLS e acesso de backend; não há grants a anon/authenticated.
A tabela de resultados mantém o grão e os identificadores do coletor atual.
Páginas brutas conservam bytea, JSON interpretado, URL, SHA-256, página e aquisição.
Execuções têm status, data, fonte, paginação, totais, horário e erro.

## Fluxo preparado

O runner --persist verifica as seis relações antes da coleta, cria a execução,
preserva páginas e fatos antes da ponte, adquire cada item uma vez, conserva as
identidades e observações e fecha o relatório. Cada rerun exige run_id/diretório
novo. ON CONFLICT conserva o primeiro fato e a identidade base; observações e
páginas de cada run ficam independentes. A view mostra a identidade base.

Para avaliação operacional, executar os comandos somente após migrations
aplicadas e os cinco contadores iniciais confirmados em zero:

```sh
python coletor/esteira_evt007.py --date 2026-09-09 --catser /caminho/catser.csv --output /evidencias/primeiro_run --persist
python coletor/esteira_evt007.py --date 2026-09-09 --catser /caminho/catser.csv --output /evidencias/rerun --persist
```

DATABASE_URL deve apontar ao destino novo autorizado, nunca ao projeto antigo.
A conferência posterior deve demonstrar que results e item_identity não duplicam
as mesmas chaves. collection_runs e raw_pages crescem por execução; isso é
genealogia esperada, não duplicação factual. Observações também são por execução.

## Estado real desta entrega

get_project, execute_sql read-only e list_migrations para o destino novo retornaram
"You do not have permission to perform this action" na conexão Supabase disponível.
A listagem dessa conexão contém apenas os projetos antigos. Nada foi aplicado
ao novo projeto. Existência das seis relações e contagens iniciais são NÃO VERIFICADAS.
Não se conclui que o projeto ou as tabelas não existam; falta acesso para verificar.

19 testes locais passaram. Incluem fixtures, snapshot CATSER certificado e SQLite
para chaves/ON CONFLICT/preservação dos bytes. Não equivalem a validação PostgreSQL,
RLS remota, migration aplicada ou rerun real no novo destino.

Não houve nova consulta externa de safra após esta correção: a ordem condiciona
essa consulta à confirmação do banco físico. A resposta vazia observada na etapa
anterior permanece histórica e não serve como prova desta etapa.

Pendência necessária: disponibilizar wpsvmrmuxdvajjumdjqp na conexão Supabase desta
trilha, com acesso de leitura e aplicação das migrations já autorizadas. A autorização
de negócio foi recebida; não está sendo solicitada novamente.
