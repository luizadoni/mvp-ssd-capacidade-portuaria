"""
Analise segmentada: correcao dos tres vieses identificados no diagnostico.

O diagnostico critico mostrou que a leitura direta dos indicadores agregados
leva a recomendacao errada. Esta etapa refaz a analise controlando por:
  1. modo de navegacao (maritimo x interior x apoio), porque a espera
     atracada tem significado operacional distinto em cada um;
  2. escolha do estimador (soma x mediana), reportando os dois;
  3. multiplicidade de posicoes por berco.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HORAS_ANO = 8760.0
SEGMENTOS = {
    "Maritimo de carga": ["Longo Curso", "Cabotagem"],
    "Interior (fluvial)": ["Interior"],
    "Apoio": ["Apoio Marítimo", "Apoio Portuário"],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()
    proj, ano = Path(a.proj), a.ano
    g = proj / "dados" / "gold"

    fato = pd.read_parquet(g / f"fato_atracacao_{ano}.parquet")
    dim_i = pd.read_parquet(g / f"dim_instalacao_{ano}.parquet")
    dim_b = pd.read_parquet(g / f"dim_berco_{ano}.parquet")
    dim_n = pd.read_parquet(g / f"dim_navegacao_{ano}.parquet")
    dim_c = pd.read_parquet(g / f"dim_natureza_carga_{ano}.parquet")
    silver = pd.read_parquet(proj / "dados" / "silver" / f"atracacao_tratada_{ano}.parquet")

    b = (fato[fato["flag_apto_analise_tempo"]]
         .merge(dim_i, on="sk_instalacao", how="left")
         .merge(dim_n, on="sk_navegacao", how="left")
         .merge(dim_c, on="sk_natureza", how="left"))
    b["segmento"] = "Outros"
    for nome, tipos in SEGMENTOS.items():
        b.loc[b["tipo_navegacao"].isin(tipos), "segmento"] = nome

    comp = b.dropna(subset=["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
                            "t3_operacao_h", "t4_espera_desatracacao_h"]).copy()
    R: dict = {"ano": ano}

    # ------------------------------------------------------------------
    # A. Decomposicao por segmento, com os dois estimadores
    # ------------------------------------------------------------------
    etapas = ["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
              "t3_operacao_h", "t4_espera_desatracacao_h"]
    seg_out = []
    for seg, grp in comp.groupby("segmento"):
        somas = grp[etapas].sum()
        meds = grp[etapas].median()
        seg_out.append({
            "segmento": seg,
            "atracacoes": int(len(grp)),
            "peso_total_milhoes_t": round(float(grp["peso_bruto_t"].sum() / 1e6), 2),
            "navio_hora_total": round(float(somas.sum()), 1),
            "share_por_soma_pct": {k.replace("_h", ""): round(float(v / somas.sum() * 100), 2)
                                   for k, v in somas.items()},
            "share_por_mediana_pct": {k.replace("_h", ""): round(float(v / meds.sum() * 100), 2)
                                      for k, v in meds.items()},
            "estadia_mediana_h": round(float(grp["te_estadia_h"].median()), 2),
            "estadia_media_h": round(float(grp["te_estadia_h"].mean()), 2),
            "estadia_p90_h": round(float(grp["te_estadia_h"].quantile(0.9)), 2),
            "berco_improdutivo_pct_atracado": round(
                float((somas["t2_espera_inicio_op_h"] + somas["t4_espera_desatracacao_h"])
                      / (somas["t2_espera_inicio_op_h"] + somas["t3_operacao_h"]
                         + somas["t4_espera_desatracacao_h"]) * 100), 2),
        })
    R["a_decomposicao_por_segmento"] = sorted(seg_out, key=lambda x: -x["navio_hora_total"])

    # ------------------------------------------------------------------
    # B. Ranking corrigido: so segmento maritimo de carga, so operacao
    #    produtiva. E este o universo em que berco improdutivo significa
    #    capacidade de cais perdida.
    # ------------------------------------------------------------------
    mar = comp[(comp["segmento"] == "Maritimo de carga") & comp["operacao_produtiva"]].copy()
    rank = (mar.groupby(["sk_instalacao", "porto_atracacao", "complexo_portuario", "sguf",
                         "tipo_autoridade"])
            .agg(atracacoes=("sk_atracacao", "count"),
                 improdutivo_h=("berco_improdutivo_h", "sum"),
                 improdutivo_medio_h=("berco_improdutivo_h", "mean"),
                 improdutivo_mediano_h=("berco_improdutivo_h", "median"),
                 operacao_h=("t3_operacao_h", "sum"),
                 atracado_h=("ta_atracado_h", "sum"),
                 espera_h=("t1_espera_atracacao_h", "sum"),
                 peso_t=("peso_bruto_t", "sum"))
            .reset_index())
    rank["pct_improdutivo"] = (rank["improdutivo_h"] / rank["atracado_h"] * 100).round(2)
    rank["posicoes_equivalentes"] = (rank["improdutivo_h"] / HORAS_ANO).round(2)
    rank["t_por_hora_atracado"] = (rank["peso_t"] / rank["atracado_h"]).round(1)
    rank = rank[rank["atracacoes"] >= 50].sort_values("improdutivo_h", ascending=False)

    mediana_setor = float(rank["pct_improdutivo"].median())
    rank["horas_recuperaveis"] = np.where(
        rank["pct_improdutivo"] > mediana_setor,
        rank["improdutivo_h"] - rank["atracado_h"] * mediana_setor / 100, 0.0)
    rank = rank.sort_values("horas_recuperaveis", ascending=False)
    rank.to_csv(proj / "outputs" / f"ranking_maritimo_{ano}.csv", index=False)

    R["b_ranking_corrigido"] = {
        "universo": "navegacao de longo curso e cabotagem, operacao de movimentacao de carga, instalacoes com 50+ atracacoes",
        "instalacoes": int(len(rank)),
        "atracacoes": int(rank["atracacoes"].sum()),
        "improdutivo_total_h": round(float(rank["improdutivo_h"].sum()), 1),
        "pct_improdutivo_mediano_setor": round(mediana_setor, 2),
        "horas_recuperaveis_total": round(float(rank["horas_recuperaveis"].sum()), 1),
        "posicoes_de_cais_equivalentes_recuperaveis": round(
            float(rank["horas_recuperaveis"].sum() / HORAS_ANO), 2),
        "pct_recuperavel_no_top10": round(
            float(rank.head(10)["horas_recuperaveis"].sum() / rank["horas_recuperaveis"].sum() * 100), 2),
        "top15": rank.head(15)[["porto_atracacao", "complexo_portuario", "sguf", "tipo_autoridade",
                                "atracacoes", "improdutivo_h", "improdutivo_mediano_h",
                                "pct_improdutivo", "horas_recuperaveis", "posicoes_equivalentes"]]
                 .round(2).to_dict(orient="records"),
    }

    # ------------------------------------------------------------------
    # C. Quanto a leitura ingenua erraria
    # ------------------------------------------------------------------
    todos = (comp.groupby("sk_instalacao")
             .agg(improdutivo_h=("berco_improdutivo_h", "sum"))
             .sort_values("improdutivo_h", ascending=False))
    top10_ingenuo = set(todos.head(10).index)
    top10_corrigido = set(rank.head(10)["sk_instalacao"])
    R["c_custo_do_vies"] = {
        "top10_ingenuo": list(top10_ingenuo),
        "top10_corrigido": list(top10_corrigido),
        "instalacoes_em_comum": len(top10_ingenuo & top10_corrigido),
        "leitura": ("Das dez instalacoes que o ranking nao segmentado apontaria para "
                    "intervencao, apenas as que aparecem em ambos os conjuntos resistem "
                    "ao controle por modo de navegacao."),
    }

    # ------------------------------------------------------------------
    # D. Congestionamento dentro do segmento maritimo
    # ------------------------------------------------------------------
    s = silver.dropna(subset=["Data Atracação", "Data Desatracação"])
    s = s[~s["flag_cronologia_invalida"] & ~s["flag_estadia_outlier"]]
    ev = pd.concat([
        pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Atracação"], "d": 1}),
        pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
    ]).sort_values(["IDBerco", "t", "d"], ascending=[True, True, False])
    ev["oc"] = ev.groupby("IDBerco")["d"].cumsum()
    pos = ev.groupby("IDBerco")["oc"].max().clip(lower=1).rename("posicoes").reset_index()
    pos_inst = (dim_b.merge(pos, left_on="sk_berco", right_on="IDBerco", how="left")
                .groupby("sk_instalacao")["posicoes"].sum().rename("posicoes_inst").reset_index())

    u = rank.merge(pos_inst, on="sk_instalacao", how="left")
    u["posicoes_inst"] = u["posicoes_inst"].fillna(1)
    u["ocupacao_pct"] = (u["atracado_h"] / (HORAS_ANO * u["posicoes_inst"]) * 100).round(2)
    u["espera_mediana_h"] = mar.groupby("sk_instalacao")["t1_espera_atracacao_h"].median().reindex(u["sk_instalacao"]).values
    uu = u.dropna(subset=["ocupacao_pct", "espera_mediana_h"])
    rho, p = stats.spearmanr(uu["ocupacao_pct"], uu["espera_mediana_h"])
    R["d_congestionamento_maritimo"] = {
        "instalacoes": int(len(uu)),
        "spearman_rho": round(float(rho), 4),
        "p_valor": float(f"{p:.6g}"),
        "variancia_de_ordem_explicada_pct": round(float(rho ** 2 * 100), 1),
        "ocupacao_mediana_pct": round(float(uu["ocupacao_pct"].median()), 2),
        "espera_mediana_h": round(float(uu["espera_mediana_h"].median()), 2),
    }

    # ------------------------------------------------------------------
    # E. Robustez: multiplicidade de berco
    # ------------------------------------------------------------------
    R["e_multiplicidade_berco"] = {
        "bercos_avaliados": int(len(pos)),
        "bercos_exclusivos": int((pos["posicoes"] <= 1).sum()),
        "pct_exclusivos": round(float((pos["posicoes"] <= 1).mean() * 100), 2),
        "mediana_posicoes": int(pos["posicoes"].median()),
        "p90_posicoes": int(pos["posicoes"].quantile(0.9)),
        "max_posicoes": int(pos["posicoes"].max()),
        "implicacao": ("IDBerco nao e uma posicao de atracacao exclusiva. Taxas de "
                       "ocupacao calculadas com um berco = uma posicao superestimariam "
                       "a utilizacao e levariam a diagnostico falso de congestionamento."),
    }

    out = proj / "outputs" / f"resultados_segmentados_{ano}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
    print(json.dumps(R, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
