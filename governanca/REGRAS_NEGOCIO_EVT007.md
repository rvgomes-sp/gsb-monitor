# Regras de negócio — EVT-007

## 1. Limite do evento

O EVT-007 representa resultado/homologação. A operação de referência é a 10.5
do Manual PNCP 2.5.

O evento conserva dois tempos:

- `dataResultado`: quando ocorreu o resultado;
- `dataInclusao`: quando o resultado foi incluído no PNCP.

As datas não podem ser fundidas, substituídas ou inferidas uma da outra.

## 2. Fonte e universo

- Fonte técnica exclusiva: API PNCP 2.5.
- Universo: somente compras realizadas no Compras.gov.
- Proibidos: outra API, portal, navegador, scraping, planilha como fonte,
  fallback e runtime em `C:\`.
- A coleta dos 93 casos é a referência empírica que caracteriza a execução
  correta dessas regras.

## 3. Cancelamentos

Licitação, item ou resultado com cancelamento explícito não entra na base
comercial.

A resposta bruta e a decisão de exclusão permanecem na auditoria. O expurgo é
da oportunidade comercial, não da evidência de origem.

## 4. Fornecedor elegível

### Porte

Somente `DEMAIS`.

### Natureza jurídica

Somente:

- sociedade anônima de capital aberto;
- sociedade anônima de capital fechado;
- sociedade empresária limitada;
- sociedade limitada unipessoal.

Os nomes e códigos recebidos devem ser normalizados contra o domínio oficial.
Valor ausente ou não reconhecido não é aprovado automaticamente.

## 5. Valor homologado e rota

O cálculo utiliza valor homologado, nunca valor estimado.

- valor de R$ 1.000.000,00 até R$ 10.000.000,00:
  `VIEIRA_MENDONCA`;
- valor superior a R$ 10.000.000,00:
  `VAZQUEZ_FONSECA`.

## 6. Compras com vários itens

A contratação entra quando:

1. pelo menos um item individual possui valor homologado igual ou superior a
   R$ 1.000.000,00; ou
2. a soma de até 15 itens possui total superior a
   R$ 10.000.000,00.

## 7. Regras que permanecem

- nenhuma modalidade é excluída;
- ausência de campo não gera aprovação nem descarte automático;
- fornecedor precisa ter nome e identificação para uso comercial;
- cada descarte, retenção, agregação e rota conserva o motivo;
- nenhuma abordagem é disparada sem a regra operacional autorizada;
- coleta factual, leitura de edital e ativação comercial são camadas distintas;
- oportunidades aprovadas são persistidas diretamente no banco consumido pelo monitor;
- planilha, CSV e importação manual não fazem parte do fluxo operacional.
