# Arquitetura do GSB Monitor V2.5

## Princípio permanente

Dado público → caso → evento → evidência → valor confiável → rota → decisão humana.

O contrato PNCP é resolvido exclusivamente no artefato local canônico
registrado. Divergência ou ausência bloqueia a operação, sem fallback para
internet. Somente o adaptador de runtime autorizado consulta dados externos; o
documento confirma, o humano decide, o banco será a fonte de verdade e o radar
será sempre uma visão derivada.

A matriz `EVT-001` a `EVT-014` é estável por decisão GOV-001. Começar pelo EVT-007 é prioridade operacional, não redução da arquitetura.

## Fluxo ativo

1. O endpoint oficial de resultados de itens do Dados Abertos Compras.gov enumera o D-1 por `dataResultadoPncpInicial` e `dataResultadoPncpFinal`.
2. A descoberta preserva todas as páginas JSON e sua auditoria.
3. A consolidação factual lê somente esses arquivos locais.
4. Cada resultado é validado por `dataResultadoPncp`, deduplicado e preservado com a nomenclatura oficial.
5. Campos derivados recebem prefixo `gsb`.
6. São produzidas visões por resultado, contratação e fornecedor, além da auditoria factual.
7. O enriquecimento de item e a qualificação comercial permanecem bloqueados
   até existir artefato local registrado e compatível.
8. Somente casos registrados e validados poderão alimentar o radar e o fluxo de abordagem.

## Separação de responsabilidades

- `src/Descobrir_EVT007_D1.ps1`: enumeração, paginação, checkpoint e páginas brutas.
- `src/Consolidar_EVT007_DadosAbertos.ps1`: camada factual exclusivamente local.
- `src/Coletar_EVT007.ps1`: guarda que impede a repetição das rotas HTTP 301.
- `src/Qualificar_EVT007.ps1`: guarda que impede qualificação prematura.
- `config/api/`: registro de artefatos locais e adaptadores externos autorizados.
- `config/comercial/`: regras GSB mantidas inativas até o enriquecimento.
- `output/factual/`: saídas factuais; não contém base comercial.

## Barreira de contaminação

O fluxo ativo não aceita:

- candidatos ou resultados do V2;
- `CandidateCsv` como porta de entrada após a descoberta completa;
- chamadas ao núcleo `/api/pncp/v1` durante a consolidação;
- consulta documental ao portal PNCP ou fallback para internet;
- uso de OpenAPI cuja versão declarada divirja do registro local;
- fallback para D-2 ou janela maior;
- `dataPublicacaoPncp` como substituta de `dataResultadoPncp`;
- exclusão de modalidade;
- classificação comercial sem item e catálogo oficiais.
- descarte automático por ausência de dado.
- abordagem automática ou sem validação humana.

## Relação entre as camadas

- **Descoberta:** comprova cobertura e preserva o retorno oficial.
- **Factual integral:** conserva todos os resultados D-1 para auditoria.
- **Factual utilizável:** exclui apenas resultados cancelados ou sem fornecedor identificado.
- **Enriquecimento:** futuro; deve adicionar item, catálogo, objeto, modalidade
  e origem por artefato local registrado e adaptador autorizado.
- **Comercial:** futuro; somente após o enriquecimento e a aplicação auditada das regras.
- **Decisão humana:** obrigatória antes de encaminhar a oportunidade a qualquer rota comercial.
