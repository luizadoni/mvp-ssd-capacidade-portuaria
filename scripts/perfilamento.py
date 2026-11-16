"""Perfilamento inicial das tabelas brutas da ANTAQ.

Uso: python3 -I perfilamento.py <caminho_atracacao.txt> <caminho_carga.txt>
Nao faz parte do pipeline final: serve para conhecer o dado antes de modelar.
"""
import sys
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

atr_path, carga_path = sys.argv[1], sys.argv[2]

print("=" * 70)
print("ATRACACAO")
print("=" * 70)
atr = pd.read_csv(atr_path, sep=";", encoding="utf-8-sig", dtype=str)
print(f"linhas: {len(atr):,} | colunas: {len(atr.columns)}")
print("\nnulos por coluna (%):")
nulos = (atr.isna().mean() * 100).round(2).sort_values(ascending=False)
print(nulos.to_string())

print("\ncardinalidade:")
for c in ["IDAtracacao", "CDTUP", "IDBerco", "Complexo Portuário", "Porto Atracação",
          "Tipo da Autoridade Portuária", "Tipo de Operação",
          "Tipo de Navegação da Atracação", "SGUF", "Região Geográfica",
          "Nacionalidade do Armador", "FlagMCOperacaoAtracacao", "Mes"]:
    if c in atr.columns:
        print(f"  {c:40s} {atr[c].nunique():>8,}")

print("\nvalores de colunas categoricas chave:")
for c in ["Tipo da Autoridade Portuária", "Tipo de Operação",
          "Tipo de Navegação da Atracação", "FlagMCOperacaoAtracacao",
          "Instalação Portuária em Rio"]:
    if c in atr.columns:
        print(f"\n--- {c} ---")
        print(atr[c].value_counts(dropna=False).head(15).to_string())

print("\nduplicatas de IDAtracacao:", atr["IDAtracacao"].duplicated().sum())

print("\namostra de datas:")
print(atr[["Data Chegada", "Data Atracação", "Data Início Operação",
           "Data Término Operação", "Data Desatracação"]].head(5).to_string())

print("\n" + "=" * 70)
print("CARGA (amostra de 400 mil linhas)")
print("=" * 70)
carga = pd.read_csv(carga_path, sep=";", encoding="utf-8-sig", dtype=str, nrows=400_000)
print(f"colunas: {list(carga.columns)}")
print("\nnulos por coluna (%):")
print((carga.isna().mean() * 100).round(2).sort_values(ascending=False).to_string())
for c in ["Natureza da Carga", "Sentido", "Tipo Operação da Carga", "FlagAutorizacao",
          "FlagMCOperacaoCarga", "ConteinerEstado"]:
    if c in carga.columns:
        print(f"\n--- {c} ---")
        print(carga[c].value_counts(dropna=False).head(12).to_string())
print("\namostra VLPesoCargaBruta / QTCarga / TEU:")
print(carga[["VLPesoCargaBruta", "QTCarga", "TEU"]].head(8).to_string())
