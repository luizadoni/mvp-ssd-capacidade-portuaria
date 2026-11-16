"""Gera o Catalogo de Dados a partir da camada gold.

Os dominios sao medidos no proprio dado, nao declarados de memoria.
Uso: python3 -I gerar_catalogo.py --proj <dir> --ano 2025
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Descricao e linhagem de cada atributo. A linhagem indica a coluna de origem
# no arquivo bruto da ANTAQ e a transformacao aplicada" + " até " + "a camada gold.
META = {
    # ---------------- fato_atracacao ----------------
    ("fato_atracacao", "sk_atracacao"): ("Identificador único da atracação", "Atracacao.txt / IDAtracacao", "cópia direta"),
    ("fato_atracacao", "sk_instalacao"): ("Instalação portuária onde ocorreu a atracação", "Atracacao.txt / CDTUP", "cópia direta, usada como FK"),
    ("fato_atracacao", "sk_berco"): ("Berço utilizado", "Atracacao.txt / IDBerco", "cópia direta, usada como FK"),
    ("fato_atracacao", "sk_data"): ("Data de desatracação, convenção temporal da ANTAQ", "Atracacao.txt / Data Desatracação", "truncada para data"),
    ("fato_atracacao", "sk_navegacao"): ("Combinação de tipo de navegação e tipo de operação", "Atracacao.txt / Tipo de Navegação + Tipo de Operação", "chave sintética gerada na gold"),
    ("fato_atracacao", "sk_natureza"): ("Natureza de carga predominante na atracação", "Carga.txt / Natureza da Carga", "maior peso bruto por atracação"),
    ("fato_atracacao", "nacionalidade_armador"): ("Nacionalidade do armador", "Atracacao.txt / Nacionalidade do Armador", "cópia direta"),
    ("fato_atracacao", "numero_imo"): ("Número IMO da embarcação", "Atracacao.txt / N do IMO", "cópia direta"),
    ("fato_atracacao", "t1_espera_atracacao_h"): ("Tempo entre a chegada à área de fundeio e a atracação", "Atracacao.txt / Data Atracação menos Data Chegada", "diferença em horas"),
    ("fato_atracacao", "t2_espera_inicio_op_h"): ("Tempo atracado antes do início da operação", "Atracacao.txt / Data Início Operação menos Data Atracação", "diferença em horas"),
    ("fato_atracacao", "t3_operacao_h"): ("Duração da operação de carga ou descarga", "Atracacao.txt / Data Término Operação menos Data Início Operação", "diferença em horas"),
    ("fato_atracacao", "t4_espera_desatracacao_h"): ("Tempo atracado após o término da operação", "Atracacao.txt / Data Desatracação menos Data Término Operação", "diferença em horas"),
    ("fato_atracacao", "ta_atracado_h"): ("Tempo total atracado", "Atracacao.txt / Data Desatracação menos Data Atracação", "diferença em horas, equivale a T2+T3+T4"),
    ("fato_atracacao", "te_estadia_h"): ("Estadia total no porto", "Atracacao.txt / Data Desatracação menos Data Chegada", "diferença em horas, equivale a T1+TA"),
    ("fato_atracacao", "berco_improdutivo_h"): ("Tempo de berço ocupado sem operação", "derivado", "T2 mais T4"),
    ("fato_atracacao", "peso_bruto_t"): ("Peso bruto movimentado na atracação", "Carga.txt / VLPesoCargaBruta", "soma por IDAtracacao, itens autorizados"),
    ("fato_atracacao", "teu"): ("Unidades equivalentes a vinte pés movimentadas", "Carga.txt / TEU", "soma por IDAtracacao"),
    ("fato_atracacao", "qtd_itens_carga"): ("Número de registros de carga da atracação", "Carga.txt / IDCarga", "contagem por IDAtracacao"),
    ("fato_atracacao", "prancha_operacional_th"): ("Produtividade durante a operação", "derivado", "peso bruto dividido por T3"),
    ("fato_atracacao", "prancha_geral_th"): ("Produtividade considerando todo o tempo atracado", "derivado", "peso bruto dividido por TA"),
    ("fato_atracacao", "flag_cronologia_invalida"): ("Marca registro cuja sequência de datas é impossível", "derivado", "algum tempo negativo"),
    ("fato_atracacao", "flag_operacao_ausente"): ("Marca registro sem data de início ou término de operação", "derivado", "teste de nulo"),
    ("fato_atracacao", "flag_estadia_outlier"): ("Marca estadia acima de 30 dias", "derivado", "TE maior que 720 horas"),
    ("fato_atracacao", "flag_sem_carga_declarada"): ("Marca atracação sem item de carga associado", "derivado", "ausência de correspondência em Carga.txt"),
    ("fato_atracacao", "flag_atracacao_exclusiva"): ("Atracação que movimentou um único perfil de carga", "derivado", "contagem distinta de natureza igual a um"),
    ("fato_atracacao", "flag_prancha_implausivel"): ("Marca prancha acima do limite de plausibilidade", "derivado", "prancha acima de 20000 t/h"),
    ("fato_atracacao", "flag_fora_bbox"): ("Marca coordenada fora do território brasileiro", "derivado", "teste de caixa delimitadora"),
    ("fato_atracacao", "flag_apto_analise_tempo"): ("Registro válido para análise de tempo", "derivado", "sem cronologia inválida, sem outlier e com TA definido"),
    # ---------------- dim_instalacao ----------------
    ("dim_instalacao", "sk_instalacao"): ("Código da instalação portuária", "Atracacao.txt / CDTUP", "chave primaria"),
    ("dim_instalacao", "porto_atracacao"): ("Nome do porto ou terminal", "Atracacao.txt / Porto Atracação", "último valor observado no ano"),
    ("dim_instalacao", "complexo_portuario"): ("Complexo portuário, agrupamento territorial da ANTAQ", "Atracacao.txt / Complexo Portuário", "último valor observado"),
    ("dim_instalacao", "apelido_instalacao"): ("Apelido da instalação", "Atracacao.txt / Apelido Instalação Portuária", "último valor observado"),
    ("dim_instalacao", "tipo_autoridade"): ("Porto organizado ou terminal autorizado", "Atracacao.txt / Tipo da Autoridade Portuária", "último valor observado"),
    ("dim_instalacao", "municipio"): ("Município da instalação", "Atracacao.txt / Município", "último valor observado"),
    ("dim_instalacao", "uf"): ("Unidade da federação por extenso", "Atracacao.txt / UF", "último valor observado"),
    ("dim_instalacao", "sguf"): ("Sigla da unidade da federação", "Atracacao.txt / SGUF", "último valor observado"),
    ("dim_instalacao", "regiao_geografica"): ("Região geográfica do IBGE", "Atracacao.txt / Região Geográfica", "último valor observado"),
    ("dim_instalacao", "regiao_hidrografica"): ("Região hidrográfica, preenchida para instalações fluviais", "Atracacao.txt / Região Hidrográfica", "último valor observado"),
    ("dim_instalacao", "instalacao_em_rio"): ("Indica instalação fluvial", "Atracacao.txt / Instalação Portuária em Rio", "último valor observado"),
    ("dim_instalacao", "latitude"): ("Latitude da instalação", "Atracacao.txt / Coordenadas", "segundo elemento após separação por vírgula"),
    ("dim_instalacao", "longitude"): ("Longitude da instalação", "Atracacao.txt / Coordenadas", "primeiro elemento após separação por vírgula"),
    # ---------------- dim_berco ----------------
    ("dim_berco", "sk_berco"): ("Código do berço", "Atracacao.txt / IDBerco", "chave primaria"),
    ("dim_berco", "berco"): ("Identificação do berço declarada pela instalação", "Atracacao.txt / Berço", "último valor observado"),
    ("dim_berco", "sk_instalacao"): ("Instalação a que o berço pertence", "Atracacao.txt / CDTUP", "FK para dim_instalacao"),
    # ---------------- dim_tempo ----------------
    ("dim_tempo", "sk_data"): ("Data de desatracação", "derivado", "chave primaria"),
    ("dim_tempo", "ano"): ("Ano", "derivado", "extraído de sk_data"),
    ("dim_tempo", "mes"): ("Mes", "derivado", "extraído de sk_data"),
    ("dim_tempo", "nome_mes"): ("Competência no formato AAAA-MM", "derivado", "extraído de sk_data"),
    ("dim_tempo", "trimestre"): ("Trimestre", "derivado", "extraído de sk_data"),
    ("dim_tempo", "semestre"): ("Semestre", "derivado", "extraído de sk_data"),
    ("dim_tempo", "dia_semana"): ("Dia da semana, zero igual a segunda", "derivado", "extraído de sk_data"),
    ("dim_tempo", "fim_de_semana"): ("Indica sábado ou domingo", "derivado", "dia_semana maior ou igual a cinco"),
    # ---------------- dim_navegacao ----------------
    ("dim_navegacao", "sk_navegacao"): ("Chave sintética", "derivado", "chave primaria"),
    ("dim_navegacao", "tipo_navegacao"): ("Modo de navegação da atracação", "Atracacao.txt / Tipo de Navegação da Atracação", "cópia direta"),
    ("dim_navegacao", "tipo_operacao"): ("Finalidade da atracação", "Atracacao.txt / Tipo de Operação", "cópia direta"),
    ("dim_navegacao", "operacao_produtiva"): ("Indica atracação que movimenta carga", "derivado", "tipo de operação em lista de referência"),
    # ---------------- dim_natureza_carga ----------------
    ("dim_natureza_carga", "sk_natureza"): ("Chave sintética", "derivado", "chave primaria"),
    ("dim_natureza_carga", "natureza_carga"): ("Natureza da carga", "Carga.txt / Natureza da Carga", "cópia direta mais categoria para ausencia"),
    ("dim_natureza_carga", "granel"): ("Indica carga a granel", "derivado", "prefixo do nome da natureza"),
}

TIPOS = {"object": "texto", "str": "texto", "datetime64[ms]": "data", "float64": "numérico", "int64": "inteiro", "int32": "inteiro",
         "bool": "booleano", "datetime64[ns]": "data", "category": "categorico"}


def dominio(s: pd.Series) -> str:
    s2 = s.dropna()
    if s2.empty:
        return "sem valores preenchidos"
    if pd.api.types.is_bool_dtype(s2):
        return "verdadeiro ou falso"
    if pd.api.types.is_datetime64_any_dtype(s2):
        return f"{s2.min().date()} até {s2.max().date()}"
    if pd.api.types.is_numeric_dtype(s2):
        return f"{s2.min():,.2f} até {s2.max():,.2f} (mediana {s2.median():,.2f})"
    u = s2.unique()
    if len(u) <= 9:
        return "; ".join(sorted(map(str, u)))
    return f"{len(u):,} valores distintos (ex.: {', '.join(map(str, sorted(map(str, u))[:3]))})"


def carregar_regras(proj: Path, ano: int) -> dict:
    """Lê o domínio DECLARADO a partir da mesma fonte usada pela auditoria
    de conformidade, para que catálogo e auditoria nunca divirjam."""
    csv = proj / "outputs" / f"qualidade_por_atributo_{ano}.csv"
    if not csv.exists():
        return {}
    q = pd.read_csv(csv)
    return {(r.tabela, r.atributo): r.regra_de_dominio for r in q.itertuples()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", required=True)
    ap.add_argument("--ano", type=int, default=2025)
    a = ap.parse_args()
    proj, ano = Path(a.proj), a.ano
    g = proj / "dados" / "gold"

    regras = carregar_regras(proj, ano)
    ordem = ["fato_atracacao", "dim_instalacao", "dim_berco", "dim_tempo",
             "dim_navegacao", "dim_natureza_carga"]
    L: list[str] = []
    L.append("# Catálogo de Dados")
    L.append("")
    L.append(f"Camada **gold**, esquema estrela, ano de referência **{ano}**.")
    L.append("")
    L.append("Fonte primária: ANTAQ, Estatístico Aquaviário, tabelas `Atracacao.txt` e `Carga.txt`.")
    L.append("**Domínio esperado** é a regra declarada antes de olhar o dado, e é contra ela que a conformidade é medida em `scripts/qualidade.py`.")
    L.append("**Domínio observado** é o que o dado efetivamente apresentou. A divergência entre os dois está quantificada no relatório de qualidade.")
    L.append("A coluna Linhagem indica a origem no arquivo bruto e a transformação aplicada.")
    L.append("")
    L.append("Grão da tabela fato: **uma linha por atracação**.")
    L.append("")

    for nome in ordem:
        df = pd.read_parquet(g / f"{nome}_{ano}.parquet")
        L.append(f"## {nome}")
        L.append("")
        L.append(f"Linhas: **{len(df):,}**  ·  Atributos: **{len(df.columns)}**")
        L.append("")
        L.append("| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |")
        L.append("|---|---|---|---|---|---|---|")
        for c in df.columns:
            desc, origem, transf = META.get((nome, c), ("", "", ""))
            tipo = TIPOS.get(str(df[c].dtype), str(df[c].dtype))
            nulos = df[c].isna().mean()
            n_nulos = int(df[c].isna().sum())
            if n_nulos == 0:
                obrig = "sim"
            elif nulos < 0.001:
                obrig = f"sim, com {n_nulos} exceção(ões)"
            else:
                obrig = f"não ({nulos*100:.1f}% nulo)"
            lin = f"`{origem}` · {transf}" if origem else ""
            esperado = regras.get((nome, c), "sem domínio declarado")
            if esperado == "sem domínio declarado":
                esperado = "livre (identificador ou texto descritivo)"
            L.append(f"| `{c}` | {tipo} | {desc} | {esperado} | {dominio(df[c])} | {obrig} | {lin} |")
        L.append("")

    L.append("## Regras de negócio aplicadas na transformação")
    L.append("")
    L.append("1. **Definição dos tempos.** T1 é a diferença entre atracação e chegada; T2 entre início de operação e atracação; T3 entre término e início de operação; T4 entre desatracação e término de operação. As definições seguem a Documentação do Estatístico Aquaviário da ANTAQ.")
    L.append("2. **Filtro de autorização na carga.** Só entram no cálculo de peso e TEU os itens com `FlagAutorizacao = S` e `FlagMCOperacaoCarga = 1`, que são os registros validados pela agência. Isso reduziu 2.467.854 itens para 2.294.271.")
    L.append("3. **Conciliação de grão.** A tabela de carga tem vários itens por atracação. Os itens são agregados por `IDAtracacao` antes da junção, caso contrário a tabela fato duplicaria atracações.")
    L.append("4. **Natureza predominante.** Quando uma atracação movimenta mais de um perfil de carga, prevalece o de maior peso bruto. O caso de perfil único é marcado em `flag_atracacao_exclusiva`, seguindo a definição de atracação exclusiva da ANTAQ.")
    L.append("5. **Valores ausentes não são imputados.** A ausência é marcada em coluna própria para que possa ser medida como indicador de qualidade, em vez de ficar oculta sob um valor substituto.")
    L.append("6. **Registros inválidos não são excluídos.** São marcados por flags, de modo que cada análise declare explicitamente qual subconjunto utilizou.")
    L.append("7. **Convenção temporal.** Atributos de tempo usam a data de desatracação, conforme convenção da própria ANTAQ.")

    out = proj / "catalogo" / "catalogo_dados.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"catalogo gerado: {out} ({len('\n'.join(L)):,} caracteres)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
