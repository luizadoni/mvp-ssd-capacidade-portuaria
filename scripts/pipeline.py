"""
MVP: Pipeline de dados para decisao sobre capacidade portuaria.
Camadas bronze -> silver -> gold, com modelagem em esquema estrela.

Uso:
    python3 -I pipeline.py --raw <dir_arquivos_brutos> --out <dir_projeto> --ano 2025

Fonte: ANTAQ, Estatistico Aquaviario (Sistema de Desempenho Portuario).
Grao da tabela fato: uma atracacao.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Parametros de negocio. Todo limiar usado no pipeline esta declarado aqui,
# para que a regra fique auditavel em vez de escondida no meio do codigo.
# --------------------------------------------------------------------------
PARAMS = {
    # Acima deste valor a estadia e tratada como outlier operacional e sai
    # das estatisticas de tendencia central (continua na base, marcada).
    "estadia_max_horas": 24 * 30,          # 30 dias
    # Operacao com duracao nula mas com carga declarada e inconsistente.
    "operacao_min_horas": 0.0,
    # Atracacoes de apoio/passageiro nao entram no calculo de produtividade.
    "tipos_operacao_produtiva": ["Movimentação da Carga", "Misto"],
    # Prancha considerada implausivel (t/h) para fins de conformidade.
    "prancha_max_th": 20000.0,
    # Caixa delimitadora aproximada do territorio brasileiro e aguas jurisdicionais.
    "bbox_brasil": {"lat_min": -35.0, "lat_max": 6.0, "lon_min": -75.0, "lon_max": -28.0},
}

COLS_DATA = [
    "Data Chegada",
    "Data Atracação",
    "Data Início Operação",
    "Data Término Operação",
    "Data Desatracação",
]

COLS_CARGA_USADAS = [
    "IDCarga", "IDAtracacao", "Natureza da Carga", "Sentido",
    "TEU", "QTCarga", "VLPesoCargaBruta",
    "FlagAutorizacao", "FlagMCOperacaoCarga",
]


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


# ==========================================================================
# BRONZE
# ==========================================================================
def bronze(raw_dir: Path, out_dir: Path, ano: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Copia fiel da origem, sem transformacao. So tipagem como texto.

    A camada bronze existe para garantir que qualquer numero do trabalho possa
    ser rastreado ate a linha original publicada pela ANTAQ.
    """
    log("BRONZE: lendo arquivos brutos")
    atr = pd.read_csv(
        raw_dir / f"{ano}Atracacao.txt", sep=";", encoding="utf-8-sig", dtype=str
    )
    carga = pd.read_csv(
        raw_dir / f"{ano}Carga.txt", sep=";", encoding="utf-8-sig", dtype=str,
        usecols=COLS_CARGA_USADAS,
    )
    log(f"BRONZE: atracacao {len(atr):,} linhas | carga {len(carga):,} linhas")

    bronze_dir = out_dir / "dados" / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    atr.to_parquet(bronze_dir / f"atracacao_{ano}.parquet", index=False)
    carga.to_parquet(bronze_dir / f"carga_{ano}.parquet", index=False)
    return atr, carga


# ==========================================================================
# SILVER
# ==========================================================================
def _para_datahora(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%d/%m/%Y %H:%M:%S", errors="coerce")


def _para_decimal(s: pd.Series) -> pd.Series:
    """ANTAQ publica decimal com virgula e milhar sem separador."""
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce",
    )


def silver(atr: pd.DataFrame, carga: pd.DataFrame, out_dir: Path, ano: int):
    """Tipagem, calculo dos tempos e reconciliacao atracacao x carga.

    Aqui ficam as regras de negocio explicitas:
      T1 espera para atracar     = Data Atracacao      - Data Chegada
      T2 espera inicio operacao  = Data Inicio Oper.   - Data Atracacao
      T3 operacao                = Data Termino Oper.  - Data Inicio Oper.
      T4 espera desatracacao     = Data Desatracacao   - Data Termino Oper.
      TA atracado                = T2 + T3 + T4
      TE estadia                 = T1 + TA
    Definicoes conforme Documentacao do Estatistico Aquaviario (ANTAQ, 2026).
    """
    log("SILVER: tipando atracacao")
    df = atr.copy()
    for c in COLS_DATA:
        df[c] = _para_datahora(df[c])

    # --- coordenadas -> lat/lon numericos -------------------------------
    coord = df["Coordenadas"].str.split(",", n=1, expand=True)
    df["longitude"] = pd.to_numeric(coord[0], errors="coerce")
    df["latitude"] = pd.to_numeric(coord[1], errors="coerce")

    # --- tempos (horas) --------------------------------------------------
    h = lambda a, b: (df[a] - df[b]).dt.total_seconds() / 3600.0
    df["t1_espera_atracacao_h"] = h("Data Atracação", "Data Chegada")
    df["t2_espera_inicio_op_h"] = h("Data Início Operação", "Data Atracação")
    df["t3_operacao_h"] = h("Data Término Operação", "Data Início Operação")
    df["t4_espera_desatracacao_h"] = h("Data Desatracação", "Data Término Operação")
    df["ta_atracado_h"] = h("Data Desatracação", "Data Atracação")
    df["te_estadia_h"] = h("Data Desatracação", "Data Chegada")

    # Tempo de berco ocupado sem operacao: capacidade consumida sem producao.
    # E a medida central da decisao deste MVP.
    df["berco_improdutivo_h"] = df["t2_espera_inicio_op_h"] + df["t4_espera_desatracacao_h"]

    # --- flags de validade (nao se descarta linha; marca-se) -------------
    df["flag_cronologia_invalida"] = (
        (df["t1_espera_atracacao_h"] < 0)
        | (df["t2_espera_inicio_op_h"] < 0)
        | (df["t3_operacao_h"] < 0)
        | (df["t4_espera_desatracacao_h"] < 0)
        | (df["ta_atracado_h"] < 0)
    ).fillna(False)

    df["flag_operacao_ausente"] = df["Data Início Operação"].isna() | df["Data Término Operação"].isna()
    df["flag_estadia_outlier"] = (df["te_estadia_h"] > PARAMS["estadia_max_horas"]).fillna(False)
    df["flag_fora_bbox"] = ~(
        df["latitude"].between(PARAMS["bbox_brasil"]["lat_min"], PARAMS["bbox_brasil"]["lat_max"])
        & df["longitude"].between(PARAMS["bbox_brasil"]["lon_min"], PARAMS["bbox_brasil"]["lon_max"])
    )

    # Registro apto a sustentar analise de tempo.
    df["flag_apto_analise_tempo"] = (
        ~df["flag_cronologia_invalida"]
        & ~df["flag_estadia_outlier"]
        & df["ta_atracado_h"].notna()
    )

    # ----------------------------------------------------------------
    # Reconciliacao com a tabela de carga.
    # Grao diferente: carga tem N linhas por atracacao. E preciso agregar
    # antes de juntar, senao a tabela fato duplicaria atracacoes.
    # ----------------------------------------------------------------
    log("SILVER: agregando carga ao grao de atracacao")
    cg = carga.copy()
    cg["VLPesoCargaBruta"] = _para_decimal(cg["VLPesoCargaBruta"])
    cg["TEU"] = _para_decimal(cg["TEU"])
    cg["QTCarga"] = _para_decimal(cg["QTCarga"])

    # Regra: so entram itens autorizados pelo SDP e marcados como movimentacao
    # de carga. Itens nao autorizados sao registros em revisao pela agencia.
    antes = len(cg)
    cg_val = cg[(cg["FlagAutorizacao"] == "S") & (cg["FlagMCOperacaoCarga"] == "1")].copy()
    log(f"SILVER: carga {antes:,} -> {len(cg_val):,} apos regra de autorizacao")

    agg = cg_val.groupby("IDAtracacao").agg(
        peso_bruto_t=("VLPesoCargaBruta", "sum"),
        teu=("TEU", "sum"),
        qtd_itens_carga=("IDCarga", "count"),
        qtd_naturezas=("Natureza da Carga", "nunique"),
    ).reset_index()

    # Natureza predominante por peso: define o perfil operacional da atracacao.
    nat = (
        cg_val.groupby(["IDAtracacao", "Natureza da Carga"])["VLPesoCargaBruta"]
        .sum().reset_index()
        .sort_values(["IDAtracacao", "VLPesoCargaBruta"], ascending=[True, False])
        .drop_duplicates("IDAtracacao")
        .rename(columns={"Natureza da Carga": "natureza_predominante"})
        [["IDAtracacao", "natureza_predominante"]]
    )
    agg = agg.merge(nat, on="IDAtracacao", how="left")

    # Atracacao exclusiva: movimentou um unico perfil de carga (definicao ANTAQ).
    agg["flag_atracacao_exclusiva"] = agg["qtd_naturezas"] == 1

    df = df.merge(agg, on="IDAtracacao", how="left")
    df["flag_sem_carga_declarada"] = df["peso_bruto_t"].isna()
    df["peso_bruto_t"] = df["peso_bruto_t"].fillna(0.0)
    df["teu"] = df["teu"].fillna(0.0)
    df["qtd_itens_carga"] = df["qtd_itens_carga"].fillna(0).astype(int)

    # --- produtividade ---------------------------------------------------
    # Prancha media operacional: toneladas movimentadas por hora de operacao.
    with np.errstate(divide="ignore", invalid="ignore"):
        df["prancha_operacional_th"] = np.where(
            (df["t3_operacao_h"] > 0) & (df["peso_bruto_t"] > 0),
            df["peso_bruto_t"] / df["t3_operacao_h"],
            np.nan,
        )
        df["prancha_geral_th"] = np.where(
            (df["ta_atracado_h"] > 0) & (df["peso_bruto_t"] > 0),
            df["peso_bruto_t"] / df["ta_atracado_h"],
            np.nan,
        )
    df["flag_prancha_implausivel"] = (df["prancha_operacional_th"] > PARAMS["prancha_max_th"]).fillna(False)

    silver_dir = out_dir / "dados" / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(silver_dir / f"atracacao_tratada_{ano}.parquet", index=False)
    log(f"SILVER: {len(df):,} atracacoes tratadas")
    return df, cg_val


# ==========================================================================
# GOLD: esquema estrela
# ==========================================================================
def gold(df: pd.DataFrame, out_dir: Path, ano: int) -> dict:
    log("GOLD: construindo esquema estrela")
    gold_dir = out_dir / "dados" / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)

    # --- dim_instalacao (grao: CDTUP) -----------------------------------
    dim_inst = (
        df.sort_values("Data Desatracação")
        .groupby("CDTUP")
        .agg(
            porto_atracacao=("Porto Atracação", "last"),
            complexo_portuario=("Complexo Portuário", "last"),
            apelido_instalacao=("Apelido Instalação Portuária", "last"),
            tipo_autoridade=("Tipo da Autoridade Portuária", "last"),
            municipio=("Município", "last"),
            uf=("UF", "last"),
            sguf=("SGUF", "last"),
            regiao_geografica=("Região Geográfica", "last"),
            regiao_hidrografica=("Região Hidrográfica", "last"),
            instalacao_em_rio=("Instalação Portuária em Rio", "last"),
            latitude=("latitude", "last"),
            longitude=("longitude", "last"),
        )
        .reset_index()
        .rename(columns={"CDTUP": "sk_instalacao"})
    )

    # --- dim_berco (grao: IDBerco) --------------------------------------
    dim_berco = (
        df.sort_values("Data Desatracação")
        .groupby("IDBerco")
        .agg(berco=("Berço", "last"), sk_instalacao=("CDTUP", "last"))
        .reset_index()
        .rename(columns={"IDBerco": "sk_berco"})
    )

    # --- dim_tempo (grao: data de desatracacao) -------------------------
    # Convencao ANTAQ: atributos temporais usam a data de desatracacao.
    datas = pd.to_datetime(df["Data Desatracação"].dt.date.dropna().unique())
    dim_tempo = pd.DataFrame({"sk_data": datas}).sort_values("sk_data")
    dim_tempo["ano"] = dim_tempo["sk_data"].dt.year
    dim_tempo["mes"] = dim_tempo["sk_data"].dt.month
    dim_tempo["nome_mes"] = dim_tempo["sk_data"].dt.strftime("%Y-%m")
    dim_tempo["trimestre"] = dim_tempo["sk_data"].dt.quarter
    dim_tempo["semestre"] = np.where(dim_tempo["mes"] <= 6, 1, 2)
    dim_tempo["dia_semana"] = dim_tempo["sk_data"].dt.dayofweek
    dim_tempo["fim_de_semana"] = dim_tempo["dia_semana"] >= 5

    # --- dim_navegacao (grao: combinacao tipo navegacao x tipo operacao) --
    dim_nav = (
        df[["Tipo de Navegação da Atracação", "Tipo de Operação"]]
        .drop_duplicates().dropna().reset_index(drop=True)
        .rename(columns={
            "Tipo de Navegação da Atracação": "tipo_navegacao",
            "Tipo de Operação": "tipo_operacao",
        })
    )
    dim_nav["sk_navegacao"] = dim_nav.index + 1
    dim_nav["operacao_produtiva"] = dim_nav["tipo_operacao"].isin(PARAMS["tipos_operacao_produtiva"])

    # --- dim_natureza_carga ---------------------------------------------
    naturezas = sorted(df["natureza_predominante"].dropna().unique().tolist()) + ["Sem carga declarada"]
    dim_nat = pd.DataFrame({"natureza_carga": naturezas})
    dim_nat["sk_natureza"] = dim_nat.index + 1
    dim_nat["granel"] = dim_nat["natureza_carga"].str.startswith("Granel")

    # --- fato_atracacao --------------------------------------------------
    fato = df.copy()
    fato["natureza_predominante"] = fato["natureza_predominante"].fillna("Sem carga declarada")
    fato = fato.merge(
        dim_nav, left_on=["Tipo de Navegação da Atracação", "Tipo de Operação"],
        right_on=["tipo_navegacao", "tipo_operacao"], how="left",
    ).merge(
        dim_nat, left_on="natureza_predominante", right_on="natureza_carga", how="left",
    )
    fato["sk_data"] = pd.to_datetime(fato["Data Desatracação"].dt.date)

    fato_cols = {
        "IDAtracacao": "sk_atracacao",
        "CDTUP": "sk_instalacao",
        "IDBerco": "sk_berco",
        "sk_data": "sk_data",
        "sk_navegacao": "sk_navegacao",
        "sk_natureza": "sk_natureza",
        "Nacionalidade do Armador": "nacionalidade_armador",
        "Nº do IMO": "numero_imo",
        "t1_espera_atracacao_h": "t1_espera_atracacao_h",
        "t2_espera_inicio_op_h": "t2_espera_inicio_op_h",
        "t3_operacao_h": "t3_operacao_h",
        "t4_espera_desatracacao_h": "t4_espera_desatracacao_h",
        "ta_atracado_h": "ta_atracado_h",
        "te_estadia_h": "te_estadia_h",
        "berco_improdutivo_h": "berco_improdutivo_h",
        "peso_bruto_t": "peso_bruto_t",
        "teu": "teu",
        "qtd_itens_carga": "qtd_itens_carga",
        "prancha_operacional_th": "prancha_operacional_th",
        "prancha_geral_th": "prancha_geral_th",
        "flag_cronologia_invalida": "flag_cronologia_invalida",
        "flag_operacao_ausente": "flag_operacao_ausente",
        "flag_estadia_outlier": "flag_estadia_outlier",
        "flag_sem_carga_declarada": "flag_sem_carga_declarada",
        "flag_atracacao_exclusiva": "flag_atracacao_exclusiva",
        "flag_prancha_implausivel": "flag_prancha_implausivel",
        "flag_fora_bbox": "flag_fora_bbox",
        "flag_apto_analise_tempo": "flag_apto_analise_tempo",
    }
    fato = fato[list(fato_cols.keys())].rename(columns=fato_cols)

    tabelas = {
        "dim_instalacao": dim_inst,
        "dim_berco": dim_berco,
        "dim_tempo": dim_tempo,
        "dim_navegacao": dim_nav[["sk_navegacao", "tipo_navegacao", "tipo_operacao", "operacao_produtiva"]],
        "dim_natureza_carga": dim_nat[["sk_natureza", "natureza_carga", "granel"]],
        "fato_atracacao": fato,
    }
    for nome, t in tabelas.items():
        t.to_parquet(gold_dir / f"{nome}_{ano}.parquet", index=False)
        log(f"GOLD: {nome:22s} {len(t):>8,} linhas")
    return tabelas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()

    raw_dir, out_dir = Path(a.raw), Path(a.out)
    atr, carga = bronze(raw_dir, out_dir, a.ano)
    df, cg = silver(atr, carga, out_dir, a.ano)
    gold(df, out_dir, a.ano)

    (out_dir / "outputs").mkdir(parents=True, exist_ok=True)
    with open(out_dir / "outputs" / f"parametros_{a.ano}.json", "w", encoding="utf-8") as f:
        json.dump(PARAMS, f, ensure_ascii=False, indent=2)
    log("concluido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
