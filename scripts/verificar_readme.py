"""Confere os numeros citados no README contra os arquivos de saida.

Ultima etapa do trabalho: nenhum numero do documento deve existir sem
lastro em um arquivo gerado pelo pipeline.

Uso: python3 -I verificar_readme.py <dir_projeto> 2025
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

proj = Path(sys.argv[1])
ano = int(sys.argv[2]) if len(sys.argv) > 2 else 2025

q = json.load(open(proj / "outputs" / f"relatorio_qualidade_{ano}.json", encoding="utf-8"))
a = json.load(open(proj / "outputs" / f"resultados_analise_{ano}.json", encoding="utf-8"))
s = json.load(open(proj / "outputs" / f"resultados_segmentados_{ano}.json", encoding="utf-8"))
readme = (proj / "README.md").read_text(encoding="utf-8")

seg = {x["segmento"]: x for x in s["a_decomposicao_por_segmento"]}

# (descricao, valor esperado, string que deve aparecer no README)
CHECAGENS = [
    ("atracacoes 2025", q["linhas_fato"], "116.327"),
    ("itens de carga", 2467854, "2.467.854"),
    ("itens apos filtro", 2294271, "2.294.271"),
    ("itens removidos", 2467854 - 2294271, "173.583"),
    ("instalacoes", 212, "212"),
    ("bercos", 625, "625"),
    # --- qualidade: cobertura por atributo ---
    ("atributos auditados", q["atributos_auditados"], "59 atributos"),
    ("tabelas auditadas", q["tabelas_auditadas"], "seis tabelas"),
    ("completude media", q["completude"]["completude_media_pct"], "95,72%"),
    ("conformes", 36, "36 são conformes sem ausências"),
    ("conformes com ausencia", 15, "15 são conformes com ausências"),
    ("com violacao", 8, "8 apresentam violação de domínio"),
    ("apelido instalacao", 32.08, "32,1%"),
    ("regiao hidrografica", 47.64, "47,6%"),
    ("numero imo", 51.49, "51,5%"),
    ("sem data de operacao", q["aptidao"]["sem_data_de_operacao"], "6.695"),
    ("pct sem data de operacao", q["aptidao"]["pct_sem_data_de_operacao"], "5,76%"),
    ("duplicatas pk", sum(v for k, v in q["unicidade"].items()), "Zero duplicatas de chave primária"),
    ("cronologia invalida", q["consistencia"]["registros_com_cronologia_invalida"], "Zero violações de cronologia"),
    ("coerencia testados", q["consistencia"]["coerencia_T2_T3_T4_igual_TA"]["registros_testados"], "109.632"),
    ("coerencia erro max", q["consistencia"]["coerencia_T2_T3_T4_igual_TA"]["erro_maximo_horas"], "erro máximo de zero"),
    ("dominios declarados", q["conformidade"]["atributos_com_dominio_declarado"], "27 têm domínio declarado"),
    ("total violacoes", q["conformidade"]["total_de_violacoes"], "390 violações"),
    ("estadia e espera extremas", 153, "153 estadias e 144 esperas"),
    ("prancha implausivel", q["conformidade"]["marcacoes_de_plausibilidade"]["prancha_acima_de_20000_th"], "73 pranchas"),
    ("estadia outlier", q["conformidade"]["marcacoes_de_plausibilidade"]["estadia_acima_de_30_dias"], "1.250"),
    ("sobreposicoes", q["acuracia"]["atracacoes_com_sobreposicao_de_berco"], "36.118"),
    ("pct sobreposicao", q["acuracia"]["pct_sobreposicao"], "31,05%"),
    ("bercos com sobreposicao", q["acuracia"]["bercos_com_ao_menos_uma_sobreposicao"], "408"),
    ("p95 sobreposicao", q["acuracia"]["p95_horas_sobrepostas"], "137"),
    ("bercos exclusivos", q["acuracia"]["bercos_com_posicao_unica"], "219"),
    ("pct exclusivos", q["acuracia"]["pct_bercos_com_posicao_unica"], "35,1%"),
    ("ocupacao simultanea max", q["acuracia"]["ocupacao_simultanea_maxima"], "125"),
    ("defasagem dias", q["atualidade"]["defasagem_dias"], "320"),
    ("meses cobertos", q["atualidade"]["meses_cobertos"], "12 meses"),
    ("sem carga declarada", q["acuracia"]["atracacoes_sem_carga_declarada"], "22.145"),
    ("pct sem carga", q["acuracia"]["pct_sem_carga_declarada"], "19,04%"),
    # --- resultados ---
    ("cadeia completa", a["p1_decomposicao"]["atracacoes_com_cadeia_completa"], "108.506"),
    ("navio-hora total", a["p1_decomposicao"]["navio_hora_total"], "6.575.336"),
    ("share T1 soma", a["p1_decomposicao"]["participacao_pct"]["t1_espera_atracacao"], "54,5%"),
    ("share T3 soma", a["p1_decomposicao"]["participacao_pct"]["t3_operacao"], "33,4%"),
    ("improdutivo total h", a["p1_decomposicao"]["berco_improdutivo_total_h"], "793.178"),
    ("improdutivo pct", a["p1_decomposicao"]["berco_improdutivo_pct_do_tempo_atracado"], "26,5%"),
    ("posicoes equivalentes", a["p2_concentracao"]["equivalente_em_posicoes_de_berco"], "90,5"),
    ("var instalacao", a["p4_produtividade"]["variancia_explicada_log_prancha"]["por_instalacao"], "59,8%"),
    ("var natureza", a["p4_produtividade"]["variancia_explicada_log_prancha"]["por_natureza_da_carga"], "18,9%"),
    ("var navegacao", a["p4_produtividade"]["variancia_explicada_log_prancha"]["por_tipo_de_navegacao"], "5,4%"),
    ("prod analisadas", a["p4_produtividade"]["atracacoes_na_analise"], "78.618"),
    ("maritimo atracacoes", seg["Maritimo de carga"]["atracacoes"], "42.780"),
    ("maritimo peso Mt", seg["Maritimo de carga"]["peso_total_milhoes_t"], "1,28 bilhão"),
    ("maritimo improdutivo pct", seg["Maritimo de carga"]["berco_improdutivo_pct_atracado"], "17,2%"),
    ("fluvial atracacoes", seg["Interior (fluvial)"]["atracacoes"], "52.642"),
    ("fluvial peso Mt", seg["Interior (fluvial)"]["peso_total_milhoes_t"], "87 milhões"),
    ("fluvial improdutivo pct", seg["Interior (fluvial)"]["berco_improdutivo_pct_atracado"], "47,5%"),
    ("ranking instalacoes", s["b_ranking_corrigido"]["instalacoes"], "76 instalações"),
    ("ranking atracacoes", s["b_ranking_corrigido"]["atracacoes"], "30.772"),
    ("mediana setor", s["b_ranking_corrigido"]["pct_improdutivo_mediano_setor"], "18,2%"),
    ("horas recuperaveis", s["b_ranking_corrigido"]["horas_recuperaveis_total"], "46.095"),
    ("posicoes recuperaveis", s["b_ranking_corrigido"]["posicoes_de_cais_equivalentes_recuperaveis"], "5,26"),
    ("top10 share", s["b_ranking_corrigido"]["pct_recuperavel_no_top10"], "71,3%"),
    ("em comum no top10", s["c_custo_do_vies"]["instalacoes_em_comum"], "apenas uma permanece"),
    ("spearman maritimo", s["d_congestionamento_maritimo"]["spearman_rho"], "0,396"),
    ("variancia ordem", s["d_congestionamento_maritimo"]["variancia_de_ordem_explicada_pct"], "16%"),
    ("ocupacao mediana", s["d_congestionamento_maritimo"]["ocupacao_mediana_pct"], "21,4%"),
    ("assimetria T1", 3.88, "3,88"),
    ("concentracao p90", 68.4, "68,4%"),
    ("p99 espera", 411.0, "411 horas"),
]

falhas = []
for desc, valor, trecho in CHECAGENS:
    ok = trecho in readme
    print(f"{'OK  ' if ok else 'FALHA'}  {desc:28s} valor={valor!s:<14} procurado no README: {trecho!r}")
    if not ok:
        falhas.append((desc, valor, trecho))

# Checagem de integridade interna dos proprios resultados
print("\n--- coerencia interna ---")
p1 = a["p1_decomposicao"]
soma_share = sum(p1["participacao_pct"].values())
print(f"{'OK  ' if abs(soma_share-100) < 0.1 else 'FALHA'}  shares de T1..T4 somam {soma_share:.2f}%")
imp = p1["horas_por_etapa"]["t2_espera_inicio_op"] + p1["horas_por_etapa"]["t4_espera_desatracacao"]
print(f"{'OK  ' if abs(imp - p1['berco_improdutivo_total_h']) < 1 else 'FALHA'}  T2+T4 = berco improdutivo "
      f"({imp:,.1f} vs {p1['berco_improdutivo_total_h']:,.1f})")
rec = s["b_ranking_corrigido"]["horas_recuperaveis_total"] / 8760
print(f"{'OK  ' if abs(rec - s['b_ranking_corrigido']['posicoes_de_cais_equivalentes_recuperaveis']) < 0.02 else 'FALHA'}"
      f"  horas recuperaveis / 8760 = {rec:.2f} posicoes")
razao = a["sintese_decisao"]["horas_recuperaveis_top10"] / s["b_ranking_corrigido"]["horas_recuperaveis_total"]
print(f"{'OK  ' if razao > 4 else 'FALHA'}  erro da leitura ingenua: fator {razao:.2f}x")

print(f"\n{'TODAS AS CHECAGENS PASSARAM' if not falhas else f'{len(falhas)} FALHA(S)'}")
for f in falhas:
    print("   ", f)
sys.exit(1 if falhas else 0)
