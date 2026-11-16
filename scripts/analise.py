"""
Analise: solucao do problema de decisao sobre capacidade portuaria.

Responde as perguntas de negocio P1 a P4 definidas no README.
P5 (qualidade) e respondida por qualidade.py.

Uso: python3 -I analise.py --proj <dir_projeto> --ano 2025
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HORAS_ANO = 8760.0


def carregar(proj: Path, ano: int):
    g = proj / "dados" / "gold"
    fato = pd.read_parquet(g / f"fato_atracacao_{ano}.parquet")
    dim_i = pd.read_parquet(g / f"dim_instalacao_{ano}.parquet")
    dim_b = pd.read_parquet(g / f"dim_berco_{ano}.parquet")
    dim_n = pd.read_parquet(g / f"dim_navegacao_{ano}.parquet")
    dim_c = pd.read_parquet(g / f"dim_natureza_carga_{ano}.parquet")
    silver = pd.read_parquet(proj / "dados" / "silver" / f"atracacao_tratada_{ano}.parquet")
    return fato, dim_i, dim_b, dim_n, dim_c, silver


def posicoes_efetivas(silver: pd.DataFrame) -> pd.DataFrame:
    """Infere quantas embarcacoes um berco comporta simultaneamente.

    A auditoria de acuracia mostrou que IDBerco nao representa uma posicao
    exclusiva: ha sobreposicao de janelas de ocupacao em 65% dos bercos.
    Assumir uma posicao por berco produziria taxas de ocupacao acima de
    100% e inviabilizaria qualquer analise de congestionamento.

    A ocupacao simultanea maxima observada no ano e usada como estimativa
    do numero de posicoes de atracacao do berco. E uma estimativa por
    limite inferior: se duas embarcacoes couberam ao mesmo tempo, existem
    ao menos duas posicoes.
    """
    s = silver.dropna(subset=["Data Atracação", "Data Desatracação"]).copy()
    s = s[~s["flag_cronologia_invalida"] & ~s["flag_estadia_outlier"]]

    eventos = pd.concat([
        pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Atracação"], "d": 1}),
        pd.DataFrame({"IDBerco": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
    ]).sort_values(["IDBerco", "t", "d"], ascending=[True, True, False])
    eventos["ocupacao"] = eventos.groupby("IDBerco")["d"].cumsum()
    pos = eventos.groupby("IDBerco")["ocupacao"].max().rename("posicoes_estimadas").reset_index()
    pos["posicoes_estimadas"] = pos["posicoes_estimadas"].clip(lower=1)
    return pos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()
    proj = Path(a.proj)
    fato, dim_i, dim_b, dim_n, dim_c, silver = carregar(proj, a.ano)

    base = (
        fato[fato["flag_apto_analise_tempo"]]
        .merge(dim_i, on="sk_instalacao", how="left")
        .merge(dim_n, on="sk_navegacao", how="left")
        .merge(dim_c, on="sk_natureza", how="left")
    )
    R: dict = {"ano": a.ano, "atracacoes_analisadas": int(len(base))}

    # ==================================================================
    # P1. Decomposicao do tempo do navio no porto
    # ==================================================================
    comp = base.dropna(subset=["t1_espera_atracacao_h", "t2_espera_inicio_op_h",
                               "t3_operacao_h", "t4_espera_desatracacao_h"])
    tot = {
        "t1_espera_atracacao": float(comp["t1_espera_atracacao_h"].sum()),
        "t2_espera_inicio_op": float(comp["t2_espera_inicio_op_h"].sum()),
        "t3_operacao": float(comp["t3_operacao_h"].sum()),
        "t4_espera_desatracacao": float(comp["t4_espera_desatracacao_h"].sum()),
    }
    soma = sum(tot.values())
    R["p1_decomposicao"] = {
        "atracacoes_com_cadeia_completa": int(len(comp)),
        "navio_hora_total": round(soma, 1),
        "horas_por_etapa": {k: round(v, 1) for k, v in tot.items()},
        "participacao_pct": {k: round(v / soma * 100, 2) for k, v in tot.items()},
        "mediana_h": {
            "t1": round(float(comp["t1_espera_atracacao_h"].median()), 2),
            "t2": round(float(comp["t2_espera_inicio_op_h"].median()), 2),
            "t3": round(float(comp["t3_operacao_h"].median()), 2),
            "t4": round(float(comp["t4_espera_desatracacao_h"].median()), 2),
            "estadia": round(float(comp["te_estadia_h"].median()), 2),
        },
        "media_h": {
            "t1": round(float(comp["t1_espera_atracacao_h"].mean()), 2),
            "t2": round(float(comp["t2_espera_inicio_op_h"].mean()), 2),
            "t3": round(float(comp["t3_operacao_h"].mean()), 2),
            "t4": round(float(comp["t4_espera_desatracacao_h"].mean()), 2),
            "estadia": round(float(comp["te_estadia_h"].mean()), 2),
        },
        "desvio_padrao_h": {
            "t1": round(float(comp["t1_espera_atracacao_h"].std()), 2),
            "t3": round(float(comp["t3_operacao_h"].std()), 2),
            "estadia": round(float(comp["te_estadia_h"].std()), 2),
        },
        "berco_improdutivo_total_h": round(float(tot["t2_espera_inicio_op"] + tot["t4_espera_desatracacao"]), 1),
        "berco_improdutivo_pct_do_tempo_atracado": round(
            (tot["t2_espera_inicio_op"] + tot["t4_espera_desatracacao"])
            / (tot["t2_espera_inicio_op"] + tot["t3_operacao"] + tot["t4_espera_desatracacao"]) * 100, 2),
    }

    # ==================================================================
    # P2. Onde esta concentrado o berco-hora improdutivo
    # ==================================================================
    por_inst = (
        comp.groupby(["sk_instalacao", "porto_atracacao", "complexo_portuario",
                      "sguf", "tipo_autoridade"])
        .agg(
            atracacoes=("sk_atracacao", "count"),
            improdutivo_h=("berco_improdutivo_h", "sum"),
            improdutivo_medio_h=("berco_improdutivo_h", "mean"),
            operacao_h=("t3_operacao_h", "sum"),
            atracado_h=("ta_atracado_h", "sum"),
            espera_h=("t1_espera_atracacao_h", "sum"),
            peso_t=("peso_bruto_t", "sum"),
        ).reset_index()
    )
    por_inst["pct_improdutivo"] = (por_inst["improdutivo_h"] / por_inst["atracado_h"] * 100).round(2)
    por_inst["posicoes_berco_equivalentes"] = (por_inst["improdutivo_h"] / HORAS_ANO).round(2)
    por_inst = por_inst.sort_values("improdutivo_h", ascending=False)

    top = por_inst.head(20)
    R["p2_concentracao"] = {
        "improdutivo_total_h": round(float(por_inst["improdutivo_h"].sum()), 1),
        "equivalente_em_posicoes_de_berco": round(float(por_inst["improdutivo_h"].sum() / HORAS_ANO), 1),
        "instalacoes_avaliadas": int(len(por_inst)),
        "pct_do_improdutivo_no_top10": round(
            float(por_inst.head(10)["improdutivo_h"].sum() / por_inst["improdutivo_h"].sum() * 100), 2),
        "pct_do_improdutivo_no_top20": round(
            float(top["improdutivo_h"].sum() / por_inst["improdutivo_h"].sum() * 100), 2),
        "top20": top[["sk_instalacao", "porto_atracacao", "complexo_portuario", "sguf",
                      "tipo_autoridade", "atracacoes", "improdutivo_h", "improdutivo_medio_h",
                      "pct_improdutivo", "posicoes_berco_equivalentes"]]
               .round(2).to_dict(orient="records"),
    }
    por_inst.to_csv(proj / "outputs" / f"ranking_instalacoes_{a.ano}.csv", index=False)

    # ==================================================================
    # P3. A espera para atracar e explicada por congestionamento?
    # ==================================================================
    pos = posicoes_efetivas(silver)
    dim_b2 = dim_b.merge(pos, left_on="sk_berco", right_on="IDBerco", how="left")
    dim_b2["posicoes_estimadas"] = dim_b2["posicoes_estimadas"].fillna(1)
    pos_inst = dim_b2.groupby("sk_instalacao")["posicoes_estimadas"].sum().rename("posicoes_inst").reset_index()

    util = por_inst.merge(pos_inst, on="sk_instalacao", how="left")
    util["posicoes_inst"] = util["posicoes_inst"].fillna(1)
    util["ocupacao_pct"] = (util["atracado_h"] / (HORAS_ANO * util["posicoes_inst"]) * 100).round(2)
    util["espera_media_h"] = (util["espera_h"] / util["atracacoes"]).round(2)

    # So instalacoes com volume relevante entram na correlacao, para que o
    # resultado nao seja dominado por terminais com poucas atracacoes.
    rel = util[(util["atracacoes"] >= 100) & util["ocupacao_pct"].notna() & util["espera_media_h"].notna()]
    rho, p_rho = stats.spearmanr(rel["ocupacao_pct"], rel["espera_media_h"])

    # Comparacao entre instalacoes muito ocupadas e pouco ocupadas
    q1, q3 = rel["ocupacao_pct"].quantile([0.25, 0.75])
    baixa = rel[rel["ocupacao_pct"] <= q1]["espera_media_h"]
    alta = rel[rel["ocupacao_pct"] >= q3]["espera_media_h"]
    tstat, p_t = stats.ttest_ind(alta, baixa, equal_var=False)

    R["p3_congestionamento"] = {
        "instalacoes_na_analise": int(len(rel)),
        "criterio": "instalacoes com ao menos 100 atracacoes aptas",
        "ocupacao_mediana_pct": round(float(rel["ocupacao_pct"].median()), 2),
        "ocupacao_p90_pct": round(float(rel["ocupacao_pct"].quantile(0.9)), 2),
        "spearman_ocupacao_vs_espera": {
            "rho": round(float(rho), 4), "p_valor": float(f"{p_rho:.6g}"),
        },
        "quartil_baixa_ocupacao": {
            "n": int(len(baixa)), "ocupacao_max_pct": round(float(q1), 2),
            "espera_media_h": round(float(baixa.mean()), 2),
            "desvio_padrao_h": round(float(baixa.std()), 2),
        },
        "quartil_alta_ocupacao": {
            "n": int(len(alta)), "ocupacao_min_pct": round(float(q3), 2),
            "espera_media_h": round(float(alta.mean()), 2),
            "desvio_padrao_h": round(float(alta.std()), 2),
        },
        "teste_t_welch": {"t": round(float(tstat), 4), "p_valor": float(f"{p_t:.6g}")},
    }
    util.to_csv(proj / "outputs" / f"ocupacao_instalacoes_{a.ano}.csv", index=False)

    # ==================================================================
    # P4. A produtividade varia mais entre instalacoes ou entre cargas?
    # ==================================================================
    prod = base[
        base["operacao_produtiva"]
        & base["prancha_operacional_th"].notna()
        & ~base["flag_prancha_implausivel"]
        & base["flag_atracacao_exclusiva"].fillna(False)
    ].copy()
    prod["log_prancha"] = np.log(prod["prancha_operacional_th"])

    def eta2(df: pd.DataFrame, grupo: str, alvo: str = "log_prancha") -> float:
        """Proporcao da variancia do alvo explicada pelo agrupamento."""
        media = df[alvo].mean()
        sqt = ((df[alvo] - media) ** 2).sum()
        g = df.groupby(grupo)[alvo].agg(["mean", "count"])
        sqe = (g["count"] * (g["mean"] - media) ** 2).sum()
        return float(sqe / sqt)

    e_inst = eta2(prod, "sk_instalacao")
    e_nat = eta2(prod, "natureza_carga")
    e_nav = eta2(prod, "tipo_navegacao")

    por_nat = prod.groupby("natureza_carga")["prancha_operacional_th"].agg(
        n="count", mediana="median", media="mean", desvio="std",
        p10=lambda x: x.quantile(0.10), p90=lambda x: x.quantile(0.90),
    ).round(2).reset_index()

    # Dispersao interna: dentro de um mesmo perfil de carga, quanto variam
    # as instalacoes? Razao p90/p10 da mediana por instalacao.
    disp = []
    for nat_nome, g in prod.groupby("natureza_carga"):
        med_inst = g.groupby("sk_instalacao")["prancha_operacional_th"].median()
        med_inst = med_inst[g.groupby("sk_instalacao").size() >= 30]
        if len(med_inst) >= 5:
            disp.append({
                "natureza_carga": nat_nome,
                "instalacoes": int(len(med_inst)),
                "mediana_p10": round(float(med_inst.quantile(0.10)), 2),
                "mediana_p90": round(float(med_inst.quantile(0.90)), 2),
                "razao_p90_p10": round(float(med_inst.quantile(0.90) / med_inst.quantile(0.10)), 2),
            })

    R["p4_produtividade"] = {
        "atracacoes_na_analise": int(len(prod)),
        "criterio": "operacao produtiva, atracacao exclusiva, prancha plausivel",
        "variancia_explicada_log_prancha": {
            "por_instalacao": round(e_inst, 4),
            "por_natureza_da_carga": round(e_nat, 4),
            "por_tipo_de_navegacao": round(e_nav, 4),
        },
        "prancha_por_natureza_th": por_nat.to_dict(orient="records"),
        "dispersao_entre_instalacoes_dentro_da_carga": disp,
    }

    # ==================================================================
    # Sintese para a decisao
    # ==================================================================
    ganho_alvo = por_inst.head(10).copy()
    # Cenario: as 10 instalacoes com maior berco-hora improdutivo reduzem seu
    # tempo improdutivo ao nivel mediano das instalacoes comparaveis.
    mediana_pct = float(por_inst[por_inst["atracacoes"] >= 100]["pct_improdutivo"].median())
    ganho_alvo["pct_alvo"] = mediana_pct
    ganho_alvo["horas_recuperaveis"] = np.where(
        ganho_alvo["pct_improdutivo"] > mediana_pct,
        ganho_alvo["improdutivo_h"] - (ganho_alvo["atracado_h"] * mediana_pct / 100),
        0.0,
    )
    R["sintese_decisao"] = {
        "pct_improdutivo_mediano_do_setor": round(mediana_pct, 2),
        "horas_recuperaveis_top10": round(float(ganho_alvo["horas_recuperaveis"].sum()), 1),
        "posicoes_de_berco_equivalentes_recuperaveis": round(
            float(ganho_alvo["horas_recuperaveis"].sum() / HORAS_ANO), 2),
        "detalhe": ganho_alvo[["porto_atracacao", "complexo_portuario", "atracacoes",
                               "pct_improdutivo", "horas_recuperaveis"]].round(2).to_dict(orient="records"),
    }

    out = proj / "outputs" / f"resultados_analise_{a.ano}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
    print(json.dumps(R, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
