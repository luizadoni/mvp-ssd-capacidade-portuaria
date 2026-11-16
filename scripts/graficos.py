"""Gera as figuras do relatorio. Saida em outputs/figuras.

Uso: python3 -I graficos.py --proj <dir_projeto> --ano 2025
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8882"
GRID = "#e4e3df"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.size": 10,
    "font.family": "DejaVu Sans", "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titlecolor": INK, "axes.grid": False,
})


def limpa(ax, eixo="x"):
    for s in ["top", "right", "left", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    if eixo == "x":
        ax.xaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    elif eixo == "y":
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)


def mil(x, _=None):
    return f"{x:,.0f}".replace(",", ".")


def fig1(seg, out):
    """Decomposicao do tempo por segmento: soma contra mediana."""
    etapas = ["t1_espera_atracacao", "t2_espera_inicio_op", "t3_operacao", "t4_espera_desatracacao"]
    rotulos = ["T1 espera para atracar", "T2 espera p/ iniciar", "T3 operação", "T4 espera p/ sair"]
    segs = [s["segmento"] for s in seg]

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.0))
    for ax, chave, titulo in zip(
        axes, ["share_por_soma_pct", "share_por_mediana_pct"],
        ["Somando todas as horas do ano", "Usando a atracação mediana"],
    ):
        esq = np.zeros(len(segs))
        for i, (e, rot) in enumerate(zip(etapas, rotulos)):
            vals = np.array([s[chave][e] for s in seg])
            ax.barh(segs, vals, left=esq, color=C[i], height=0.52,
                    label=rot, edgecolor=SURFACE, linewidth=2)
            for j, (v, l) in enumerate(zip(vals, esq)):
                if v >= 6:
                    ax.text(l + v / 2, j, f"{v:.0f}%", ha="center", va="center",
                            color="white", fontsize=9, fontweight="bold")
            esq += vals
        ax.set_xlim(0, 100)
        ax.set_title(titulo, fontsize=11, fontweight="bold", pad=10, loc="left")
        ax.set_xlabel("participação no tempo do navio (%)")
        limpa(ax, "x")
        ax.invert_yaxis()
    axes[1].set_yticklabels([])
    fig.subplots_adjust(wspace=0.08)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.05, -0.26), ncol=4,
                   frameon=False, fontsize=9.5)
    fig.suptitle("O mesmo dado, dois estimadores, duas conclusões opostas",
                 fontsize=13, fontweight="bold", x=0.009, ha="left", y=1.04)
    fig.text(0.009, 0.965,
             "Somar horas faz a espera parecer o maior problema. A atracação típica mostra que o tempo é da operação.",
             fontsize=9.5, color=INK2, ha="left")
    fig.savefig(out / "fig1_decomposicao_tempo.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig2(top, out):
    d = pd.DataFrame(top).head(12).iloc[::-1]
    nomes = [n if len(n) <= 42 else n[:40] + "…" for n in d["porto_atracacao"]]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.barh(nomes, d["horas_recuperaveis"], color=C[0], height=0.62)
    for i, (v, p) in enumerate(zip(d["horas_recuperaveis"], d["pct_improdutivo"])):
        ax.text(v + max(d["horas_recuperaveis"]) * 0.012, i,
                f"{mil(v)} h   ·   {p:.0f}% do tempo atracado",
                va="center", fontsize=9, color=INK2)
    ax.set_xlim(0, max(d["horas_recuperaveis"]) * 1.52)
    ax.xaxis.set_major_formatter(FuncFormatter(mil))
    ax.set_xlabel("horas de berço recuperáveis por ano")
    limpa(ax, "x")
    fig.suptitle("Onde há capacidade de cais a recuperar, no segmento marítimo de carga",
                 fontsize=13, fontweight="bold", x=0.008, ha="left", y=1.06)
    fig.text(0.008, 1.005,
             "Alvo: trazer o tempo de berço sem operação ao nível mediano do setor (18,2% do tempo atracado).",
             fontsize=9.5, color=INK2, ha="left")
    fig.savefig(out / "fig2_ranking_recuperavel.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig3(proj, ano, dcong, out):
    g = proj / "dados" / "gold"
    fato = pd.read_parquet(g / f"fato_atracacao_{ano}.parquet")
    dim_n = pd.read_parquet(g / f"dim_navegacao_{ano}.parquet")
    m = fato[fato["flag_apto_analise_tempo"]].merge(dim_n, on="sk_navegacao", how="left")
    m = m[m["tipo_navegacao"].isin(["Longo Curso", "Cabotagem"]) & m["operacao_produtiva"]]
    esp = (m.groupby("sk_instalacao")["t1_espera_atracacao_h"].median()
           .rename("espera_mediana_h").reset_index())

    u = pd.read_csv(proj / "outputs" / f"ranking_maritimo_{ano}.csv")
    oc = pd.read_csv(proj / "outputs" / f"ocupacao_instalacoes_{ano}.csv")[["sk_instalacao", "ocupacao_pct"]]
    d = (u.merge(oc, on="sk_instalacao", how="inner")
          .merge(esp, on="sk_instalacao", how="left")
          .dropna(subset=["ocupacao_pct", "espera_mediana_h"]))
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ax.scatter(d["ocupacao_pct"], d["espera_mediana_h"], s=np.clip(d["atracacoes"] / 6, 18, 320),
               color=C[0], alpha=0.55, edgecolor=SURFACE, linewidth=1.6, zorder=3)
    ax.set_xlabel("ocupação estimada do cais (%)")
    ax.set_ylabel("espera mediana para atracar, T1 (h)")
    limpa(ax, "y")
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    ax.set_title("Congestionamento explica pouco da espera", fontsize=13,
                 fontweight="bold", loc="left", pad=16)
    txt = (f"Spearman ρ = {dcong['spearman_rho']:.2f}  (p = {dcong['p_valor']:.1e})\n"
           f"explica {dcong['variancia_de_ordem_explicada_pct']:.0f}% da variação de ordem\n"
           f"n = {dcong['instalacoes']} instalações · área = nº de atracações")
    ax.text(0.98, 0.96, txt, transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, color=INK2,
            bbox=dict(boxstyle="round,pad=0.6", fc=SURFACE, ec=GRID))
    fig.text(0.0, 1.0,
             "Há relação, mas fraca: terminais com ocupação parecida esperam tempos muito diferentes.",
             fontsize=9.5, color=INK2, transform=ax.transAxes, va="bottom")
    fig.savefig(out / "fig3_ocupacao_vs_espera.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig4(p4, out):
    ve = p4["variancia_explicada_log_prancha"]
    disp = pd.DataFrame(p4["dispersao_entre_instalacoes_dentro_da_carga"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.4),
                             gridspec_kw={"width_ratios": [1, 1.35], "wspace": 0.42})

    ax = axes[0]
    k = ["por_instalacao", "por_natureza_da_carga", "por_tipo_de_navegacao"]
    rot = ["Qual instalação", "Qual tipo de carga", "Qual navegação"]
    vals = [ve[x] * 100 for x in k]
    ax.barh(rot[::-1], vals[::-1], color=[C[2], C[3], C[1]][::-1], height=0.55)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1.2, i, f"{v:.1f}%", va="center", fontsize=10,
                color=INK, fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.22)
    ax.set_xlabel("variação da produtividade explicada (%)")
    limpa(ax, "x")
    ax.set_title("O terminal pesa 3x mais que o tipo de carga",
                 fontsize=11, fontweight="bold", loc="left", pad=10)

    ax = axes[1]
    d = disp.sort_values("razao_p90_p10")
    y = np.arange(len(d))
    ax.hlines(y, d["mediana_p10"], d["mediana_p90"], color=GRID, lw=5, zorder=1)
    ax.scatter(d["mediana_p10"], y, color=C[1], s=70, zorder=3, label="instalação no p10")
    ax.scatter(d["mediana_p90"], y, color=C[0], s=70, zorder=3, label="instalação no p90")
    for i, r in enumerate(d.itertuples()):
        ax.text(r.mediana_p90 * 1.12, i, f"{r.razao_p90_p10:.0f}x",
                va="center", fontsize=9.5, color=INK, fontweight="bold")
    ax.set_yticks(y, d["natureza_carga"])
    ax.set_xscale("log")
    ax.set_xlabel("prancha mediana da instalação (t/h, escala log)")
    ax.set_xlim(20, 9000)
    ax.set_ylim(-0.75, len(d) - 0.25)
    limpa(ax, "x")
    ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=2,
              bbox_to_anchor=(0.0, -0.02))
    ax.set_title("Dentro do mesmo tipo de carga, a distância entre terminais é enorme",
                 fontsize=11, fontweight="bold", loc="left", pad=10)
    fig.savefig(out / "fig4_produtividade.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig5(proj, ano, out):
    silver = pd.read_parquet(proj / "dados" / "silver" / f"atracacao_tratada_{ano}.parquet")
    s = silver.dropna(subset=["Data Atracação", "Data Desatracação"])
    s = s[~s["flag_cronologia_invalida"] & ~s["flag_estadia_outlier"]]
    ev = pd.concat([
        pd.DataFrame({"b": s["IDBerco"], "t": s["Data Atracação"], "d": 1}),
        pd.DataFrame({"b": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
    ]).sort_values(["b", "t", "d"], ascending=[True, True, False])
    ev["oc"] = ev.groupby("b")["d"].cumsum()
    pos = ev.groupby("b")["oc"].max().clip(lower=1)
    cat = pd.cut(pos, [0, 1, 2, 4, 8, 1e9],
                 labels=["1\n(exclusivo)", "2", "3 a 4", "5 a 8", "9 ou mais"])
    cont = cat.value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    cores = [C[2]] + [C[1]] * 4
    ax.bar(cont.index.astype(str), cont.values, color=cores, width=0.6)
    for i, v in enumerate(cont.values):
        ax.text(i, v + 6, str(v), ha="center", fontsize=10, color=INK, fontweight="bold")
    ax.set_ylabel("número de berços")
    ax.set_xlabel("embarcações simultâneas observadas no berço durante 2025")
    ax.set_ylim(0, cont.max() * 1.18)
    limpa(ax, "y")
    ax.set_title("Só 35% dos berços são de fato uma posição exclusiva",
                 fontsize=13, fontweight="bold", loc="left", pad=16)
    fig.text(0.0, 1.0,
             "Calcular ocupação supondo um navio por berço produziria taxas acima de 100% e falso diagnóstico de fila.",
             fontsize=9.5, color=INK2, transform=ax.transAxes, va="bottom")
    fig.savefig(out / "fig5_multiplicidade_berco.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()
    proj = Path(a.proj)
    out = proj / "outputs" / "figuras"
    out.mkdir(parents=True, exist_ok=True)

    seg = json.load(open(proj / "outputs" / f"resultados_segmentados_{a.ano}.json", encoding="utf-8"))
    ana = json.load(open(proj / "outputs" / f"resultados_analise_{a.ano}.json", encoding="utf-8"))

    principais = [s for s in seg["a_decomposicao_por_segmento"]
                  if s["segmento"] in ("Maritimo de carga", "Interior (fluvial)", "Apoio")]
    fig1(principais, out)
    fig2(seg["b_ranking_corrigido"]["top15"], out)
    fig3(proj, a.ano, seg["d_congestionamento_maritimo"], out)
    fig4(ana["p4_produtividade"], out)
    fig5(proj, a.ano, out)
    print("figuras geradas:", sorted(p.name for p in out.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
