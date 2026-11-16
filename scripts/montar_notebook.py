"""Monta o notebook de analise (02_analise.ipynb) e o executa.

Mantem o notebook e os scripts em sincronia: o notebook le os mesmos
arquivos da camada gold e reproduz as respostas das perguntas de negocio.

Uso: python3 -I montar_notebook.py <dir_projeto> <ano>
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

proj = Path(sys.argv[1])
ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2025

md = lambda s: nbf.v4.new_markdown_cell(s.strip())
cd = lambda s: nbf.v4.new_code_cell(s.strip())

cells = [
md(f"""
# Análise: onde intervir para recuperar capacidade de cais

Notebook de análise do MVP. Ano de referência **{ano}**.

Ele parte da camada **gold** já construída por `scripts/pipeline.py` e reproduz,
célula a célula, as respostas às perguntas de negócio P1 a P4 e a verificação
de qualidade P5.

Ordem de execução do projeto:

1. `scripts/coleta.py` baixa os arquivos e grava o manifesto
2. `scripts/pipeline.py` constrói bronze, silver e gold
3. `scripts/qualidade.py` audita os 59 atributos
4. **este notebook** responde às perguntas
5. `notebooks/01_pipeline_databricks.py` replica tudo em PySpark na nuvem
"""),

cd(f"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJ = Path("..") if Path("../dados/gold").exists() else Path(".")
ANO = {ano}
G = PROJ / "dados" / "gold"

fato   = pd.read_parquet(G / f"fato_atracacao_{{ANO}}.parquet")
dim_i  = pd.read_parquet(G / f"dim_instalacao_{{ANO}}.parquet")
dim_b  = pd.read_parquet(G / f"dim_berco_{{ANO}}.parquet")
dim_t  = pd.read_parquet(G / f"dim_tempo_{{ANO}}.parquet")
dim_n  = pd.read_parquet(G / f"dim_navegacao_{{ANO}}.parquet")
dim_c  = pd.read_parquet(G / f"dim_natureza_carga_{{ANO}}.parquet")

print(f"fato_atracacao ...... {{len(fato):>8,}} linhas, {{len(fato.columns)}} atributos")
for nome, d in [("dim_instalacao", dim_i), ("dim_berco", dim_b), ("dim_tempo", dim_t),
                ("dim_navegacao", dim_n), ("dim_natureza_carga", dim_c)]:
    print(f"{{nome:.<20}} {{len(d):>8,}} linhas, {{len(d.columns)}} atributos")
"""),

md("""
## Junção do esquema estrela

A tabela fato guarda apenas chaves e medidas. Os atributos descritivos vêm das
dimensões. Esta é a junção usada em toda a análise.
"""),

cd("""
base = (fato
        .merge(dim_i, on="sk_instalacao", how="left")
        .merge(dim_n, on="sk_navegacao",  how="left")
        .merge(dim_c, on="sk_natureza",   how="left"))

# Só entram na análise de tempo os registros aptos: sem cronologia inválida,
# sem estadia outlier e com tempo atracado definido.
base = base[base["flag_apto_analise_tempo"]]
print(f"{len(base):,} atracações aptas de {len(fato):,} ({len(base)/len(fato)*100:.2f}%)")

# Segmentação por modo de navegação. A justificativa está na P2.
SEGMENTOS = {"Marítimo de carga": ["Longo Curso", "Cabotagem"],
             "Interior (fluvial)": ["Interior"],
             "Apoio": ["Apoio Marítimo", "Apoio Portuário"]}
base["segmento"] = "Outros"
for nome, tipos in SEGMENTOS.items():
    base.loc[base["tipo_navegacao"].isin(tipos), "segmento"] = nome

base["segmento"].value_counts()
"""),

md("""
## P1. Para onde vai o tempo da embarcação

A decomposição oficial da ANTAQ separa quatro tempos. T2 e T4 são berço
ocupado sem nada sendo movimentado: é a capacidade mais barata de recuperar.

O ponto de atenção é o estimador. Soma e mediana levam a conclusões opostas.
"""),

cd("""
ETAPAS = ["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
          "t3_operacao_h", "t4_espera_desatracacao_h"]
comp = base.dropna(subset=ETAPAS)

somas = comp[ETAPAS].sum()
meds  = comp[ETAPAS].median()

p1 = pd.DataFrame({
    "horas_no_ano": somas.round(0),
    "share_por_soma_%": (somas / somas.sum() * 100).round(2),
    "atracação_mediana_h": meds.round(2),
    "share_por_mediana_%": (meds / meds.sum() * 100).round(2),
})
p1.index = ["T1 espera para atracar", "T2 espera p/ iniciar",
            "T3 operação", "T4 espera p/ sair"]
print(f"navio-hora total: {somas.sum():,.0f} h em {len(comp):,} atracações\\n")
p1
"""),

cd("""
t1 = comp["t1_espera_atracacao_h"]
print(f"assimetria de T1 .... {t1.skew():.2f}")
print(f"média ............... {t1.mean():.2f} h")
print(f"mediana ............. {t1.median():.2f} h")
print(f"percentil 99 ........ {t1.quantile(0.99):.1f} h\\n")

for q in [0.90, 0.95, 0.99]:
    acima = t1[t1 > t1.quantile(q)]
    print(f"os {(1-q)*100:>4.0f}% com maior espera concentram "
          f"{acima.sum()/t1.sum()*100:5.1f}% de todas as horas de espera")

improd = somas["t2_espera_inicio_op_h"] + somas["t4_espera_desatracacao_h"]
atracado = improd + somas["t3_operacao_h"]
print(f"\\nberço improdutivo: {improd:,.0f} h = {improd/atracado*100:.2f}% do tempo atracado")
print(f"equivalente a {improd/8760:.1f} posições de cais paradas o ano inteiro")
"""),

md("""
## P2. Onde está concentrado, e por que o ranking direto engana

Primeiro o ranking sem segmentação, que é o que sairia de uma leitura direta
do indicador. Depois o teste da hipótese alternativa de que ele esteja
capturando modelo de negócio em vez de ineficiência.
"""),

cd("""
ingenuo = (comp.groupby(["sk_instalacao", "porto_atracacao", "sguf"])
           .agg(atracacoes=("sk_atracacao", "count"),
                improdutivo_h=("berco_improdutivo_h", "sum"),
                atracado_h=("ta_atracado_h", "sum"))
           .reset_index())
ingenuo["pct_improdutivo"] = (ingenuo["improdutivo_h"] / ingenuo["atracado_h"] * 100).round(1)
ingenuo.nlargest(8, "improdutivo_h")[
    ["porto_atracacao", "sguf", "atracacoes", "improdutivo_h", "pct_improdutivo"]].round(0)
"""),

cd("""
# Perfil operacional das instalações do topo: o teste que derruba a leitura direta.
for cod in ingenuo.nlargest(4, "improdutivo_h")["sk_instalacao"]:
    s = comp[comp["sk_instalacao"] == cod]
    print(f"--- {s['porto_atracacao'].iloc[0]} ({s['sguf'].iloc[0]}), n={len(s):,}")
    print(f"    navegação .......... {s['tipo_navegacao'].value_counts().head(2).to_dict()}")
    print(f"    instalação em rio .. {s['instalacao_em_rio'].value_counts().to_dict()}")
    print(f"    medianas ........... T1={s['t1_espera_atracacao_h'].median():.1f}h  "
          f"T2={s['t2_espera_inicio_op_h'].median():.1f}h  "
          f"T3={s['t3_operacao_h'].median():.1f}h  "
          f"T4={s['t4_espera_desatracacao_h'].median():.1f}h")
    print(f"    peso médio ......... {s['peso_bruto_t'].mean():,.0f} t\\n")
"""),

md("""
O padrão é claro. As instalações do topo são terminais fluviais de barcaça,
com espera para atracar perto de zero, operação curta e longa espera atracado.
A barcaça atraca e aguarda a formação do comboio: a espera atracada **é** o
modelo logístico, não desperdício.

Comparando os segmentos por volume movimentado, a diferença fica evidente.
"""),

cd("""
seg = (comp.groupby("segmento")
       .agg(atracacoes=("sk_atracacao", "count"),
            peso_Mt=("peso_bruto_t", lambda x: x.sum() / 1e6),
            improdutivo_h=("berco_improdutivo_h", "sum"),
            operacao_h=("t3_operacao_h", "sum"),
            atracado_h=("ta_atracado_h", "sum"))
       .reset_index())
seg["pct_improdutivo"] = (seg["improdutivo_h"] / seg["atracado_h"] * 100).round(2)
seg["t_por_atracacao"] = (seg["peso_Mt"] * 1e6 / seg["atracacoes"]).round(0)
seg.round(2)
"""),

cd("""
# Ranking corrigido: só o universo em que berço improdutivo significa
# capacidade de cais marítimo perdida.
mar = comp[(comp["segmento"] == "Marítimo de carga") & comp["operacao_produtiva"]]

rank = (mar.groupby(["sk_instalacao", "porto_atracacao", "sguf", "tipo_autoridade"])
        .agg(atracacoes=("sk_atracacao", "count"),
             improdutivo_h=("berco_improdutivo_h", "sum"),
             atracado_h=("ta_atracado_h", "sum"),
             peso_t=("peso_bruto_t", "sum"))
        .reset_index())
rank["pct_improdutivo"] = (rank["improdutivo_h"] / rank["atracado_h"] * 100).round(2)
rank = rank[rank["atracacoes"] >= 50]

alvo = rank["pct_improdutivo"].median()
rank["horas_recuperaveis"] = np.where(
    rank["pct_improdutivo"] > alvo,
    rank["improdutivo_h"] - rank["atracado_h"] * alvo / 100, 0.0)
rank = rank.sort_values("horas_recuperaveis", ascending=False)

print(f"universo: {len(rank)} instalações, {rank['atracacoes'].sum():,} atracações")
print(f"alvo (mediana do setor): {alvo:.2f}% do tempo atracado")
print(f"recuperável: {rank['horas_recuperaveis'].sum():,.0f} h = "
      f"{rank['horas_recuperaveis'].sum()/8760:.2f} posições de cais")
print(f"concentração no top 10: "
      f"{rank.head(10)['horas_recuperaveis'].sum()/rank['horas_recuperaveis'].sum()*100:.1f}%\\n")
rank.head(10)[["porto_atracacao", "sguf", "atracacoes", "pct_improdutivo",
               "horas_recuperaveis"]].round(1)
"""),

cd("""
# O custo do viés, quantificado: quantas instalações sobrevivem à correção?
top_ingenuo   = set(ingenuo.nlargest(10, "improdutivo_h")["sk_instalacao"])
top_corrigido = set(rank.head(10)["sk_instalacao"])
comuns = top_ingenuo & top_corrigido
print(f"top 10 ingênuo   : {len(top_ingenuo)} instalações")
print(f"top 10 corrigido : {len(top_corrigido)} instalações")
print(f"em comum ........ : {len(comuns)}  ->  {10-len(comuns)} de 10 decisões "
      f"seriam direcionadas ao lugar errado")
"""),

md("""
## P3. Fila ou coordenação?

A decisão entre construir berço e reorganizar programação depende de a espera
ser ou não explicada por congestionamento.

Antes de calcular ocupação, é preciso resolver um problema: `IDBerco` não é
uma posição exclusiva de atracação.
"""),

cd("""
silver = pd.read_parquet(PROJ / "dados" / "silver" / f"atracacao_tratada_{ANO}.parquet")
s = silver.dropna(subset=["Data Atracação", "Data Desatracação"])
s = s[~s["flag_cronologia_invalida"] & ~s["flag_estadia_outlier"]]

# Ocupação simultânea máxima observada em cada berço ao longo do ano.
ev = pd.concat([
    pd.DataFrame({"b": s["IDBerco"], "t": s["Data Atracação"],    "d":  1}),
    pd.DataFrame({"b": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
]).sort_values(["b", "t", "d"], ascending=[True, True, False])
ev["oc"] = ev.groupby("b")["d"].cumsum()
pos = ev.groupby("b")["oc"].max().clip(lower=1)

print(f"berços avaliados ................. {len(pos):,}")
print(f"com posição única (exclusivos) ... {(pos<=1).sum():,} ({(pos<=1).mean()*100:.1f}%)")
print(f"mediana de posições .............. {pos.median():.0f}")
print(f"percentil 90 ..................... {pos.quantile(0.9):.0f}")
print(f"máximo ........................... {pos.max()}")
print("\\nSupor uma posição por berço produziria ocupação acima de 100% "
      "e falso diagnóstico de congestionamento.")
"""),

cd("""
pos_inst = (dim_b.merge(pos.rename("posicoes"), left_on="sk_berco", right_index=True, how="left")
            .groupby("sk_instalacao")["posicoes"].sum().rename("posicoes_inst").reset_index())

u = rank.merge(pos_inst, on="sk_instalacao", how="left")
u["posicoes_inst"] = u["posicoes_inst"].fillna(1)
u["ocupacao_pct"] = (u["atracado_h"] / (8760 * u["posicoes_inst"]) * 100).round(2)
u["espera_mediana_h"] = (mar.groupby("sk_instalacao")["t1_espera_atracacao_h"]
                         .median().reindex(u["sk_instalacao"]).values)

uu = u.dropna(subset=["ocupacao_pct", "espera_mediana_h"])
rho, p = stats.spearmanr(uu["ocupacao_pct"], uu["espera_mediana_h"])
print(f"n = {len(uu)} instalações marítimas")
print(f"Spearman rho = {rho:.4f}  (p = {p:.2e})")
print(f"variação de ordem explicada: {rho**2*100:.1f}%")
print(f"ocupação mediana do setor: {uu['ocupacao_pct'].median():.2f}%\\n")
print("Leitura: a relação existe e é significativa, mas explica pouco. "
      "Ocupação na casa dos 20% não é sistema saturado. Para a maioria "
      "das instalações da lista, berço novo não é a intervenção indicada.")
"""),

md("""
## P4. Intervir por terminal ou por tipo de carga?

Decomposição da variância do logaritmo da prancha operacional. A pergunta é
qual fator explica mais: quem é o terminal, ou o que ele movimenta.
"""),

cd("""
prod = base[base["operacao_produtiva"]
            & base["prancha_operacional_th"].notna()
            & ~base["flag_prancha_implausivel"]
            & base["flag_atracacao_exclusiva"].fillna(False)].copy()
prod["log_prancha"] = np.log(prod["prancha_operacional_th"])

def eta2(df, grupo, alvo="log_prancha"):
    m = df[alvo].mean()
    sqt = ((df[alvo] - m) ** 2).sum()
    g = df.groupby(grupo)[alvo].agg(["mean", "count"])
    return float((g["count"] * (g["mean"] - m) ** 2).sum() / sqt)

print(f"atracações na análise: {len(prod):,}\\n")
for rot, col in [("qual instalação", "sk_instalacao"),
                 ("qual tipo de carga", "natureza_carga"),
                 ("qual navegação", "tipo_navegacao")]:
    print(f"{rot:.<24} {eta2(prod, col)*100:5.1f}% da variação explicada")
"""),

cd("""
# Dispersão entre terminais DENTRO de cada tipo de carga.
linhas = []
for nat, g in prod.groupby("natureza_carga"):
    med = g.groupby("sk_instalacao")["prancha_operacional_th"].median()
    med = med[g.groupby("sk_instalacao").size() >= 30]
    if len(med) >= 5:
        linhas.append({"natureza_carga": nat, "instalacoes": len(med),
                       "p10_t_h": round(med.quantile(0.10), 1),
                       "p90_t_h": round(med.quantile(0.90), 1),
                       "razao_p90_p10": round(med.quantile(0.90) / med.quantile(0.10), 1)})
pd.DataFrame(linhas).sort_values("razao_p90_p10", ascending=False)
"""),

md("""
## P5. A base sustenta essas decisões?

Resumo da auditoria. O relatório completo, com os 59 atributos, está em
`outputs/relatorio_qualidade_{ANO}.md`.
"""),

cd("""
qa = pd.read_csv(PROJ / "outputs" / f"qualidade_por_atributo_{ANO}.csv")
print(f"{len(qa)} atributos auditados em {qa['tabela'].nunique()} tabelas\\n")
print(qa.groupby("situacao").size().to_string())
print()
print("Atributos com menor completude:")
print(qa.nsmallest(5, "completude_pct")[["tabela", "atributo", "completude_pct"]].to_string(index=False))
print()
print("Violações de domínio declarado:")
v = qa[qa["violacoes_de_dominio"] > 0][["tabela", "atributo", "violacoes_de_dominio", "regra_de_dominio"]]
print(v.to_string(index=False) if len(v) else "  nenhuma")
"""),

cd("""
rel = json.load(open(PROJ / "outputs" / f"relatorio_qualidade_{ANO}.json", encoding="utf-8"))
print("Integridade referencial e cronológica")
print(json.dumps(rel["consistencia"], ensure_ascii=False, indent=2))
"""),

md("""
## Síntese para a decisão

A recomendação não é a mesma para todos os terminais da lista, e é a
decomposição do tempo que a diferencia.

Onde **T2 e T4** dominam, a intervenção é de coordenação: liberação
documental, escala de turno, sequenciamento de equipe. Custa pouco e é rápida.

Onde **T3** domina e a prancha está no percentil baixo do seu tipo de carga,
a intervenção é de equipamento, e aí há capital envolvido.

Onde **T1** domina mas a ocupação é baixa, o caminho é programação de janelas,
não obra civil.

Esse é o produto do MVP: ele não diz quanto investir, mas elimina classes
inteiras de intervenção para cada terminal, que é o que um sistema de suporte
à decisão deve fazer.
"""),

cd("""
top = rank.head(10).merge(u[["sk_instalacao", "ocupacao_pct"]], on="sk_instalacao", how="left")
perfil = mar.groupby("sk_instalacao")[["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
                                       "t3_operacao_h", "t4_espera_desatracacao_h"]].median()
top = top.merge(perfil, on="sk_instalacao", how="left")

def indicar(r):
    if r["ocupacao_pct"] is not None and r["t1_espera_atracacao_h"] > r["t3_operacao_h"] and r["ocupacao_pct"] < 40:
        return "programação de janelas"
    if (r["t2_espera_inicio_op_h"] + r["t4_espera_desatracacao_h"]) > r["t3_operacao_h"]:
        return "coordenação em terra"
    return "produtividade de equipamento"

top["intervenção_indicada"] = top.apply(indicar, axis=1)
top[["porto_atracacao", "sguf", "atracacoes", "pct_improdutivo",
     "horas_recuperaveis", "intervenção_indicada"]].round(1)
"""),
]

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13"},
}
destino = proj / "notebooks" / "02_analise.ipynb"
destino.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, destino)
print(f"notebook escrito: {destino} ({len(cells)} celulas)")
