# GSB — composição visual v1

Somente apresentação. Contrato canônico de campos v1.1, fontes de dados, status, 42 casos e motores permanecem intactos.

## Tipografia

Decisão explícita do Mentor, confirmada pelo Investidor: Cormorant Garamond para identidade/display/editorial; Segoe UI para operação. Implementação isolada em `public/assets/identity_typography.css`, após os estilos de composição. Não há terceira família editorial nem substituição do contrato semântico.

| Token | Família declarada | Aplicação |
|---|---|---|
| --font-brand | Cormorant Garamond, serif | GB e GSB Monitor: 600 |
| --font-display | Cormorant Garamond, serif | Ana: 500; Investigação/caso: 600 |
| --font-editorial | Cormorant Garamond, serif | Títulos: 500/600; frase: itálico 400 |
| --font-body | Segoe UI, sans-serif | Operação, menus, campos, rótulos e estados |
| --font-number | Cormorant Garamond, serif | Valores destacados e KPIs grandes: 600 |
| --font-operational-number | Segoe UI, sans-serif | Valores/datas pequenos: 600 e tabular-nums |

A Cormorant é carregada pelo serviço Google Fonts somente nas duas novas telas, nos pesos usados (romana 500/600 e itálica 400), com `display=swap` e `referrerpolicy=no-referrer` no link. Nenhum arquivo de fonte é redistribuído no repositório. Origem e licença verificadas: [Cormorant — Google Fonts](https://fonts.google.com/specimen/Cormorant+Garamond) e [SIL OFL 1.1 do projeto](https://github.com/google/fonts/blob/main/ofl/cormorantgaramond/OFL.txt), copyright 2015 Cormorant Project Authors. Segoe UI usa a instalação legítima do sistema; não é distribuída como webfont. Os fallbacks genéricos são resiliência, não novas vozes aprovadas. Em sistemas sem Segoe haverá fallback sans-serif; falha de rede pode impedir Cormorant de carregar. A validação deve distinguir família declarada de fonte efetivamente disponível.

## Cor

| Papel | Investigação | Carteira |
|---|---|---|
| Fundo | #07090B | #0C0D10 |
| Painel | #101315 | #21191F |
| Bordô | #49252C | Mesma família |
| Cobre | #EEAA84 | #F0C09A |
| Rose gold / rosé | #D79B91 | #E7A4AC |
| Salmão | #F48F79 | #EDB1AC |
| Marfim | #F5E9DA | Mesma família |
| Texto secundário | #C2B4A9 | Rótulos #CBB4A8 |

Halos são localizados em selo, ícones, bordas selecionadas e saída. Ausência de evidência não recebe classe de pressão alta.

## Logo e ornamento

O projeto não contém um asset vetorial oficial do monograma. `public/favicon.svg` é um ícone genérico e não foi usado como marca. A referência reutilizada é `.emblem` em `public/assets/vip_monitor.css`: gradiente radial, dois aros e letras sobrepostas. O GB passa a Cormorant 600, com tracking -6 px, compensação de tracking 6 px e ajuste óptico (-1 px, +1 px). Caixa e aros preservados; centro escuro e metal menos intenso. Denominação: **implementação canônica proposta do monograma GSB**, não asset oficial certificado.

| Halo alterado | Antes | Depois | Função |
|---|---|---|---|
| Selo Investigação | blur 25 px, #D57F44 a 34% | blur 18 px, spread 0, #D18D5D a 20% | Identidade, sem iluminar o fundo |
| Selo Ana | blur 29 px, #E8A7A8 a 33% | blur 20 px, spread 0, #DF9AA3 a 20% | Assinatura rosé |
| Letras GB | blur 12 px, #FFC691 a 50% | blur 7 px, #E7B283 a 30% | Brilho concentrado nas letras |

Os demais halos, cores, ornamentos, grids, paddings e controles permanecem como na composição aprovada. A hierarquia tipográfica muda somente a apresentação; nenhum dado ou estado é recodificado.

`public/assets/brand/rose-line.svg` é ornamento botânico vetorial decorativo para a variante Ana, sem dados ou comportamento. A rosa do raster não foi extraída nem declarada asset oficial.

## Composição e aceite

Investigação: três sínteses, fases, seis núcleos em grade 3×2, faixa de assinatura/evidências/fiscal, tese/plano lateral e saída. Os campos secundários abrem no detalhe, sem retirar o bloco do cockpit.

Carteira: título e frase próprios, cinco KPIs, casos/selecionado lado a lado, três áreas operacionais e faixa de próxima ação/propostas.

`visual_acceptance.html` é uma página de QA autenticada. Renderiza as telas reais em um iframe de 1920×1080, 1600×900 ou 1366×768, sem zoom, transformação de escala, fixtures ou alteração de dados. A rolagem da aplicação é medida dentro do frame, não pela janela externa do navegador de QA. Métricas de DOM não substituem screenshots: o navegador disponível não expõe resize e a captura ampliada da etapa anterior falhou por timeout. Nenhuma captura nativa deve ser rotulada como captura de outro viewport.
