-- 030 — Biblioteca de objetos + taxonomia CNAE-like (schema gsb)
-- Projeto Supabase: observatorio-sg (pjghkqqrbcjmcvujwunf).
-- Ver governanca/DOUTRINA_ESTEIRA_BIBLIOTECA.md.

create schema if not exists gsb;

-- ===== Biblioteca: 1 linha por contratação >= 10MM (estimado). Inferência + verdade. =====
create table if not exists gsb.biblioteca_objetos (
  id                bigserial primary key,
  data_referencia   date,
  controle_pncp     text,
  uf                text,
  orgao             text,
  modalidade_id     int,
  valor_estimado    numeric,
  situacao          text,
  objeto            text not null,
  descricao_curta   text,
  familia_inferida  text,
  garantia_hipotese text,
  motivo_hipotese   text,
  garantia_label_raw text,          -- rótulo cru do humano
  garantia_grau     text,           -- normalizado
  nota              text,           -- o "porquê" (humano)
  rotulado_por      text default 'rodrigo',   -- rodrigo | maquina
  fonte             text,
  -- códigos da taxonomia
  codigo_objeto     text,
  grupo_objeto      text,
  garantia_grau_fino text,
  garantia_codigo   text,
  garantia_status   text,           -- EXIGE | ND
  garantia_prioridade int,          -- 0..9
  id_biblioteca     text,           -- codigo_objeto-garantia_codigo
  created_at        timestamptz default now()
);
create unique index if not exists ux_biblioteca_controle
  on gsb.biblioteca_objetos (controle_pncp) where controle_pncp is not null;
create index if not exists ix_biblioteca_familia on gsb.biblioteca_objetos (familia_inferida);
create index if not exists ix_biblioteca_grau on gsb.biblioteca_objetos (garantia_grau);
create index if not exists ix_biblioteca_uf on gsb.biblioteca_objetos (uf);
create index if not exists ix_biblioteca_orgao on gsb.biblioteca_objetos (orgao);

-- ===== Codebooks da taxonomia (crescem a cada nova família) =====
create table if not exists gsb.tax_grupo_objeto (
  codigo text primary key, nome text not null, descricao text
);
insert into gsb.tax_grupo_objeto(codigo,nome,descricao) values
 ('O','OBRA / ENGENHARIA','Execução física, construção, reforma, infraestrutura, engenharia'),
 ('S','SERVIÇO','Serviços continuados, mão de obra, TI, locação, financeiro, diversos'),
 ('B','BEM / AQUISIÇÃO','Compra de material, insumo, equipamento, veículo, medicamento, alimento'),
 ('C','CONCESSÃO / PPP','Concessões, parcerias público-privadas'),
 ('X','NÃO CLASSIFICADO','A enriquecer — objeto ainda sem grupo definido')
on conflict (codigo) do nothing;

create table if not exists gsb.tax_subgrupo_objeto (
  codigo text primary key,
  grupo  text not null references gsb.tax_grupo_objeto(codigo),
  familia_ref text, nome text not null
);
insert into gsb.tax_subgrupo_objeto(codigo,grupo,familia_ref,nome) values
 ('O.01','O','OBRA_EDIFICACAO','Edificação / reforma predial'),
 ('O.02','O','OBRA_PAVIMENTACAO','Pavimentação / recapeamento'),
 ('O.03','O','OBRA_SANEAMENTO','Saneamento / obra hídrica'),
 ('O.04','O','OBRA_RODOVIA','Rodovia / estrada'),
 ('O.05','O','OBRA_ELETRICA','Infraestrutura elétrica / iluminação'),
 ('O.06','O','OBRA_ARTE_ESPECIAL','Ponte / viaduto / obra de arte'),
 ('O.07','O','SERVICO_ENGENHARIA','Serviço de engenharia / fiscalização de obra'),
 ('S.01','S','SERVICO_CONTINUO_MAO_OBRA','Serviço contínuo c/ dedicação de mão de obra'),
 ('S.02','S','TI_SOFTWARE','TI / software / telecom'),
 ('S.03','S','SERVICO_DIVERSO','Serviço diverso'),
 ('S.04','S','LOCACAO','Locação'),
 ('S.05','S','SERVICO_FINANCEIRO','Serviço financeiro (folha/banco)'),
 ('B.01','B','MEDICAMENTO_SAUDE','Medicamento / insumo / saúde'),
 ('B.02','B','ALIMENTACAO','Alimentação / gêneros'),
 ('B.03','B','COMBUSTIVEL','Combustível'),
 ('B.04','B','VEICULO_MAQUINA','Veículo / máquina'),
 ('B.05','B','EQUIPAMENTO_MOBILIARIO','Equipamento / mobiliário'),
 ('B.06','B','MATERIAL_INSUMO','Material / insumo'),
 ('C.01','C','CONCESSAO_PPP','Concessão / PPP'),
 ('X.00','X','OUTRO','Não classificado — a enriquecer')
on conflict (codigo) do nothing;

create table if not exists gsb.tax_garantia (
  codigo text primary key, nome text not null, status text not null,
  prioridade int not null, descricao text
);
insert into gsb.tax_garantia(codigo,nome,status,prioridade,descricao) values
 ('G0','CERTEZA','EXIGE',0,'Garantia certa (concessão/PPP, grande vulto)'),
 ('G1','EXIGE','EXIGE',0,'Exige garantia (obra, engenharia, serviço contínuo c/ mão de obra)'),
 ('ND.A','PROVÁVEL','ND',1,'Não identificado — prioridade 1 de consulta ao edital'),
 ('ND.B','POSSÍVEL','ND',2,'Não identificado — prioridade 2'),
 ('ND.C','DEPENDE','ND',3,'Não identificado — prioridade 3'),
 ('ND.D','IMPROVÁVEL','ND',4,'Não identificado — prioridade 4 (baixa)'),
 ('ND.Z','SEM QUALIFICAÇÃO','ND',9,'Não identificado — sem qualificação inicial')
on conflict (codigo) do nothing;
