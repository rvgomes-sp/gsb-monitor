# E1 — primeira fatia funcional do Monitor

Escopo: dados existentes dos 42 casos → Investigação EVT-007 → Carteira da Ana → mesmo caso no Monitor. Sem coleta, enriquecimento, migrations ou gravação de dados de teste. Produção e main permanecem fora desta entrega.

## Matriz de componentes

| Componente | Fonte | Status | Persistência | Ação real? |
|---|---|---|---|---|
| Lista do Monitor | `/api/feed`, `monitor.opportunities` | FUNCIONAL REAL | Registros existentes, sem alteração | Pesquisa, paginação e abertura do caso |
| Identidade entre visões | `monitor.opportunities.id`, exposto como `case_id` | FUNCIONAL REAL, identidade transitória E1 | Usa o id já gravado, sem gerar outro | URLs selecionam o registro exato |
| Link legado com `process` repetido | Comparação dos registros do feed | ESTADO VAZIO REAL de seleção | Nenhuma escolha automática ou gravação | Solicita escolha do fornecedor |
| Empresa, CNPJ, órgão, processo, objeto, data e valor | Campos existentes do feed | FUNCIONAL REAL; ausências explícitas | Carteira existente | Leitura, busca e navegação |
| Rota | Rota já armazenada | FUNCIONAL REAL | Carteira existente | Exibição; sem requalificação |
| Contato, telefone, e-mail e notas | `/api/operations`, `monitor.outreach` | FUNCIONAL REAL ou ESTADO VAZIO REAL | Memória operacional existente | Consulta nas duas novas visões |
| Histórico | `monitor.outreach_history`, associado ao outreach | FUNCIONAL REAL ou ESTADO VAZIO REAL | Histórico existente | Expandir registros; nenhuma inferência de conversa |
| Follow-up | `outreach.next_follow_up_at` | FUNCIONAL REAL ou ESTADO VAZIO REAL | Data registrada; vazio = ainda não definido | Leitura e contagem de datas registradas |
| Mensagem | `outreach.subject` e `body` | FUNCIONAL REAL ou ESTADO VAZIO REAL | Texto já registrado | Leitura; não comprova envio de e-mail |
| Propostas | `monitor.proposals` | FUNCIONAL REAL ou ESTADO VAZIO REAL | Propostas existentes | Consulta; zero somente após leitura bem-sucedida |
| Casos da Carteira da Ana | Casos com contato/notas/status/histórico/proposta existentes | FUNCIONAL REAL ou ESTADO VAZIO REAL | Derivação de leitura; não cria carteira duplicada | Abre o mesmo caso; nenhum fallback para primeiros oito |
| Caso sem trabalho aberto diretamente na Carteira | Mesmo id do Monitor | ESTADO VAZIO REAL | Nenhuma inclusão por navegação | Exibe que é consulta sem registro de trabalho |
| Texto original da garantia | `percentual_garantia_execucao` legado | FUNCIONAL REAL como registro herdado, NÃO cláusula confirmada | Original preservado | Consulta em Garantia/Evidências; sem parsing escalar |
| Obrigação, percentual exigível, reforço, prazo e cobertura | Fonte documental ainda não integrada | CAPACIDADE FUTURA | Nenhum cálculo novo | Exibe não verificado/não investigado |
| Evidências do fato inicial | Campos já existentes no Monitor | FUNCIONAL REAL como registro da base, sem nova verificação PNCP | Fonte original permanece no banco | Distingue registro factual, indício herdado e desconhecimento |
| Dor, tese e intervenção | Ainda não há modelo evidencial integrado | CAPACIDADE FUTURA | Nada artificialmente persistido | Exibe não investigada; próximo passo é orientação, não conclusão |
| Perfil ampliado, fluxo contratual, OSINT, seguradora | Motores ainda não conectados nesta fase | CAPACIDADE FUTURA | Nenhuma nova consulta/tabela | Sem números ou botões de motor; aviso explícito |
| Preparar/enviar e-mail nas novas telas | Não integrado nesta fatia | CAPACIDADE FUTURA | Nenhum envio | Botões removidos; leitura da mensagem existente continua |
| Editar no Monitor existente | Rotas operacionais já existentes | FUNCIONAL REAL preexistente, escrita não testada no Preview | `monitor.outreach` / propostas | Mantido somente com leitura disponível e processo único |
| Buscar/ler edital no Monitor | Motor canônico ainda não integrado | CAPACIDADE FUTURA | Não cria fila | Botão retirado; documentos existentes, quando houver, continuam como links |
| Dossiês antigos estáticos | `commercial_intelligence_cases.json` | DEMONSTRATIVO / REFERÊNCIA; não validado para operação atual | Arquivo preservado com classificação explícita | Não abastece novas telas; leitura do Monitor restrita a `demo=1` |
| Protótipo assimétrico antigo e seus scores | `monitor_evt007_assimetrica.html`, `evt007_assimetrica.js` | DEMONSTRATIVO | Referência visual preservada | Oculto sem `demo=1`, com aviso permanente quando aberto |

Uma falha de leitura não é ESTADO VAZIO REAL: é indisponibilidade. A interface informa o erro e não o substitui por zero, contato ausente, não iniciado, safra antiga ou exemplos.

## Identidade e preservação

A E1 não decide a identidade canônica do coletor. Usa o id existente como referência opaca, preservando os 42 registros. `process_id` continua referência da contratação/item usada pelo legado. As duas ocorrências com fornecedor diferente não são deduplicadas.

Uma URL por `case_id` inválido não seleciona o primeiro caso. Uma URL legada por `process` com múltiplos registros exige escolha. Operações que só têm `process_id` não são atribuídas a fornecedores arbitrariamente: se houver memória compartilhada ambígua, a interface bloqueia a associação. As ações de escrita do Monitor não são oferecidas para esses processos repetidos.

A importação destrutiva está localizada em `app/api/import/snapshot/route.ts`, função POST: apaga `monitor.opportunities`, apaga propostas, recria ids com posição e substitui estado comercial. O chamador `monitor/subir_ouro.py` envia `operations={}`. Nenhuma dessas rotas foi executada ou refatorada nesta E1.

Fase 2 deverá substituir esse fluxo por ingestão factual idempotente: identificar resultado/unidade econômica, acrescentar fato a caso existente ou criar candidato, preservando contato, notas, follow-up, propostas e histórico. Ausência em uma safra nunca autoriza exclusão. O snapshot protege a evidência atual; a rotina antiga ainda exige neutralização técnica antes de qualquer nova coleta.

## Leitura operacional

`/api/operations` foi alterado de quatro consultas concorrentes em uma conexão limitada a uma sessão para uma consulta JSON consistente, com limite de espera e encerramento da conexão. A consulta equivalente foi medida em menos de 1 ms diretamente no banco de 42 casos. Isso não prova, isoladamente, a causa do antigo HTTP 504 na Vercel; o resultado do Preview é a prova de integração necessária.

A autenticação existente permanece obrigatória. Sem cópia de cookies, senha em arquivos, bypass, service role no navegador ou criação de usuários.

## Validação local

- Build Next.js e TypeScript concluído.
- Testes funcionais de identidade, ambiguidade, contato/notas/histórico, ausência versus erro e garantia composta.
- Sem alteração de schema, de dados comerciais ou do coletor.
- `npm ci` encontra inconsistência preexistente no lockfile (@emnapi/core/runtime); build local usa `npm install --package-lock=false --ignore-scripts`, sem alterar dependências declaradas/lockfile.
- Dois testes antigos de preservação referenciam arquivos que não existem neste repositório (`config/comercial/regras_comerciais.json` e `src/sincronizar_monitor_nuvem.py`). Não foram removidos nem substituídos por aprovação artificial.

Critério final: validar o Preview com Caiapó e conferir novamente os 42, a memória operacional, main e produção. Mocks e capacidades futuras não são dependências a preencher para essa prova.
