# Modelo de Dados

## Decisão de modelagem

O modelo é um **esquema estrela**, com uma tabela fato e cinco dimensões.

A escolha do grão veio da pergunta de negócio, não da conveniência de processamento. A decisão que este MVP apoia é onde intervir para recuperar capacidade de cais, e capacidade de cais é consumida por **atracação**. Por isso o grão da tabela fato é **uma linha por atracação**.

Essa definição tem uma consequência irreversível que precisa ficar explícita: uma vez agregado por atracação, o detalhe de cada item de carga deixa de ser recuperável na camada analítica. Foi uma escolha consciente. A granularidade de item de carga serviria a uma pergunta sobre mix de mercadorias, que não é a pergunta deste trabalho. O detalhe permanece disponível na camada bronze para quem precisar reabrir essa questão.

## Diagrama

```mermaid
erDiagram
    DIM_INSTALACAO  ||--o{ FATO_ATRACACAO : "ocorre em"
    DIM_BERCO       ||--o{ FATO_ATRACACAO : "utiliza"
    DIM_TEMPO       ||--o{ FATO_ATRACACAO : "desatraca em"
    DIM_NAVEGACAO   ||--o{ FATO_ATRACACAO : "classifica"
    DIM_NATUREZA    ||--o{ FATO_ATRACACAO : "movimenta"
    DIM_INSTALACAO  ||--o{ DIM_BERCO      : "possui"

    FATO_ATRACACAO {
        texto    sk_atracacao PK
        texto    sk_instalacao FK
        texto    sk_berco FK
        data     sk_data FK
        inteiro  sk_navegacao FK
        inteiro  sk_natureza FK
        numerico t1_espera_atracacao_h
        numerico t2_espera_inicio_op_h
        numerico t3_operacao_h
        numerico t4_espera_desatracacao_h
        numerico ta_atracado_h
        numerico te_estadia_h
        numerico berco_improdutivo_h
        numerico peso_bruto_t
        numerico teu
        numerico prancha_operacional_th
        booleano flags_de_qualidade
    }
    DIM_INSTALACAO {
        texto    sk_instalacao PK
        texto    porto_atracacao
        texto    complexo_portuario
        texto    tipo_autoridade
        texto    municipio
        texto    sguf
        texto    regiao_geografica
        texto    instalacao_em_rio
        numerico latitude
        numerico longitude
    }
    DIM_BERCO {
        texto sk_berco PK
        texto berco
        texto sk_instalacao FK
    }
    DIM_TEMPO {
        data    sk_data PK
        inteiro ano
        inteiro mes
        texto   nome_mes
        inteiro trimestre
        inteiro semestre
        inteiro dia_semana
        booleano fim_de_semana
    }
    DIM_NAVEGACAO {
        inteiro  sk_navegacao PK
        texto    tipo_navegacao
        texto    tipo_operacao
        booleano operacao_produtiva
    }
    DIM_NATUREZA {
        inteiro  sk_natureza PK
        texto    natureza_carga
        booleano granel
    }
```

## Linhagem: do arquivo bruto à camada analítica

```mermaid
flowchart LR
    A1["Atracacao.txt<br/>116.327 linhas<br/>29 colunas"]:::raw
    A2["Carga.txt<br/>2.467.854 linhas<br/>27 colunas"]:::raw

    B1["bronze/atracacao<br/>cópia fiel"]:::bronze
    B2["bronze/carga<br/>cópia fiel"]:::bronze

    S1["silver/atracacao_tratada<br/>tipagem + cálculo T1 a T4<br/>+ flags de qualidade"]:::silver
    S2["agregação por IDAtracacao<br/>filtro de autorização<br/>2.467.854 para 2.294.271"]:::silver

    G1["fato_atracacao<br/>116.327"]:::gold
    G2["5 dimensões"]:::gold

    A1 --> B1 --> S1
    A2 --> B2 --> S2
    S2 -- "junção 1:1<br/>por IDAtracacao" --> S1
    S1 --> G1
    S1 --> G2

    classDef raw fill:#f4f3ef,stroke:#8a8882,color:#0b0b0b
    classDef bronze fill:#fdf0e8,stroke:#eb6834,color:#0b0b0b
    classDef silver fill:#eaf2fc,stroke:#2a78d6,color:#0b0b0b
    classDef gold fill:#e7f7f1,stroke:#1baf7a,color:#0b0b0b
```

## O ponto crítico da transformação: conciliação de grãos diferentes

As duas tabelas de origem estão em grãos distintos. `Atracacao.txt` tem uma linha por atracação. `Carga.txt` tem uma linha por item de carga, e uma mesma atracação pode ter milhares de itens, com máximo observado de 7.292.

Uma junção direta entre as duas multiplicaria cada atracação pelo número de seus itens de carga e inflaria qualquer soma de tempo em ordens de grandeza. A tabela fato passaria de 116.327 para mais de 2 milhões de linhas, e o tempo de operação de um navio seria contado uma vez para cada caixa movimentada.

A transformação correta tem três passos, nesta ordem:

1. **Filtrar** os itens de carga pelas marcas de validação da própria agência, `FlagAutorizacao = S` e `FlagMCOperacaoCarga = 1`. Isso remove 173.583 itens, que são registros ainda em revisão pela ANTAQ.
2. **Agregar** por `IDAtracacao`, somando peso bruto e TEU, contando itens e identificando a natureza de carga predominante por maior peso.
3. **Juntar** o resultado, agora no grão de atracação, por `IDAtracacao`, em relação um para um.

As 22.145 atracações sem nenhum item de carga correspondente, 19,04% do total, não são erro de junção. São atracações de apoio, passageiro, abastecimento e reparo, que de fato não movimentam carga. Elas são preservadas e marcadas em `flag_sem_carga_declarada`, porque consomem berço mesmo sem movimentar carga, e portanto importam para a decisão sobre capacidade.

## Por que esquema estrela e não tabela única

A alternativa seria manter um único arquivo largo com todos os atributos repetidos linha a linha. O esquema estrela foi escolhido por três razões práticas neste problema:

A primeira é que as dimensões de instalação e de berço são consultadas de forma independente da fato. A pergunta sobre multiplicidade de posições por berço, que acabou sendo determinante para o resultado, é respondida com uma junção entre a dimensão de berço e a fato, e seria desnecessariamente cara em formato largo.

A segunda é que os atributos descritivos da instalação mudam de significado ao longo do tempo, enquanto os fatos não. Separar a descrição do evento deixa essa diferença explícita.

A terceira é auditabilidade. Cada medida da tabela fato tem linhagem declarada até a coluna de origem, e cada atributo descritivo tem um único lugar onde é definido. Uma inconsistência de nome de porto, por exemplo, aparece em uma linha da dimensão, não espalhada por milhares de linhas de fato.
