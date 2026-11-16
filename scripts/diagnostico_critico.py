"""Verificacoes criticas antes de transformar resultado em recomendacao.

Testa tres hipoteses alternativas que, se verdadeiras, invalidariam a
leitura ingenua do ranking de berco improdutivo:
  H1. As instalacoes do topo operam comboios/barcacas, em que a espera
      atracada e parte do modelo logistico, e nao perda evitavel.
  H2. A assimetria de T1 concentra o total em poucas atracacoes extremas.
  H3. A sobreposicao de berco se concentra em bercos especificos.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

proj = Path(sys.argv[1])
ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
g = proj / "dados" / "gold"

fato = pd.read_parquet(g / f"fato_atracacao_{ano}.parquet")
dim_i = pd.read_parquet(g / f"dim_instalacao_{ano}.parquet")
dim_n = pd.read_parquet(g / f"dim_navegacao_{ano}.parquet")
dim_c = pd.read_parquet(g / f"dim_natureza_carga_{ano}.parquet")
silver = pd.read_parquet(proj / "dados" / "silver" / f"atracacao_tratada_{ano}.parquet")

b = (fato[fato["flag_apto_analise_tempo"]]
     .merge(dim_i, on="sk_instalacao", how="left")
     .merge(dim_n, on="sk_navegacao", how="left")
     .merge(dim_c, on="sk_natureza", how="left"))

print("=" * 72)
print("H1. Perfil das instalacoes do topo do ranking de berco improdutivo")
print("=" * 72)
for cod in ["BRPA248", "BRSP011", "BRRO022", "BRNTR", "BRMCP", "BRSSZ"]:
    sub = b[b["sk_instalacao"] == cod]
    if sub.empty:
        continue
    nome = sub["porto_atracacao"].iloc[0]
    print(f"\n--- {cod} | {nome} | n={len(sub):,}")
    print("  navegacao:", sub["tipo_navegacao"].value_counts().head(3).to_dict())
    print("  operacao :", sub["tipo_operacao"].value_counts().head(3).to_dict())
    print("  natureza :", sub["natureza_carga"].value_counts().head(3).to_dict())
    print(f"  T1 med={sub['t1_espera_atracacao_h'].median():.1f}h  "
          f"T2 med={sub['t2_espera_inicio_op_h'].median():.1f}h  "
          f"T3 med={sub['t3_operacao_h'].median():.1f}h  "
          f"T4 med={sub['t4_espera_desatracacao_h'].median():.1f}h")
    print(f"  em rio: {sub['instalacao_em_rio'].value_counts().to_dict()}")
    print(f"  peso medio por atracacao: {sub['peso_bruto_t'].mean():,.0f} t")

print("\n" + "=" * 72)
print("H2. Concentracao do tempo de espera (T1)")
print("=" * 72)
# Mesmo subconjunto usado na decomposicao P1 (cadeia temporal completa),
# para que a assimetria relatada aqui e no notebook sejam o mesmo numero.
ETAPAS = ["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
          "t3_operacao_h", "t4_espera_desatracacao_h"]
comp_b = b.dropna(subset=ETAPAS)
t1 = comp_b["t1_espera_atracacao_h"]
tot = t1.sum()
for q in [0.50, 0.75, 0.90, 0.95, 0.99]:
    corte = t1.quantile(q)
    acima = t1[t1 > corte]
    print(f"  atracacoes acima do p{int(q*100)} ({corte:8.1f}h): "
          f"{len(acima):6,} atracacoes = {acima.sum()/tot*100:5.1f}% do total de horas de espera")
print(f"  assimetria (skew) de T1: {t1.skew():.2f}")
print(f"  media {t1.mean():.2f}h | mediana {t1.median():.2f}h | p99 {t1.quantile(0.99):.1f}h | max {t1.max():.1f}h")
print(f"  share de T1 no navio-hora total usando MEDIANAS em vez de somas:")
med = comp_b[["t1_espera_atracacao_h", "t2_espera_inicio_op_h", "t3_operacao_h",
         "t4_espera_desatracacao_h"]].median()
print("   ", (med / med.sum() * 100).round(2).to_dict())

print("\n" + "=" * 72)
print("H3. Concentracao da sobreposicao de berco")
print("=" * 72)
s = silver.dropna(subset=["Data Atracação", "Data Desatracação"]).copy()
s = s[~s["flag_cronologia_invalida"]].sort_values(["IDBerco", "Data Atracação"])
s["fim_ant"] = s.groupby("IDBerco")["Data Desatracação"].shift(1)
s["sobrep_h"] = (s["fim_ant"] - s["Data Atracação"]).dt.total_seconds() / 3600.0
s["tem_sobrep"] = s["sobrep_h"] > 0
por_berco = s.groupby("IDBerco").agg(n=("IDAtracacao", "count"), sobrep=("tem_sobrep", "sum"))
por_berco["taxa"] = por_berco["sobrep"] / por_berco["n"]
print(f"  bercos: {len(por_berco):,}")
print(f"  bercos com taxa de sobreposicao > 50%: {(por_berco['taxa'] > 0.5).sum()}")
print(f"  bercos com zero sobreposicao:          {(por_berco['sobrep'] == 0).sum()}")
print(f"  share das sobreposicoes nos 20 bercos mais afetados: "
      f"{por_berco.nlargest(20,'sobrep')['sobrep'].sum()/por_berco['sobrep'].sum()*100:.1f}%")

eventos = pd.concat([
    pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Atracação"], "d": 1}),
    pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
]).sort_values(["IDBerco", "t", "d"], ascending=[True, True, False])
eventos["oc"] = eventos.groupby("IDBerco")["d"].cumsum()
pos = eventos.groupby("IDBerco")["oc"].max()
print(f"\n  ocupacao simultanea maxima por berco:")
print("   ", pos.value_counts().sort_index().head(12).to_dict())
print(f"  bercos com ocupacao simultanea maxima = 1 (berco de fato exclusivo): {(pos<=1).sum()}")
print(f"  mediana de posicoes estimadas: {pos.median():.0f} | p90: {pos.quantile(0.9):.0f} | max: {pos.max()}")
