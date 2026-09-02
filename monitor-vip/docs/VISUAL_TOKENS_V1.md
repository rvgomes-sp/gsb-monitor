# GSB — composição visual v1

Somente apresentação. Contrato canônico de campos v1.1, fontes de dados, status, 42 casos e motores permanecem intactos.

## Tipografia

As imagens raster aprovadas não identificam a família exata. Nenhum arquivo WOFF/TTF/OTF foi encontrado no projeto. A alternativa explicitada ao Mentor é preservar as famílias declaradas pelo Monitor existente, sem acrescentar silenciosamente uma fonte nova. Correspondência exata com o PNG permanece pendente de identificação/aprovação da fonte.

| Token | Família declarada | Aplicação |
|---|---|---|
| --font-brand | Georgia, Times New Roman, serif | Selo e GSB Monitor |
| --font-display | Georgia, Times New Roman, serif | Título principal |
| --font-editorial | Georgia, Times New Roman, serif | Títulos editoriais e frase |
| --font-body | Segoe UI, Arial, sans-serif | Operação e rótulos |
| --font-number | Georgia, Times New Roman, serif | Valores e KPIs |

As fontes são do sistema: o fallback pode variar por ambiente. Os tokens estão centralizados, mas a equivalência tipográfica exata ao protótipo não está certificada.

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

O projeto não contém um asset vetorial oficial do monograma. `public/favicon.svg` é um ícone genérico e não foi usado como marca. A referência reutilizada é `.emblem` em `public/assets/vip_monitor.css`: gradiente radial, dois aros, letras GB sobrepostas em Georgia, halo e assinatura textual. A composição foi escalada proporcionalmente para a barra lateral. Não é uma vetorização certificada do PNG.

`public/assets/brand/rose-line.svg` é ornamento botânico vetorial decorativo para a variante Ana, sem dados ou comportamento. A rosa do raster não foi extraída nem declarada asset oficial.

## Composição e aceite

Investigação: três sínteses, fases, seis núcleos em grade 3×2, faixa de assinatura/evidências/fiscal, tese/plano lateral e saída. Os campos secundários abrem no detalhe, sem retirar o bloco do cockpit.

Carteira: título e frase próprios, cinco KPIs, casos/selecionado lado a lado, três áreas operacionais e faixa de próxima ação/propostas.

`visual_acceptance.html` é uma página de QA autenticada. Renderiza as telas reais em um iframe de 1920×1080, 1600×900 ou 1366×768, sem zoom, transformação de escala, fixtures ou alteração de dados. A captura full-page do quadro corresponde à imagem do viewport interno. A rolagem da aplicação é medida dentro do frame, não pela janela externa do navegador de QA.
