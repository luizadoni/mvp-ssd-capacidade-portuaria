# Roteiro de evidências

O enunciado exige que os dados estejam efetivamente persistidos na nuvem ao final do trabalho e que isso seja demonstrável. Este roteiro lista as capturas necessárias, na ordem em que devem ser feitas, e o que cada uma comprova.

Cada arquivo deve ser salvo nesta pasta com o nome indicado, para que o README possa referenciá-lo no ponto exato do texto em que sustenta a afirmação.

## 1. Coleta

**`01_painel_antaq_download.png`**
Tela do Painel Estatístico Aquaviário, aba Base de Dados, com o ano de 2025 selecionado e o botão de download visível.
Comprova: origem oficial dos dados e data da coleta.

**`02_arquivos_baixados.png`**
Listagem da pasta local mostrando `2025Atracacao.txt` e `2025Carga.txt` com seus tamanhos.
Comprova: volume obtido. Os números devem bater com `manifesto_coleta_2025.json`, que já está nesta pasta e traz o hash SHA256 de cada arquivo.

## 2. Carga na nuvem

**`03_volume_unity_catalog.png`**
Aba Catalog do Databricks mostrando o Volume com os dois arquivos brutos carregados.
Comprova: os dados brutos chegaram à plataforma de nuvem.

**`04_notebook_executado.png`**
Notebook `01_pipeline_databricks.py` com todas as células executadas e a saída das contagens de bronze, silver e gold visível.
Comprova: o pipeline de ETL rodou na nuvem, não apenas localmente.

**`05_show_tables.png`**
Saída da célula `SHOW TABLES IN workspace.portos_mvp`, com as seis tabelas do esquema estrela listadas.
Comprova: persistência. Esta é a captura mais importante do conjunto.

**`06_describe_detail.png`**
Saída de `DESCRIBE DETAIL fato_atracacao`, mostrando formato Delta, número de arquivos e tamanho em bytes.
Comprova: a tabela é um objeto Delta materializado, não uma view temporária de sessão.

**`07_catalog_apos_cluster_desligado.png`**
Aba Catalog reaberta depois de encerrar o cluster, com as tabelas ainda presentes e consultáveis.
Comprova: a persistência sobrevive ao fim da sessão de computação. É o que distingue persistência real de resultado em memória.

## 3. Resultados das perguntas de negócio

**`08_sql_ranking.png`**
Saída da última célula do notebook, com o ranking de berço improdutivo por instalação calculado em SQL sobre as tabelas da nuvem.
Comprova: as respostas do trabalho são reproduzíveis na plataforma, e não apenas no ambiente local.

**`09_equivalencia_local_nuvem.png`**
Saída da célula de verificação de equivalência, ao lado do conteúdo de `outputs/relatorio_qualidade_2025.json`.
Comprova: as duas implementações, pandas e PySpark, aplicam as mesmas regras e chegam aos mesmos números.

## Checagem final antes de postar

Confira, um a um:

O repositório está público. Abra o link numa janela anônima para ter certeza.

Todas as imagens desta pasta estão referenciadas em algum ponto do README, no trecho de texto que elas sustentam.

Os números citados no README batem com os arquivos em `outputs/`.

As imagens estão legíveis em tamanho real, sem texto cortado.
