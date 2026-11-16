"""
Auditoria de qualidade de dados sobre a camada gold.

Duas saidas complementares, conforme a secao 3.5a do enunciado:

  1. ANALISE POR ATRIBUTO. Cada um dos atributos das seis tabelas do
     esquema estrela recebe medicao de completude, cardinalidade,
     dominio observado e aderencia ao dominio declarado. Nenhum
     atributo fica de fora, inclusive os que nao apresentaram problema,
     porque o enunciado pede que se demonstre a ausencia de problema e
     nao apenas que se relatem os problemas encontrados.

  2. ANALISE POR DIMENSAO DE QUALIDADE. As seis dimensoes classicas
     (completude, unicidade, consistencia, conformidade, acuracia e
     atualidade) agregadas no nivel do conjunto de dados.

Uso: python3 -I qualidade.py --proj <dir_projeto> --ano 2025
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

TABELAS = ["fato_atracacao", "dim_instalacao", "dim_berco", "dim_tempo",
           "dim_navegacao", "dim_natureza_carga"]

CHAVES_PRIMARIAS = {
    "fato_atracacao": "sk_atracacao",
    "dim_instalacao": "sk_instalacao",
    "dim_berco": "sk_berco",
    "dim_tempo": "sk_data",
    "dim_navegacao": "sk_navegacao",
    "dim_natureza_carga": "sk_natureza",
}

# Dominio declarado antes de olhar o dado. A conformidade e medida contra
# esta declaracao, nao contra o que o dado mostrou.
DOMINIO_DECLARADO = {
    ("fato_atracacao", "t1_espera_atracacao_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "t2_espera_inicio_op_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "t3_operacao_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "t4_espera_desatracacao_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "ta_atracado_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "te_estadia_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "berco_improdutivo_h"): ("numerico", 0, 24 * 365),
    ("fato_atracacao", "peso_bruto_t"): ("numerico", 0, 1_000_000),
    ("fato_atracacao", "teu"): ("numerico", 0, 30_000),
    ("fato_atracacao", "qtd_itens_carga"): ("numerico", 0, 50_000),
    ("fato_atracacao", "prancha_operacional_th"): ("numerico", 0, 20_000),
    ("fato_atracacao", "prancha_geral_th"): ("numerico", 0, 20_000),
    ("fato_atracacao", "nacionalidade_armador"): ("categorico", ["0", "1", "2"]),
    ("dim_instalacao", "sguf"): ("categorico", [
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
        "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
        "SE", "SP", "TO"]),
    ("dim_instalacao", "regiao_geografica"): ("categorico", [
        "Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]),
    ("dim_instalacao", "tipo_autoridade"): ("categorico", [
        "Porto Organizado", "Terminal Autorizado"]),
    ("dim_instalacao", "instalacao_em_rio"): ("categorico", ["Sim", "Não"]),
    ("dim_instalacao", "latitude"): ("numerico", -35.0, 6.0),
    ("dim_instalacao", "longitude"): ("numerico", -75.0, -28.0),
    ("dim_navegacao", "tipo_navegacao"): ("categorico", [
        "Interior", "Longo Curso", "Cabotagem", "Apoio Marítimo", "Apoio Portuário"]),
    ("dim_navegacao", "tipo_operacao"): ("categorico", [
        "Movimentação da Carga", "Apoio", "Passageiro", "Abastecimento",
        "Reparo/Manutenção", "Misto", "Marinha", "Retirada de Resíduos"]),
    ("dim_natureza_carga", "natureza_carga"): ("categorico", [
        "Carga Conteinerizada", "Carga Geral", "Granel Sólido",
        "Granel Líquido e Gasoso", "Sem carga declarada"]),
    ("dim_tempo", "ano"): ("numerico", 2025, 2025),
    ("dim_tempo", "mes"): ("numerico", 1, 12),
    ("dim_tempo", "trimestre"): ("numerico", 1, 4),
    ("dim_tempo", "semestre"): ("numerico", 1, 2),
    ("dim_tempo", "dia_semana"): ("numerico", 0, 6),
}


def resumo_dominio(s: pd.Series) -> str:
    s2 = s.dropna()
    if s2.empty:
        return "sem valores preenchidos"
    if pd.api.types.is_bool_dtype(s2):
        return f"verdadeiro em {int(s2.sum()):,} de {len(s2):,}"
    if pd.api.types.is_datetime64_any_dtype(s2):
        return f"{s2.min().date()} a {s2.max().date()}"
    if pd.api.types.is_numeric_dtype(s2):
        return (f"min {s2.min():,.2f} | p50 {s2.median():,.2f} | "
                f"max {s2.max():,.2f}")
    u = s2.unique()
    if len(u) <= 6:
        return "; ".join(sorted(map(str, u)))
    return f"{len(u):,} categorias distintas"


def violacoes_dominio(tabela: str, coluna: str, s: pd.Series) -> tuple[int, str]:
    """Conta valores fora do dominio declarado. Retorna (n, descricao)."""
    chave = (tabela, coluna)
    if chave not in DOMINIO_DECLARADO:
        return (0, "sem domínio declarado")
    decl = DOMINIO_DECLARADO[chave]
    s2 = s.dropna()
    if decl[0] == "numerico":
        _, lo, hi = decl
        n = int(((s2 < lo) | (s2 > hi)).sum())
        return (n, f"esperado entre {lo:,} e {hi:,}")
    _, categorias = decl
    n = int((~s2.astype(str).isin(categorias)).sum())
    desc = "; ".join(categorias) if len(categorias) <= 8 else f"{len(categorias)} categorias válidas"
    return (n, f"esperado em: {desc}")


# ==========================================================================
# 1. Analise por atributo
# ==========================================================================
def por_atributo(tabelas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    linhas = []
    for nome in TABELAS:
        df = tabelas[nome]
        pk = CHAVES_PRIMARIAS[nome]
        for c in df.columns:
            s = df[c]
            n_nulos = int(s.isna().sum())
            viol, regra = violacoes_dominio(nome, c, s)
            linhas.append({
                "tabela": nome,
                "atributo": c,
                "papel": ("chave primária" if c == pk
                          else "chave estrangeira" if c.startswith("sk_")
                          else "marcação de qualidade" if c.startswith("flag_")
                          else "medida" if pd.api.types.is_numeric_dtype(s) and nome == "fato_atracacao"
                          else "atributo descritivo"),
                "tipo": str(s.dtype),
                "preenchidos": int(s.notna().sum()),
                "nulos": n_nulos,
                "completude_pct": round(float(s.notna().mean() * 100), 2),
                "valores_distintos": int(s.nunique(dropna=True)),
                "dominio_observado": resumo_dominio(s),
                "regra_de_dominio": regra,
                "violacoes_de_dominio": viol,
                "situacao": ("conforme" if viol == 0 and n_nulos == 0
                             else "conforme com ausências" if viol == 0
                             else "violação de domínio"),
            })
    return pd.DataFrame(linhas)


# ==========================================================================
# 2. Analise por dimensao de qualidade
# ==========================================================================
def por_dimensao(tabelas: dict[str, pd.DataFrame], silver: pd.DataFrame,
                 atrib: pd.DataFrame) -> dict:
    fato = tabelas["fato_atracacao"]
    n = len(fato)
    r: dict = {"ano_referencia": int(pd.to_datetime(fato["sk_data"]).dt.year.mode()[0]),
               "linhas_fato": n,
               "atributos_auditados": int(len(atrib)),
               "tabelas_auditadas": len(TABELAS)}

    # --- completude ---
    r["completude"] = {
        "atributos_completos": int((atrib["completude_pct"] == 100).sum()),
        "atributos_com_ausencia": int((atrib["completude_pct"] < 100).sum()),
        "completude_media_pct": round(float(atrib["completude_pct"].mean()), 2),
        "piores_atributos": (atrib.nsmallest(6, "completude_pct")
                             [["tabela", "atributo", "completude_pct"]]
                             .to_dict(orient="records")),
    }

    # --- unicidade ---
    r["unicidade"] = {
        f"duplicatas_pk_{t}": int(tabelas[t][CHAVES_PRIMARIAS[t]].duplicated().sum())
        for t in TABELAS
    }
    r["unicidade"]["duplicatas_grao_fato"] = int(fato["sk_atracacao"].duplicated().sum())

    # --- consistencia: integridade referencial + cronologia ---
    orfas = {
        "fk_instalacao_orfa": int((~fato["sk_instalacao"].isin(tabelas["dim_instalacao"]["sk_instalacao"])).sum()),
        "fk_berco_orfa": int((~fato["sk_berco"].isin(tabelas["dim_berco"]["sk_berco"])).sum()),
        "fk_data_orfa": int((~fato["sk_data"].isin(tabelas["dim_tempo"]["sk_data"])).sum()),
        "fk_navegacao_orfa": int(fato["sk_navegacao"].isna().sum()),
        "fk_natureza_orfa": int(fato["sk_natureza"].isna().sum()),
        "fk_berco_para_instalacao_orfa": int(
            (~tabelas["dim_berco"]["sk_instalacao"].isin(tabelas["dim_instalacao"]["sk_instalacao"])).sum()),
    }
    quebras = {
        "atracacao_antes_da_chegada": int((silver["t1_espera_atracacao_h"] < 0).sum()),
        "inicio_op_antes_da_atracacao": int((silver["t2_espera_inicio_op_h"] < 0).sum()),
        "termino_op_antes_do_inicio": int((silver["t3_operacao_h"] < 0).sum()),
        "desatracacao_antes_do_termino": int((silver["t4_espera_desatracacao_h"] < 0).sum()),
        "desatracacao_antes_da_atracacao": int((silver["ta_atracado_h"] < 0).sum()),
    }
    # Coerencia aritmetica entre medidas derivadas
    d = silver.dropna(subset=["t2_espera_inicio_op_h", "t3_operacao_h", "t4_espera_desatracacao_h"])
    erro_ta = (d["t2_espera_inicio_op_h"] + d["t3_operacao_h"] + d["t4_espera_desatracacao_h"]
               - d["ta_atracado_h"]).abs()
    r["consistencia"] = {
        **orfas,
        "registros_com_cronologia_invalida": int(fato["flag_cronologia_invalida"].sum()),
        "quebras_por_etapa": quebras,
        "coerencia_T2_T3_T4_igual_TA": {
            "registros_testados": int(len(d)),
            "divergencias_acima_de_1_segundo": int((erro_ta > 1 / 3600).sum()),
            "erro_maximo_horas": round(float(erro_ta.max()), 6),
        },
    }

    # --- conformidade ---
    viol = atrib[atrib["violacoes_de_dominio"] > 0]
    r["conformidade"] = {
        "atributos_com_dominio_declarado": int((atrib["regra_de_dominio"] != "sem domínio declarado").sum()),
        "atributos_com_violacao": int(len(viol)),
        "total_de_violacoes": int(atrib["violacoes_de_dominio"].sum()),
        "detalhe_das_violacoes": viol[["tabela", "atributo", "violacoes_de_dominio",
                                       "regra_de_dominio"]].to_dict(orient="records"),
        "marcacoes_de_plausibilidade": {
            "estadia_acima_de_30_dias": int(fato["flag_estadia_outlier"].sum()),
            "prancha_acima_de_20000_th": int(fato["flag_prancha_implausivel"].sum()),
            "coordenada_fora_do_territorio": int(fato["flag_fora_bbox"].sum()),
        },
    }

    # --- acuracia: plausibilidade fisica da ocupacao de berco ---
    s = silver.dropna(subset=["Data Atracação", "Data Desatracação"]).copy()
    s = s[~s["flag_cronologia_invalida"]].sort_values(["IDBerco", "Data Atracação"])
    s["fim_anterior"] = s.groupby("IDBerco")["Data Desatracação"].shift(1)
    s["sobreposicao_h"] = (s["fim_anterior"] - s["Data Atracação"]).dt.total_seconds() / 3600.0
    sob = s[s["sobreposicao_h"] > 0]
    ev = pd.concat([
        pd.DataFrame({"b": s["IDBerco"], "t": s["Data Atracação"], "d": 1}),
        pd.DataFrame({"b": s["IDBerco"], "t": s["Data Desatracação"], "d": -1}),
    ]).sort_values(["b", "t", "d"], ascending=[True, True, False])
    ev["oc"] = ev.groupby("b")["d"].cumsum()
    pos = ev.groupby("b")["oc"].max().clip(lower=1)
    r["acuracia"] = {
        "teste": "dois navios nao podem ocupar a mesma posicao de atracacao simultaneamente",
        "atracacoes_avaliadas": int(len(s)),
        "atracacoes_com_sobreposicao_de_berco": int(len(sob)),
        "pct_sobreposicao": round(len(sob) / len(s) * 100, 2),
        "bercos_com_ao_menos_uma_sobreposicao": int(sob["IDBerco"].nunique()),
        "total_bercos": int(s["IDBerco"].nunique()),
        "mediana_horas_sobrepostas": round(float(sob["sobreposicao_h"].median()), 2),
        "p95_horas_sobrepostas": round(float(sob["sobreposicao_h"].quantile(0.95)), 2),
        "bercos_com_posicao_unica": int((pos <= 1).sum()),
        "pct_bercos_com_posicao_unica": round(float((pos <= 1).mean() * 100), 2),
        "ocupacao_simultanea_maxima": int(pos.max()),
        "interpretacao": ("A sobreposicao nao e erro de declaracao em massa: IDBerco "
                          "designa cais, area ou conjunto de posicoes, e nao uma posicao "
                          "exclusiva. A consequencia e que taxas de ocupacao calculadas "
                          "com uma posicao por berco seriam invalidas."),
        "atracacoes_sem_carga_declarada": int(fato["flag_sem_carga_declarada"].sum()),
        "pct_sem_carga_declarada": round(float(fato["flag_sem_carga_declarada"].mean() * 100), 2),
    }

    # --- atualidade ---
    ult = pd.to_datetime(fato["sk_data"]).max()
    r["atualidade"] = {
        "primeira_desatracacao": str(pd.to_datetime(fato["sk_data"]).min().date()),
        "ultima_desatracacao": str(ult.date()),
        "data_da_auditoria": str(date.today()),
        "defasagem_dias": int((pd.Timestamp(date.today()) - ult).days),
        "meses_cobertos": int(pd.to_datetime(fato["sk_data"]).dt.to_period("M").nunique()),
    }

    # --- aptidao para a decisao ---
    r["aptidao"] = {
        "aptas_analise_tempo": int(fato["flag_apto_analise_tempo"].sum()),
        "pct_aptas": round(float(fato["flag_apto_analise_tempo"].mean() * 100), 2),
        "sem_data_de_operacao": int(fato["flag_operacao_ausente"].sum()),
        "pct_sem_data_de_operacao": round(float(fato["flag_operacao_ausente"].mean() * 100), 2),
    }
    return r


def escrever_markdown(atrib: pd.DataFrame, dim: dict, destino: Path) -> None:
    L = ["# Relatório de qualidade de dados", "",
         f"Camada gold, ano {dim['ano_referencia']}. "
         f"**{dim['atributos_auditados']} atributos** auditados em "
         f"**{dim['tabelas_auditadas']} tabelas**.", "",
         "Este relatório tem duas partes. A primeira mede cada atributo individualmente, "
         "inclusive os que não apresentaram problema, porque o enunciado pede que se "
         "demonstre a ausência de problema e não apenas que se relatem os problemas "
         "encontrados. A segunda agrega o resultado nas seis dimensões clássicas de "
         "qualidade.", ""]

    L += ["## Parte 1: análise por atributo", ""]
    for t in TABELAS:
        sub = atrib[atrib["tabela"] == t]
        L += [f"### {t}", "",
              f"{len(sub)} atributos. "
              f"{int((sub['situacao'] == 'conforme').sum())} conformes sem ausências, "
              f"{int((sub['situacao'] == 'conforme com ausências').sum())} conformes com ausências, "
              f"{int((sub['situacao'] == 'violação de domínio').sum())} com violação de domínio.", "",
              "| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |",
              "|---|---|---|---|---|---|---|"]
        for _, r in sub.iterrows():
            L.append(f"| `{r.atributo}` | {r.papel} | {r.completude_pct:.2f}% | "
                     f"{r.valores_distintos:,} | {r.dominio_observado} | "
                     f"{r.regra_de_dominio} | {r.violacoes_de_dominio} |")
        L.append("")

    L += ["## Parte 2: análise por dimensão de qualidade", "",
          "```json", json.dumps(dim, ensure_ascii=False, indent=2), "```", ""]
    destino.write_text("\n".join(L), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()
    proj = Path(a.proj)
    g = proj / "dados" / "gold"

    tabelas = {t: pd.read_parquet(g / f"{t}_{a.ano}.parquet") for t in TABELAS}
    silver = pd.read_parquet(proj / "dados" / "silver" / f"atracacao_tratada_{a.ano}.parquet")

    atrib = por_atributo(tabelas)
    dim = por_dimensao(tabelas, silver, atrib)

    out = proj / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    atrib.to_csv(out / f"qualidade_por_atributo_{a.ano}.csv", index=False)
    with open(out / f"relatorio_qualidade_{a.ano}.json", "w", encoding="utf-8") as f:
        json.dump(dim, f, ensure_ascii=False, indent=2)
    escrever_markdown(atrib, dim, out / f"relatorio_qualidade_{a.ano}.md")

    print(f"atributos auditados: {len(atrib)} em {len(TABELAS)} tabelas")
    print(atrib.groupby("situacao").size().to_string())
    print()
    print(json.dumps({k: v for k, v in dim.items()
                      if k in ("completude", "unicidade", "conformidade")},
                     ensure_ascii=False, indent=2)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
