"""
Coleta dos arquivos brutos do Estatistico Aquaviario da ANTAQ.

A ANTAQ migrou o painel em 2026 e o endereco antigo web3.antaq.gov.br saiu
do ar. Este script tenta os endpoints conhecidos e, se nenhum responder,
imprime o roteiro manual. A coleta manual e um caminho legitimo e esta
documentada: o que importa para a reprodutibilidade e registrar origem,
data e volume, o que o script faz nos dois casos.

Uso:
    python3 -I coleta.py --ano 2025 --dest dados_brutos
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PORTAL = "https://www.gov.br/antaq/pt-br/assuntos/estatistica"
PAINEL = "http://ea.antaq.gov.br"

# Endpoints ja usados pela agencia, do mais recente para o mais antigo.
CANDIDATOS = [
    "https://web3.antaq.gov.br/ea/txt/{ano}.zip",
    "https://estatistica.antaq.gov.br/ea/txt/{ano}.zip",
    "https://web3.antaq.gov.br/ea/txt/{ano}Atracacao.txt",
]

ARQUIVOS_ESPERADOS = ["{ano}Atracacao.txt", "{ano}Carga.txt"]

ROTEIRO_MANUAL = """
================================================================
COLETA MANUAL (quando os endpoints diretos nao respondem)
================================================================
1. Acesse o Painel do Estatistico Aquaviario:
       {portal}
   ou diretamente: {painel}
2. Abra a aba "Base de Dados".
3. Selecione o ano desejado ({ano}).
4. Clique em "Download de todos os arquivos do ano escolhido".
5. Baixe tambem, na mesma aba:
       - o dicionario de dados
       - a modelagem dos dados
6. Extraia o zip dentro de: {dest}
7. Rode novamente este script com --somente-registrar para gerar o
   manifesto de coleta (origem, data, volume e hash de cada arquivo).
================================================================
"""


def sha256(p: Path, blocos: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(blocos), b""):
            h.update(b)
    return h.hexdigest()


def tentar_download(ano: int, dest: Path) -> list[Path]:
    baixados: list[Path] = []
    for tpl in CANDIDATOS:
        url = tpl.format(ano=ano)
        alvo = dest / url.rsplit("/", 1)[-1]
        try:
            print(f"[coleta] tentando {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(alvo, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            print(f"[coleta] obtido: {alvo.name} ({alvo.stat().st_size:,} bytes)")
            baixados.append(alvo)
            if alvo.suffix == ".zip":
                with zipfile.ZipFile(alvo) as z:
                    z.extractall(dest)
                print(f"[coleta] extraido: {z.namelist()}")
            break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            print(f"[coleta] falhou: {type(e).__name__}: {e}")
            alvo.unlink(missing_ok=True)
    return baixados


def registrar(ano: int, dest: Path) -> dict:
    """Gera o manifesto de coleta: o que torna o trabalho reproduzivel."""
    manifesto = {
        "fonte": "ANTAQ, Estatistico Aquaviario, Sistema de Desempenho Portuario (SDP)",
        "portal": PORTAL,
        "painel": PAINEL,
        "ano_referencia": ano,
        "coletado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "licenca": ("Dado publico. A ANTAQ disponibiliza a base para uso livre, "
                    "com exigencia de citacao da fonte. Nao contem dados pessoais: "
                    "o registro e por atracacao de embarcacao, nao por individuo."),
        "arquivos": [],
    }
    for nome in ARQUIVOS_ESPERADOS:
        p = dest / nome.format(ano=ano)
        if p.exists():
            with open(p, "r", encoding="utf-8-sig") as f:
                cabecalho = f.readline().strip()
                linhas = sum(1 for _ in f)
            manifesto["arquivos"].append({
                "arquivo": p.name,
                "bytes": p.stat().st_size,
                "linhas_de_dados": linhas,
                "colunas": len(cabecalho.split(";")),
                "separador": ";",
                "codificacao": "utf-8 com BOM",
                "sha256": sha256(p),
            })
            print(f"[coleta] registrado {p.name}: {linhas:,} linhas, "
                  f"{len(cabecalho.split(';'))} colunas")
        else:
            manifesto["arquivos"].append({"arquivo": p.name, "status": "ausente"})
            print(f"[coleta] AUSENTE: {p.name}")
    return manifesto


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ano", type=int, default=2025)
    ap.add_argument("--dest", default="dados_brutos")
    ap.add_argument("--somente-registrar", action="store_true",
                    help="pula o download e so gera o manifesto dos arquivos ja presentes")
    a = ap.parse_args()

    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)

    if not a.somente_registrar:
        tentar_download(a.ano, dest)

    faltando = [n.format(ano=a.ano) for n in ARQUIVOS_ESPERADOS
                if not (dest / n.format(ano=a.ano)).exists()]
    if faltando:
        print(f"\n[coleta] arquivos ausentes: {faltando}")
        print(ROTEIRO_MANUAL.format(portal=PORTAL, painel=PAINEL, ano=a.ano, dest=dest.resolve()))

    manifesto = registrar(a.ano, dest)
    saida = dest / f"manifesto_coleta_{a.ano}.json"
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
    print(f"\n[coleta] manifesto escrito em {saida}")
    return 0 if not faltando else 2


if __name__ == "__main__":
    sys.exit(main())
