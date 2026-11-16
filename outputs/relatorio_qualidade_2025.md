# Relatório de qualidade de dados

Camada gold, ano 2025. **59 atributos** auditados em **6 tabelas**.

Este relatório tem duas partes. A primeira mede cada atributo individualmente, inclusive os que não apresentaram problema, porque o enunciado pede que se demonstre a ausência de problema e não apenas que se relatem os problemas encontrados. A segunda agrega o resultado nas seis dimensões clássicas de qualidade.

## Parte 1: análise por atributo

### fato_atracacao

28 atributos. 14 conformes sem ausências, 6 conformes com ausências, 8 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_atracacao` | chave primária | 100.00% | 116,327 | 116,327 categorias distintas | sem domínio declarado | 0 |
| `sk_instalacao` | chave estrangeira | 100.00% | 212 | 212 categorias distintas | sem domínio declarado | 0 |
| `sk_berco` | chave estrangeira | 99.99% | 625 | 625 categorias distintas | sem domínio declarado | 0 |
| `sk_data` | chave estrangeira | 100.00% | 365 | 2025-01-01 a 2025-12-31 | sem domínio declarado | 0 |
| `sk_navegacao` | chave estrangeira | 99.99% | 35 | min 1.00 | p50 12.00 | max 35.00 | sem domínio declarado | 0 |
| `sk_natureza` | chave estrangeira | 100.00% | 5 | min 1.00 | p50 4.00 | max 5.00 | sem domínio declarado | 0 |
| `nacionalidade_armador` | atributo descritivo | 99.99% | 3 | 0; 1; 2 | esperado em: 0; 1; 2 | 0 |
| `numero_imo` | atributo descritivo | 51.49% | 7,532 | 7,532 categorias distintas | sem domínio declarado | 0 |
| `t1_espera_atracacao_h` | medida | 99.99% | 13,868 | min 0.00 | p50 1.00 | max 175,404.40 | esperado entre 0 e 8,760 | 144 |
| `t2_espera_inicio_op_h` | medida | 94.25% | 3,128 | min 0.00 | p50 0.38 | max 175,320.50 | esperado entre 0 e 8,760 | 3 |
| `t3_operacao_h` | medida | 94.24% | 8,134 | min 0.00 | p50 7.08 | max 87,730.20 | esperado entre 0 e 8,760 | 1 |
| `t4_espera_desatracacao_h` | medida | 94.25% | 2,826 | min 0.00 | p50 0.92 | max 7,297.00 | esperado entre 0 e 8,760 | 0 |
| `ta_atracado_h` | medida | 99.99% | 9,552 | min 0.02 | p50 11.13 | max 175,324.00 | esperado entre 0 e 8,760 | 8 |
| `te_estadia_h` | medida | 99.99% | 17,558 | min 0.03 | p50 20.57 | max 175,474.43 | esperado entre 0 e 8,760 | 153 |
| `berco_improdutivo_h` | medida | 94.24% | 5,786 | min 0.00 | p50 1.77 | max 175,321.00 | esperado entre 0 e 8,760 | 3 |
| `peso_bruto_t` | medida | 100.00% | 72,340 | min 0.00 | p50 1,806.89 | max 419,507.66 | esperado entre 0 e 1,000,000 | 0 |
| `teu` | medida | 100.00% | 3,731 | min 0.00 | p50 0.00 | max 14,145.00 | esperado entre 0 e 30,000 | 0 |
| `qtd_itens_carga` | medida | 100.00% | 1,198 | min 0.00 | p50 1.00 | max 7,292.00 | esperado entre 0 e 50,000 | 0 |
| `prancha_operacional_th` | medida | 80.96% | 91,160 | min 0.00 | p50 416.86 | max 2,705,674.00 | esperado entre 0 e 20,000 | 73 |
| `prancha_geral_th` | medida | 80.96% | 91,165 | min 0.00 | p50 265.86 | max 100,022.91 | esperado entre 0 e 20,000 | 5 |
| `flag_cronologia_invalida` | marcação de qualidade | 100.00% | 1 | verdadeiro em 0 de 116,327 | sem domínio declarado | 0 |
| `flag_operacao_ausente` | marcação de qualidade | 100.00% | 2 | verdadeiro em 6,695 de 116,327 | sem domínio declarado | 0 |
| `flag_estadia_outlier` | marcação de qualidade | 100.00% | 2 | verdadeiro em 1,250 de 116,327 | sem domínio declarado | 0 |
| `flag_sem_carga_declarada` | marcação de qualidade | 100.00% | 2 | verdadeiro em 22,145 de 116,327 | sem domínio declarado | 0 |
| `flag_atracacao_exclusiva` | marcação de qualidade | 80.96% | 2 | False; True | sem domínio declarado | 0 |
| `flag_prancha_implausivel` | marcação de qualidade | 100.00% | 2 | verdadeiro em 73 de 116,327 | sem domínio declarado | 0 |
| `flag_fora_bbox` | marcação de qualidade | 100.00% | 2 | verdadeiro em 6 de 116,327 | sem domínio declarado | 0 |
| `flag_apto_analise_tempo` | marcação de qualidade | 100.00% | 2 | verdadeiro em 115,071 de 116,327 | sem domínio declarado | 0 |

### dim_instalacao

13 atributos. 4 conformes sem ausências, 9 conformes com ausências, 0 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_instalacao` | chave primária | 100.00% | 212 | 212 categorias distintas | sem domínio declarado | 0 |
| `porto_atracacao` | atributo descritivo | 99.53% | 211 | 211 categorias distintas | sem domínio declarado | 0 |
| `complexo_portuario` | atributo descritivo | 100.00% | 42 | 42 categorias distintas | sem domínio declarado | 0 |
| `apelido_instalacao` | atributo descritivo | 32.08% | 68 | 68 categorias distintas | sem domínio declarado | 0 |
| `tipo_autoridade` | atributo descritivo | 100.00% | 2 | Porto Organizado; Terminal Autorizado | esperado em: Porto Organizado; Terminal Autorizado | 0 |
| `municipio` | atributo descritivo | 99.53% | 78 | 78 categorias distintas | sem domínio declarado | 0 |
| `uf` | atributo descritivo | 99.53% | 20 | 20 categorias distintas | sem domínio declarado | 0 |
| `sguf` | atributo descritivo | 99.53% | 20 | 20 categorias distintas | esperado em: 27 categorias válidas | 0 |
| `regiao_geografica` | atributo descritivo | 99.53% | 5 | Centro-Oeste; Nordeste; Norte; Sudeste; Sul | esperado em: Norte; Nordeste; Sudeste; Sul; Centro-Oeste | 0 |
| `regiao_hidrografica` | atributo descritivo | 47.64% | 5 |   Paraguai;   Paraná;   Tocantins-Araguaia;  Amazônica;  Atlântico Sul | sem domínio declarado | 0 |
| `instalacao_em_rio` | atributo descritivo | 100.00% | 2 | Não; Sim | esperado em: Sim; Não | 0 |
| `latitude` | atributo descritivo | 99.53% | 204 | min -32.10 | p50 -12.81 | max -0.06 | esperado entre -35.0 e 6.0 | 0 |
| `longitude` | atributo descritivo | 99.53% | 206 | min -63.92 | p50 -48.65 | max -34.84 | esperado entre -75.0 e -28.0 | 0 |

### dim_berco

3 atributos. 3 conformes sem ausências, 0 conformes com ausências, 0 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_berco` | chave primária | 100.00% | 625 | 625 categorias distintas | sem domínio declarado | 0 |
| `berco` | atributo descritivo | 100.00% | 501 | 501 categorias distintas | sem domínio declarado | 0 |
| `sk_instalacao` | chave estrangeira | 100.00% | 211 | 211 categorias distintas | sem domínio declarado | 0 |

### dim_tempo

8 atributos. 8 conformes sem ausências, 0 conformes com ausências, 0 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_data` | chave primária | 100.00% | 365 | 2025-01-01 a 2025-12-31 | sem domínio declarado | 0 |
| `ano` | atributo descritivo | 100.00% | 1 | min 2,025.00 | p50 2,025.00 | max 2,025.00 | esperado entre 2,025 e 2,025 | 0 |
| `mes` | atributo descritivo | 100.00% | 12 | min 1.00 | p50 7.00 | max 12.00 | esperado entre 1 e 12 | 0 |
| `nome_mes` | atributo descritivo | 100.00% | 12 | 12 categorias distintas | sem domínio declarado | 0 |
| `trimestre` | atributo descritivo | 100.00% | 4 | min 1.00 | p50 3.00 | max 4.00 | esperado entre 1 e 4 | 0 |
| `semestre` | atributo descritivo | 100.00% | 2 | min 1.00 | p50 2.00 | max 2.00 | esperado entre 1 e 2 | 0 |
| `dia_semana` | atributo descritivo | 100.00% | 7 | min 0.00 | p50 3.00 | max 6.00 | esperado entre 0 e 6 | 0 |
| `fim_de_semana` | atributo descritivo | 100.00% | 2 | verdadeiro em 104 de 365 | sem domínio declarado | 0 |

### dim_navegacao

4 atributos. 4 conformes sem ausências, 0 conformes com ausências, 0 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_navegacao` | chave primária | 100.00% | 35 | min 1.00 | p50 18.00 | max 35.00 | sem domínio declarado | 0 |
| `tipo_navegacao` | atributo descritivo | 100.00% | 5 | Apoio Marítimo; Apoio Portuário; Cabotagem; Interior; Longo Curso | esperado em: Interior; Longo Curso; Cabotagem; Apoio Marítimo; Apoio Portuário | 0 |
| `tipo_operacao` | atributo descritivo | 100.00% | 8 | 8 categorias distintas | esperado em: Movimentação da Carga; Apoio; Passageiro; Abastecimento; Reparo/Manutenção; Misto; Marinha; Retirada de Resíduos | 0 |
| `operacao_produtiva` | atributo descritivo | 100.00% | 2 | verdadeiro em 6 de 35 | sem domínio declarado | 0 |

### dim_natureza_carga

3 atributos. 3 conformes sem ausências, 0 conformes com ausências, 0 com violação de domínio.

| Atributo | Papel | Completude | Distintos | Domínio observado | Regra declarada | Violações |
|---|---|---|---|---|---|---|
| `sk_natureza` | chave primária | 100.00% | 5 | min 1.00 | p50 3.00 | max 5.00 | sem domínio declarado | 0 |
| `natureza_carga` | atributo descritivo | 100.00% | 5 | Carga Conteinerizada; Carga Geral; Granel Líquido e Gasoso; Granel Sólido; Sem carga declarada | esperado em: Carga Conteinerizada; Carga Geral; Granel Sólido; Granel Líquido e Gasoso; Sem carga declarada | 0 |
| `granel` | atributo descritivo | 100.00% | 2 | verdadeiro em 2 de 5 | sem domínio declarado | 0 |

## Parte 2: análise por dimensão de qualidade

```json
{
  "ano_referencia": 2025,
  "linhas_fato": 116327,
  "atributos_auditados": 59,
  "tabelas_auditadas": 6,
  "completude": {
    "atributos_completos": 36,
    "atributos_com_ausencia": 23,
    "completude_media_pct": 95.72,
    "piores_atributos": [
      {
        "tabela": "dim_instalacao",
        "atributo": "apelido_instalacao",
        "completude_pct": 32.08
      },
      {
        "tabela": "dim_instalacao",
        "atributo": "regiao_hidrografica",
        "completude_pct": 47.64
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "numero_imo",
        "completude_pct": 51.49
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "prancha_operacional_th",
        "completude_pct": 80.96
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "prancha_geral_th",
        "completude_pct": 80.96
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "flag_atracacao_exclusiva",
        "completude_pct": 80.96
      }
    ]
  },
  "unicidade": {
    "duplicatas_pk_fato_atracacao": 0,
    "duplicatas_pk_dim_instalacao": 0,
    "duplicatas_pk_dim_berco": 0,
    "duplicatas_pk_dim_tempo": 0,
    "duplicatas_pk_dim_navegacao": 0,
    "duplicatas_pk_dim_natureza_carga": 0,
    "duplicatas_grao_fato": 0
  },
  "consistencia": {
    "fk_instalacao_orfa": 0,
    "fk_berco_orfa": 6,
    "fk_data_orfa": 0,
    "fk_navegacao_orfa": 6,
    "fk_natureza_orfa": 0,
    "fk_berco_para_instalacao_orfa": 0,
    "registros_com_cronologia_invalida": 0,
    "quebras_por_etapa": {
      "atracacao_antes_da_chegada": 0,
      "inicio_op_antes_da_atracacao": 0,
      "termino_op_antes_do_inicio": 0,
      "desatracacao_antes_do_termino": 0,
      "desatracacao_antes_da_atracacao": 0
    },
    "coerencia_T2_T3_T4_igual_TA": {
      "registros_testados": 109632,
      "divergencias_acima_de_1_segundo": 0,
      "erro_maximo_horas": 0.0
    }
  },
  "conformidade": {
    "atributos_com_dominio_declarado": 27,
    "atributos_com_violacao": 8,
    "total_de_violacoes": 390,
    "detalhe_das_violacoes": [
      {
        "tabela": "fato_atracacao",
        "atributo": "t1_espera_atracacao_h",
        "violacoes_de_dominio": 144,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "t2_espera_inicio_op_h",
        "violacoes_de_dominio": 3,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "t3_operacao_h",
        "violacoes_de_dominio": 1,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "ta_atracado_h",
        "violacoes_de_dominio": 8,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "te_estadia_h",
        "violacoes_de_dominio": 153,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "berco_improdutivo_h",
        "violacoes_de_dominio": 3,
        "regra_de_dominio": "esperado entre 0 e 8,760"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "prancha_operacional_th",
        "violacoes_de_dominio": 73,
        "regra_de_dominio": "esperado entre 0 e 20,000"
      },
      {
        "tabela": "fato_atracacao",
        "atributo": "prancha_geral_th",
        "violacoes_de_dominio": 5,
        "regra_de_dominio": "esperado entre 0 e 20,000"
      }
    ],
    "marcacoes_de_plausibilidade": {
      "estadia_acima_de_30_dias": 1250,
      "prancha_acima_de_20000_th": 73,
      "coordenada_fora_do_territorio": 6
    }
  },
  "acuracia": {
    "teste": "dois navios nao podem ocupar a mesma posicao de atracacao simultaneamente",
    "atracacoes_avaliadas": 116321,
    "atracacoes_com_sobreposicao_de_berco": 36118,
    "pct_sobreposicao": 31.05,
    "bercos_com_ao_menos_uma_sobreposicao": 408,
    "total_bercos": 625,
    "mediana_horas_sobrepostas": 6.77,
    "p95_horas_sobrepostas": 137.03,
    "bercos_com_posicao_unica": 212,
    "pct_bercos_com_posicao_unica": 33.92,
    "ocupacao_simultanea_maxima": 125,
    "interpretacao": "A sobreposicao nao e erro de declaracao em massa: IDBerco designa cais, area ou conjunto de posicoes, e nao uma posicao exclusiva. A consequencia e que taxas de ocupacao calculadas com uma posicao por berco seriam invalidas.",
    "atracacoes_sem_carga_declarada": 22145,
    "pct_sem_carga_declarada": 19.04
  },
  "atualidade": {
    "primeira_desatracacao": "2025-01-01",
    "ultima_desatracacao": "2025-12-31",
    "data_da_auditoria": "2026-11-16",
    "defasagem_dias": 320,
    "meses_cobertos": 12
  },
  "aptidao": {
    "aptas_analise_tempo": 115071,
    "pct_aptas": 98.92,
    "sem_data_de_operacao": 6695,
    "pct_sem_data_de_operacao": 5.76
  }
}
```
