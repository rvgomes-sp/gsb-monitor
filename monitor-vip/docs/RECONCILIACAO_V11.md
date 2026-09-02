# Reconciliação das duas visões — contrato congelado v1.1

Referência aprovada pelo Mentor: `GSB_Matriz_Canonica_Campos_v1.1(1).xlsx`.
SHA-256: `c9523412762e122d0df6a056f11b71d4d6c544601c354a8e7b20889414e1c6bf`.

`public/data/case_contract_v1_1.json` é a transcrição das 284 entradas: 176 da Investigação, 72 da Carteira da Ana e 36 ações/navegação. Não é uma nova versão da matriz. Modelos analíticos pendentes continuam pendentes.

As páginas retomam a estrutura densa e a família grafite/bordô/cobre/marfim. A Carteira usa a variante rosé e conserva a frase aprovada. Primeiro nível: síntese. Segundo: blocos. Terceiro: detalhes expansíveis, origem e significado. Não há gráfico, mapa, score, decisor, prazo ou resultado documental demonstrativo.

## Renderização

`case_contract.js` usa os cinco estados do contrato. Campos reais resolvem valores apenas do feed e da memória operacional existentes. Valor vazio vira estado vazio; falha ou ambiguidade vira indisponibilidade; zero real continua zero. Campos futuros preservam seu espaço e estado canônico. Conteúdo demonstrativo nunca é renderizado.

O status por caso é resolvido na leitura: a classificação histórica da planilha não serve para afirmar que todo caso possui o mesmo dado. Garantia composta continua texto integral, classificado como observação herdada, sem cálculo de obrigação final.

## Identidade e memória

O `id` já persistido navega como `case_id` opaco. `process_id` continua referência de processo e não vira identidade de caso. O leitor existente recusa atribuir contato/histórico a fornecedores ambíguos. Contato e notas lidos pela Investigação e pela Ana usam a mesma fonte.

A atribuição deliberada à Carteira ainda não tem fonte integrada. `portfolioMembership()` retorna explicitamente não atribuído; nenhuma heurística por outreach ou abertura de página inclui um caso. Os totais atuais de retorno/follow-up são identificados como memória existente do Monitor, sem fingir carteira atribuída.

## Ações

Busca, navegação entre as três visões, expansão de detalhes/fontes e atualização de leitura são ações reais. Todos os controles de motores, mensagens, contato, agenda ou proposta novos permanecem desabilitados com explicação visível. As novas visões não têm POST/PUT/PATCH/DELETE nem persistência local de estado comercial.

Nenhum endpoint, coletor, schema, autenticação, rotina de importação ou motor é alterado por esta reconciliação. O bloqueio da importação destrutiva e a identidade definitiva permanecem para a fase própria; nenhuma dessas rotas é chamada pelas novas telas.

## Validação local

`node --test tests/case-context.test.mjs tests/case-contract.test.mjs`: 19 testes focados em identidade, estados, garantia, memória, ausência de atribuição e de novas escritas.

`npm run build -- --webpack`: build e TypeScript. A opção local evita dependência da disposição de worktrees; o Preview usa a configuração existente do projeto.

Aceite de navegador requer o Preview autenticado, Caiapó e confirmação antes/depois dos 42 casos e dos hashes da memória. Nenhum teste de escrita está autorizado. Não fazer merge nem promover a produção.
