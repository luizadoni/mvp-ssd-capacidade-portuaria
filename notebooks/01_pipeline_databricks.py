# Databricks notebook source
# MAGIC %md
# MAGIC # MVP: Capacidade portuária — pipeline bronze / silver / gold
# MAGIC
# MAGIC Persistência em nuvem no Databricks Free Edition, em Delta Lake gerenciado
# MAGIC pelo Unity Catalog.
# MAGIC
# MAGIC Este notebook é o equivalente funcional de `scripts/pipeline.py`, que roda em
# MAGIC pandas no ambiente local. As duas implementações aplicam as mesmas regras de
# MAGIC negócio, e a célula final compara as contagens das duas para comprovar
# MAGIC equivalência.
# MAGIC
# MAGIC **Antes de rodar:** suba `2025Atracacao.txt` e `2025Carga.txt` para um Volume
# MAGIC do Unity Catalog (Catalog > Create > Volume) e ajuste `CAMINHO_BRUTO` abaixo.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql import types as T

CATALOGO = "workspace"
ESQUEMA = "portos_mvp"
CAMINHO_BRUTO = "/Volumes/workspace/portos_mvp/brutos"
ANO = 2025

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{ESQUEMA}")
spark.sql(f"USE {CATALOGO}.{ESQUEMA}")
print(f"schema ativo: {CATALOGO}.{ESQUEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Camada bronze
# MAGIC Cópia fiel da origem, sem transformação. Todo campo entra como texto para
# MAGIC que nenhuma conversão silenciosa do leitor altere o dado original.

# COMMAND ----------

opcoes = {"sep": ";", "header": "true", "encoding": "UTF-8", "quote": '"', "multiLine": "false"}

atr_bronze = (spark.read.options(**opcoes).option("inferSchema", "false")
              .csv(f"{CAMINHO_BRUTO}/{ANO}Atracacao.txt"))

carga_bronze = (spark.read.options(**opcoes).option("inferSchema", "false")
                .csv(f"{CAMINHO_BRUTO}/{ANO}Carga.txt"))

# Normaliza nomes de coluna: Delta não aceita espaços nem acentos em alguns contextos.
def normaliza(df):
    import unicodedata, re
    novos = []
    for c in df.columns:
        n = unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode()
        n = re.sub(r"[^0-9a-zA-Z]+", "_", n).strip("_")
        novos.append(n)
    return df.toDF(*novos)

atr_bronze = normaliza(atr_bronze)
carga_bronze = normaliza(carga_bronze)

# overwriteSchema permite reexecutar o notebook depois de uma mudanca no
# conjunto de colunas. Sem ele, o Delta recusa a sobrescrita com
# DELTA_METADATA_MISMATCH para proteger a tabela existente.
(atr_bronze.write.mode("overwrite").format("delta").option("overwriteSchema", "true").saveAsTable("bronze_atracacao"))
(carga_bronze.write.mode("overwrite").format("delta").option("overwriteSchema", "true").saveAsTable("bronze_carga"))

print(f"bronze_atracacao: {atr_bronze.count():,} linhas, {len(atr_bronze.columns)} colunas")
print(f"bronze_carga....: {carga_bronze.count():,} linhas, {len(carga_bronze.columns)} colunas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Camada silver
# MAGIC Tipagem, cálculo dos tempos T1 a T4 e marcação de qualidade.
# MAGIC
# MAGIC Definições conforme a Documentação do Estatístico Aquaviário (ANTAQ):
# MAGIC
# MAGIC | tempo | definição |
# MAGIC |---|---|
# MAGIC | T1 | da chegada à área de fundeio até a atracação |
# MAGIC | T2 | da atracação até o início da operação |
# MAGIC | T3 | do início ao término da operação |
# MAGIC | T4 | do término da operação até a desatracação |
# MAGIC | TA | T2 + T3 + T4 (tempo atracado) |
# MAGIC | TE | T1 + TA (estadia) |

# COMMAND ----------

FMT = "dd/MM/yyyy HH:mm:ss"
ESTADIA_MAX_H = 24 * 30
PRANCHA_MAX = 20000.0

def horas(fim, ini):
    return (F.col(fim).cast("long") - F.col(ini).cast("long")) / 3600.0

s = atr_bronze
for c in ["Data_Chegada", "Data_Atracacao", "Data_Inicio_Operacao",
          "Data_Termino_Operacao", "Data_Desatracacao"]:
    s = s.withColumn(c, F.to_timestamp(F.col(c), FMT))

s = (s
     .withColumn("t1_espera_atracacao_h", horas("Data_Atracacao", "Data_Chegada"))
     .withColumn("t2_espera_inicio_op_h", horas("Data_Inicio_Operacao", "Data_Atracacao"))
     .withColumn("t3_operacao_h", horas("Data_Termino_Operacao", "Data_Inicio_Operacao"))
     .withColumn("t4_espera_desatracacao_h", horas("Data_Desatracacao", "Data_Termino_Operacao"))
     .withColumn("ta_atracado_h", horas("Data_Desatracacao", "Data_Atracacao"))
     .withColumn("te_estadia_h", horas("Data_Desatracacao", "Data_Chegada"))
     .withColumn("berco_improdutivo_h",
                 F.col("t2_espera_inicio_op_h") + F.col("t4_espera_desatracacao_h"))
     .withColumn("longitude", F.split("Coordenadas", ",").getItem(0).cast("double"))
     .withColumn("latitude", F.split("Coordenadas", ",").getItem(1).cast("double"))
     )

s = (s
     .withColumn("flag_cronologia_invalida",
                 F.coalesce((F.col("t1_espera_atracacao_h") < 0)
                            | (F.col("t2_espera_inicio_op_h") < 0)
                            | (F.col("t3_operacao_h") < 0)
                            | (F.col("t4_espera_desatracacao_h") < 0)
                            | (F.col("ta_atracado_h") < 0), F.lit(False)))
     .withColumn("flag_operacao_ausente",
                 F.col("Data_Inicio_Operacao").isNull() | F.col("Data_Termino_Operacao").isNull())
     .withColumn("flag_estadia_outlier",
                 F.coalesce(F.col("te_estadia_h") > ESTADIA_MAX_H, F.lit(False)))
     )

# COMMAND ----------

# MAGIC %md
# MAGIC ### Conciliação de grãos
# MAGIC `Carga` tem N itens por atracação. É preciso **agregar antes de juntar**,
# MAGIC caso contrário a tabela fato duplicaria atracações e toda soma de tempo
# MAGIC seria multiplicada pelo número de itens de carga.

# COMMAND ----------

def decimal_br(c):
    return F.regexp_replace(F.regexp_replace(F.col(c), r"\.", ""), ",", r".").cast("double")

cg = (carga_bronze
      .withColumn("peso", decimal_br("VLPesoCargaBruta"))
      .withColumn("teu_n", decimal_br("TEU"))
      .filter((F.col("FlagAutorizacao") == "S") & (F.col("FlagMCOperacaoCarga") == "1")))

print(f"carga: {carga_bronze.count():,} itens -> {cg.count():,} após regra de autorização")

agg = (cg.groupBy("IDAtracacao")
       .agg(F.sum("peso").alias("peso_bruto_t"),
            F.sum("teu_n").alias("teu"),
            F.count("IDCarga").alias("qtd_itens_carga"),
            F.countDistinct("Natureza_da_Carga").alias("qtd_naturezas")))

janela_nat = (cg.groupBy("IDAtracacao", "Natureza_da_Carga")
              .agg(F.sum("peso").alias("p")))
from pyspark.sql.window import Window
w = Window.partitionBy("IDAtracacao").orderBy(F.col("p").desc())
nat = (janela_nat.withColumn("r", F.row_number().over(w)).filter(F.col("r") == 1)
       .select("IDAtracacao", F.col("Natureza_da_Carga").alias("natureza_predominante")))

agg = agg.join(nat, "IDAtracacao", "left").withColumn(
    "flag_atracacao_exclusiva", F.col("qtd_naturezas") == 1)

silver = (s.join(agg, "IDAtracacao", "left")
          .withColumn("flag_sem_carga_declarada", F.col("peso_bruto_t").isNull())
          .fillna({"peso_bruto_t": 0.0, "teu": 0.0, "qtd_itens_carga": 0}))

silver = (silver
          .withColumn("prancha_operacional_th",
                      F.when((F.col("t3_operacao_h") > 0) & (F.col("peso_bruto_t") > 0),
                             F.col("peso_bruto_t") / F.col("t3_operacao_h")))
          .withColumn("prancha_geral_th",
                      F.when((F.col("ta_atracado_h") > 0) & (F.col("peso_bruto_t") > 0),
                             F.col("peso_bruto_t") / F.col("ta_atracado_h")))
          .withColumn("flag_prancha_implausivel",
                      F.coalesce(F.col("prancha_operacional_th") > PRANCHA_MAX, F.lit(False)))
          .withColumn("flag_fora_bbox",
                      ~(F.col("latitude").between(-35.0, 6.0)
                        & F.col("longitude").between(-75.0, -28.0)))
          .withColumn("flag_apto_analise_tempo",
                      (~F.col("flag_cronologia_invalida")) & (~F.col("flag_estadia_outlier"))
                      & F.col("ta_atracado_h").isNotNull()))

silver.write.mode("overwrite").format("delta").option("overwriteSchema", "true").saveAsTable("silver_atracacao")
print(f"silver_atracacao: {silver.count():,} linhas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Camada gold: esquema estrela

# COMMAND ----------

sv = spark.table("silver_atracacao")

dim_instalacao = (sv.groupBy(F.col("CDTUP").alias("sk_instalacao"))
                  .agg(F.max("Porto_Atracacao").alias("porto_atracacao"),
                       F.max("Complexo_Portuario").alias("complexo_portuario"),
                       F.max("Tipo_da_Autoridade_Portuaria").alias("tipo_autoridade"),
                       F.max("Municipio").alias("municipio"),
                       F.max("UF").alias("uf"),
                       F.max("SGUF").alias("sguf"),
                       F.max("Regiao_Geografica").alias("regiao_geografica"),
                       F.max("Instalacao_Portuaria_em_Rio").alias("instalacao_em_rio"),
                       F.max("latitude").alias("latitude"),
                       F.max("longitude").alias("longitude")))

dim_berco = (sv.groupBy(F.col("IDBerco").alias("sk_berco"))
             .agg(F.max("Berco").alias("berco"),
                  F.max("CDTUP").alias("sk_instalacao")))

dim_tempo = (sv.select(F.to_date("Data_Desatracacao").alias("sk_data")).distinct()
             .filter(F.col("sk_data").isNotNull())
             .withColumn("ano", F.year("sk_data"))
             .withColumn("mes", F.month("sk_data"))
             .withColumn("nome_mes", F.date_format("sk_data", "yyyy-MM"))
             .withColumn("trimestre", F.quarter("sk_data"))
             .withColumn("semestre", F.when(F.month("sk_data") <= 6, 1).otherwise(2))
             # dayofweek do Spark devolve 1 para domingo. Converte-se para a
             # convencao usada na implementacao local (0 = segunda-feira).
             .withColumn("dia_semana", (F.dayofweek("sk_data") + 5) % 7)
             .withColumn("fim_de_semana", ((F.dayofweek("sk_data") + 5) % 7) >= 5))

# ATENCAO: a chave sintetica precisa ser DETERMINISTICA.
# monotonically_increasing_id() nao e: o Spark avalia de forma preguicosa e
# recalcula a coluna a cada acao, de modo que a chave gravada na dimensao
# pode nao ser a mesma gravada na fato. O resultado e uma juncao que nao
# encontra correspondencia. row_number() sobre uma ordenacao fixa resolve,
# e as dimensoes sao gravadas e relidas do Delta antes de montar a fato.
from pyspark.sql.window import Window as W

dim_navegacao = (sv.select(
    F.col("Tipo_de_Navegacao_da_Atracacao").alias("tipo_navegacao"),
    F.col("Tipo_de_Operacao").alias("tipo_operacao")).distinct().dropna()
    .withColumn("sk_navegacao",
                F.row_number().over(W.orderBy("tipo_navegacao", "tipo_operacao")))
    .withColumn("operacao_produtiva",
                F.col("tipo_operacao").isin(["Movimentação da Carga", "Misto"])))

dim_natureza = (sv.select(F.coalesce("natureza_predominante",
                                     F.lit("Sem carga declarada")).alias("natureza_carga"))
                .distinct()
                .withColumn("sk_natureza",
                            F.row_number().over(W.orderBy("natureza_carga")))
                .withColumn("granel", F.col("natureza_carga").startswith("Granel")))

# Grava as dimensoes ANTES de montar a fato.
for nome, df in [("dim_instalacao", dim_instalacao), ("dim_berco", dim_berco),
                 ("dim_tempo", dim_tempo), ("dim_navegacao", dim_navegacao),
                 ("dim_natureza_carga", dim_natureza)]:
    df.write.mode("overwrite").format("delta").option("overwriteSchema", "true").saveAsTable(nome)
    print(f"{nome:22s} {spark.table(nome).count():>8,} linhas")

# Rele do Delta: garante que a chave usada na fato e exatamente a persistida.
d_nav = spark.table("dim_navegacao")
d_nat = spark.table("dim_natureza_carga")

# Os nomes destas duas colunas dependem da normalizacao de acentos, entao
# sao localizados pelo conteudo em vez de escritos a mao.
col_nac = [c for c in sv.columns if c.lower().startswith("nacionalidade")][0]
col_imo = [c for c in sv.columns if c.upper().endswith("IMO")][0]

fato = (sv
        .withColumn("natureza_carga", F.coalesce("natureza_predominante",
                                                 F.lit("Sem carga declarada")))
        .join(d_nav,
              (F.col("Tipo_de_Navegacao_da_Atracacao") == d_nav["tipo_navegacao"])
              & (F.col("Tipo_de_Operacao") == d_nav["tipo_operacao"]), "left")
        .join(d_nat, "natureza_carga", "left")
        .select(F.col("IDAtracacao").alias("sk_atracacao"),
                F.col("CDTUP").alias("sk_instalacao"),
                F.col("IDBerco").alias("sk_berco"),
                F.to_date("Data_Desatracacao").alias("sk_data"),
                "sk_navegacao", "sk_natureza",
                F.col(col_nac).alias("nacionalidade_armador"),
                F.col(col_imo).alias("numero_imo"),
                "t1_espera_atracacao_h", "t2_espera_inicio_op_h", "t3_operacao_h",
                "t4_espera_desatracacao_h", "ta_atracado_h", "te_estadia_h",
                "berco_improdutivo_h", "peso_bruto_t", "teu", "qtd_itens_carga",
                "prancha_operacional_th", "prancha_geral_th",
                "flag_cronologia_invalida", "flag_operacao_ausente",
                "flag_estadia_outlier", "flag_sem_carga_declarada",
                "flag_atracacao_exclusiva", "flag_prancha_implausivel",
                "flag_fora_bbox", "flag_apto_analise_tempo"))

fato.write.mode("overwrite").format("delta").option("overwriteSchema", "true").saveAsTable("fato_atracacao")
print(f"{'fato_atracacao':22s} {spark.table('fato_atracacao').count():>8,} linhas")

# Teste de integridade referencial: nenhuma linha da fato pode ficar sem
# correspondencia nas dimensoes. Se este numero nao for zero, a juncao falhou.
orfas = spark.table("fato_atracacao").filter(
    F.col("sk_navegacao").isNull() | F.col("sk_natureza").isNull()).count()
print(f"\nlinhas da fato sem chave de dimensao: {orfas:,}  "
      f"{'(OK)' if orfas == 0 else '(FALHA: a juncao nao casou)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prova de persistência em nuvem
# MAGIC As tabelas abaixo existem no Unity Catalog após o fim da execução do
# MAGIC cluster. Capturar esta saída e a aba Catalog como evidência.

# COMMAND ----------

display(spark.sql(f"SHOW TABLES IN {CATALOGO}.{ESQUEMA}"))

# COMMAND ----------

display(spark.sql("DESCRIBE DETAIL fato_atracacao"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificação de equivalência com a implementação local
# MAGIC
# MAGIC Os números abaixo devem bater com os de `outputs/relatorio_qualidade_2025.json`.
# MAGIC Valores esperados:
# MAGIC
# MAGIC ```
# MAGIC atracacoes          116.327
# MAGIC aptas               115.071
# MAGIC sem_data_operacao     6.695
# MAGIC estadia_outlier       1.250
# MAGIC sem_carga            22.145
# MAGIC peso_milhoes_t     1.403,90
# MAGIC ```
# MAGIC
# MAGIC A tabela fato tem **28 atributos**, os mesmos documentados em
# MAGIC `catalogo/catalogo_dados.md`.

# COMMAND ----------

display(spark.sql("""
SELECT
  COUNT(*)                                            AS atracacoes,
  SUM(CASE WHEN flag_apto_analise_tempo THEN 1 ELSE 0 END) AS aptas,
  SUM(CASE WHEN flag_operacao_ausente   THEN 1 ELSE 0 END) AS sem_data_operacao,
  SUM(CASE WHEN flag_estadia_outlier    THEN 1 ELSE 0 END) AS estadia_outlier,
  SUM(CASE WHEN flag_sem_carga_declarada THEN 1 ELSE 0 END) AS sem_carga,
  ROUND(SUM(peso_bruto_t)/1e6, 2)                     AS peso_milhoes_t
FROM fato_atracacao
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resposta à pergunta de negócio, direto em SQL
# MAGIC
# MAGIC Esta consulta deve devolver **15 linhas**. Se devolver menos de dez, a
# MAGIC junção entre a fato e `dim_navegacao` não casou, e o teste de integridade
# MAGIC referencial da célula da camada gold terá acusado linhas órfãs.

# COMMAND ----------

display(spark.sql("""
WITH base AS (
  SELECT f.*, i.porto_atracacao, i.complexo_portuario, i.sguf,
         n.tipo_navegacao, n.operacao_produtiva
  FROM fato_atracacao f
  JOIN dim_instalacao i ON f.sk_instalacao = i.sk_instalacao
  JOIN dim_navegacao  n ON f.sk_navegacao  = n.sk_navegacao
  WHERE f.flag_apto_analise_tempo
    AND n.tipo_navegacao IN ('Longo Curso', 'Cabotagem')
    AND n.operacao_produtiva
    AND f.t3_operacao_h IS NOT NULL
)
SELECT porto_atracacao, sguf,
       COUNT(*)                                        AS atracacoes,
       ROUND(SUM(berco_improdutivo_h), 0)              AS berco_improdutivo_h,
       ROUND(100.0*SUM(berco_improdutivo_h)/SUM(ta_atracado_h), 1) AS pct_improdutivo,
       ROUND(SUM(berco_improdutivo_h)/8760, 2)         AS posicoes_equivalentes
FROM base
GROUP BY porto_atracacao, sguf
HAVING COUNT(*) >= 50
ORDER BY berco_improdutivo_h DESC
LIMIT 15
"""))
