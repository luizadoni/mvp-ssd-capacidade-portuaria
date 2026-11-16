# Catálogo de Dados

Camada **gold**, esquema estrela, ano de referência **2025**.

Fonte primária: ANTAQ, Estatístico Aquaviário, tabelas `Atracacao.txt` e `Carga.txt`.
**Domínio esperado** é a regra declarada antes de olhar o dado, e é contra ela que a conformidade é medida em `scripts/qualidade.py`.
**Domínio observado** é o que o dado efetivamente apresentou. A divergência entre os dois está quantificada no relatório de qualidade.
A coluna Linhagem indica a origem no arquivo bruto e a transformação aplicada.

Grão da tabela fato: **uma linha por atracação**.

## fato_atracacao

Linhas: **116,327**  ·  Atributos: **28**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_atracacao` | texto | Identificador único da atracação | livre (identificador ou texto descritivo) | 116,327 valores distintos (ex.: 1520605, 1520606, 1520607) | sim | `Atracacao.txt / IDAtracacao` · cópia direta |
| `sk_instalacao` | texto | Instalação portuária onde ocorreu a atracação | livre (identificador ou texto descritivo) | 212 valores distintos (ex.: BR, BRADR, BRAL001) | sim | `Atracacao.txt / CDTUP` · cópia direta, usada como FK |
| `sk_berco` | texto | Berço utilizado | livre (identificador ou texto descritivo) | 625 valores distintos (ex.: ADR3101, ADR3102, ANT0113) | sim, com 6 exceção(ões) | `Atracacao.txt / IDBerco` · cópia direta, usada como FK |
| `sk_data` | data | Data de desatracação, convenção temporal da ANTAQ | livre (identificador ou texto descritivo) | 2025-01-01 até 2025-12-31 | sim | `Atracacao.txt / Data Desatracação` · truncada para data |
| `sk_navegacao` | numérico | Combinação de tipo de navegação e tipo de operação | livre (identificador ou texto descritivo) | 1.00 até 35.00 (mediana 12.00) | sim, com 6 exceção(ões) | `Atracacao.txt / Tipo de Navegação + Tipo de Operação` · chave sintética gerada na gold |
| `sk_natureza` | inteiro | Natureza de carga predominante na atracação | livre (identificador ou texto descritivo) | 1.00 até 5.00 (mediana 4.00) | sim | `Carga.txt / Natureza da Carga` · maior peso bruto por atracação |
| `nacionalidade_armador` | texto | Nacionalidade do armador | esperado em: 0; 1; 2 | 0; 1; 2 | sim, com 6 exceção(ões) | `Atracacao.txt / Nacionalidade do Armador` · cópia direta |
| `numero_imo` | texto | Número IMO da embarcação | livre (identificador ou texto descritivo) | 7,532 valores distintos (ex.: 0, 1013171, 1013640) | não (48.5% nulo) | `Atracacao.txt / N do IMO` · cópia direta |
| `t1_espera_atracacao_h` | numérico | Tempo entre a chegada à área de fundeio e a atracação | esperado entre 0 e 8,760 | 0.00 até 175,404.40 (mediana 1.00) | sim, com 6 exceção(ões) | `Atracacao.txt / Data Atracação menos Data Chegada` · diferença em horas |
| `t2_espera_inicio_op_h` | numérico | Tempo atracado antes do início da operação | esperado entre 0 e 8,760 | 0.00 até 175,320.50 (mediana 0.38) | não (5.8% nulo) | `Atracacao.txt / Data Início Operação menos Data Atracação` · diferença em horas |
| `t3_operacao_h` | numérico | Duração da operação de carga ou descarga | esperado entre 0 e 8,760 | 0.00 até 87,730.20 (mediana 7.08) | não (5.8% nulo) | `Atracacao.txt / Data Término Operação menos Data Início Operação` · diferença em horas |
| `t4_espera_desatracacao_h` | numérico | Tempo atracado após o término da operação | esperado entre 0 e 8,760 | 0.00 até 7,297.00 (mediana 0.92) | não (5.8% nulo) | `Atracacao.txt / Data Desatracação menos Data Término Operação` · diferença em horas |
| `ta_atracado_h` | numérico | Tempo total atracado | esperado entre 0 e 8,760 | 0.02 até 175,324.00 (mediana 11.13) | sim, com 6 exceção(ões) | `Atracacao.txt / Data Desatracação menos Data Atracação` · diferença em horas, equivale a T2+T3+T4 |
| `te_estadia_h` | numérico | Estadia total no porto | esperado entre 0 e 8,760 | 0.03 até 175,474.43 (mediana 20.57) | sim, com 6 exceção(ões) | `Atracacao.txt / Data Desatracação menos Data Chegada` · diferença em horas, equivale a T1+TA |
| `berco_improdutivo_h` | numérico | Tempo de berço ocupado sem operação | esperado entre 0 e 8,760 | 0.00 até 175,321.00 (mediana 1.77) | não (5.8% nulo) | `derivado` · T2 mais T4 |
| `peso_bruto_t` | numérico | Peso bruto movimentado na atracação | esperado entre 0 e 1,000,000 | 0.00 até 419,507.66 (mediana 1,806.89) | sim | `Carga.txt / VLPesoCargaBruta` · soma por IDAtracacao, itens autorizados |
| `teu` | numérico | Unidades equivalentes a vinte pés movimentadas | esperado entre 0 e 30,000 | 0.00 até 14,145.00 (mediana 0.00) | sim | `Carga.txt / TEU` · soma por IDAtracacao |
| `qtd_itens_carga` | inteiro | Número de registros de carga da atracação | esperado entre 0 e 50,000 | 0.00 até 7,292.00 (mediana 1.00) | sim | `Carga.txt / IDCarga` · contagem por IDAtracacao |
| `prancha_operacional_th` | numérico | Produtividade durante a operação | esperado entre 0 e 20,000 | 0.00 até 2,705,674.00 (mediana 416.86) | não (19.0% nulo) | `derivado` · peso bruto dividido por T3 |
| `prancha_geral_th` | numérico | Produtividade considerando todo o tempo atracado | esperado entre 0 e 20,000 | 0.00 até 100,022.91 (mediana 265.86) | não (19.0% nulo) | `derivado` · peso bruto dividido por TA |
| `flag_cronologia_invalida` | booleano | Marca registro cuja sequência de datas é impossível | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · algum tempo negativo |
| `flag_operacao_ausente` | booleano | Marca registro sem data de início ou término de operação | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · teste de nulo |
| `flag_estadia_outlier` | booleano | Marca estadia acima de 30 dias | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · TE maior que 720 horas |
| `flag_sem_carga_declarada` | booleano | Marca atracação sem item de carga associado | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · ausência de correspondência em Carga.txt |
| `flag_atracacao_exclusiva` | texto | Atracação que movimentou um único perfil de carga | livre (identificador ou texto descritivo) | False; True | não (19.0% nulo) | `derivado` · contagem distinta de natureza igual a um |
| `flag_prancha_implausivel` | booleano | Marca prancha acima do limite de plausibilidade | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · prancha acima de 20000 t/h |
| `flag_fora_bbox` | booleano | Marca coordenada fora do território brasileiro | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · teste de caixa delimitadora |
| `flag_apto_analise_tempo` | booleano | Registro válido para análise de tempo | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · sem cronologia inválida, sem outlier e com TA definido |

## dim_instalacao

Linhas: **212**  ·  Atributos: **13**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_instalacao` | texto | Código da instalação portuária | livre (identificador ou texto descritivo) | 212 valores distintos (ex.: BR, BRADR, BRAL001) | sim | `Atracacao.txt / CDTUP` · chave primaria |
| `porto_atracacao` | texto | Nome do porto ou terminal | livre (identificador ou texto descritivo) | 211 valores distintos (ex.: ABI Miritituba, AIVEL, ATEM Belém-PA) | não (0.5% nulo) | `Atracacao.txt / Porto Atracação` · último valor observado no ano |
| `complexo_portuario` | texto | Complexo portuário, agrupamento territorial da ANTAQ | livre (identificador ou texto descritivo) | 42 valores distintos (ex.: Almeirim, Angra dos Reis, Aracajú) | sim | `Atracacao.txt / Complexo Portuário` · último valor observado |
| `apelido_instalacao` | texto | Apelido da instalação | livre (identificador ou texto descritivo) | 68 valores distintos (ex.: ATR Logística - Chibatão, Almirante Tamandaré, Amaggi Portochuelo) | não (67.9% nulo) | `Atracacao.txt / Apelido Instalação Portuária` · último valor observado |
| `tipo_autoridade` | texto | Porto organizado ou terminal autorizado | esperado em: Porto Organizado; Terminal Autorizado | Porto Organizado; Terminal Autorizado | sim | `Atracacao.txt / Tipo da Autoridade Portuária` · último valor observado |
| `municipio` | texto | Município da instalação | livre (identificador ou texto descritivo) | 78 valores distintos (ex.: Almeirim, Ananindeua, Anchieta) | não (0.5% nulo) | `Atracacao.txt / Município` · último valor observado |
| `uf` | texto | Unidade da federação por extenso | livre (identificador ou texto descritivo) | 20 valores distintos (ex.: Alagoas, Amapá, Amazonas) | não (0.5% nulo) | `Atracacao.txt / UF` · último valor observado |
| `sguf` | texto | Sigla da unidade da federação | esperado em: 27 categorias válidas | 20 valores distintos (ex.: AL, AM, AP) | não (0.5% nulo) | `Atracacao.txt / SGUF` · último valor observado |
| `regiao_geografica` | texto | Região geográfica do IBGE | esperado em: Norte; Nordeste; Sudeste; Sul; Centro-Oeste | Centro-Oeste; Nordeste; Norte; Sudeste; Sul | não (0.5% nulo) | `Atracacao.txt / Região Geográfica` · último valor observado |
| `regiao_hidrografica` | texto | Região hidrográfica, preenchida para instalações fluviais | livre (identificador ou texto descritivo) |   Paraguai;   Paraná;   Tocantins-Araguaia;  Amazônica;  Atlântico Sul | não (52.4% nulo) | `Atracacao.txt / Região Hidrográfica` · último valor observado |
| `instalacao_em_rio` | texto | Indica instalação fluvial | esperado em: Sim; Não | Não; Sim | sim | `Atracacao.txt / Instalação Portuária em Rio` · último valor observado |
| `latitude` | numérico | Latitude da instalação | esperado entre -35.0 e 6.0 | -32.10 até -0.06 (mediana -12.81) | não (0.5% nulo) | `Atracacao.txt / Coordenadas` · segundo elemento após separação por vírgula |
| `longitude` | numérico | Longitude da instalação | esperado entre -75.0 e -28.0 | -63.92 até -34.84 (mediana -48.65) | não (0.5% nulo) | `Atracacao.txt / Coordenadas` · primeiro elemento após separação por vírgula |

## dim_berco

Linhas: **625**  ·  Atributos: **3**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_berco` | texto | Código do berço | livre (identificador ou texto descritivo) | 625 valores distintos (ex.: ADR3101, ADR3102, ANT0113) | sim | `Atracacao.txt / IDBerco` · chave primaria |
| `berco` | texto | Identificação do berço declarada pela instalação | livre (identificador ou texto descritivo) | 501 valores distintos (ex.: 001, 002, 01) | sim | `Atracacao.txt / Berço` · último valor observado |
| `sk_instalacao` | texto | Instalação a que o berço pertence | livre (identificador ou texto descritivo) | 211 valores distintos (ex.: BRADR, BRAL001, BRAM001) | sim | `Atracacao.txt / CDTUP` · FK para dim_instalacao |

## dim_tempo

Linhas: **365**  ·  Atributos: **8**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_data` | data | Data de desatracação | livre (identificador ou texto descritivo) | 2025-01-01 até 2025-12-31 | sim | `derivado` · chave primaria |
| `ano` | inteiro | Ano | esperado entre 2,025 e 2,025 | 2,025.00 até 2,025.00 (mediana 2,025.00) | sim | `derivado` · extraído de sk_data |
| `mes` | inteiro | Mes | esperado entre 1 e 12 | 1.00 até 12.00 (mediana 7.00) | sim | `derivado` · extraído de sk_data |
| `nome_mes` | texto | Competência no formato AAAA-MM | livre (identificador ou texto descritivo) | 12 valores distintos (ex.: 2025-01, 2025-02, 2025-03) | sim | `derivado` · extraído de sk_data |
| `trimestre` | inteiro | Trimestre | esperado entre 1 e 4 | 1.00 até 4.00 (mediana 3.00) | sim | `derivado` · extraído de sk_data |
| `semestre` | inteiro | Semestre | esperado entre 1 e 2 | 1.00 até 2.00 (mediana 2.00) | sim | `derivado` · extraído de sk_data |
| `dia_semana` | inteiro | Dia da semana, zero igual a segunda | esperado entre 0 e 6 | 0.00 até 6.00 (mediana 3.00) | sim | `derivado` · extraído de sk_data |
| `fim_de_semana` | booleano | Indica sábado ou domingo | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · dia_semana maior ou igual a cinco |

## dim_navegacao

Linhas: **35**  ·  Atributos: **4**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_navegacao` | inteiro | Chave sintética | livre (identificador ou texto descritivo) | 1.00 até 35.00 (mediana 18.00) | sim | `derivado` · chave primaria |
| `tipo_navegacao` | texto | Modo de navegação da atracação | esperado em: Interior; Longo Curso; Cabotagem; Apoio Marítimo; Apoio Portuário | Apoio Marítimo; Apoio Portuário; Cabotagem; Interior; Longo Curso | sim | `Atracacao.txt / Tipo de Navegação da Atracação` · cópia direta |
| `tipo_operacao` | texto | Finalidade da atracação | esperado em: Movimentação da Carga; Apoio; Passageiro; Abastecimento; Reparo/Manutenção; Misto; Marinha; Retirada de Resíduos | Abastecimento; Apoio; Marinha; Misto; Movimentação da Carga; Passageiro; Reparo/Manutenção; Retirada de Resíduos | sim | `Atracacao.txt / Tipo de Operação` · cópia direta |
| `operacao_produtiva` | booleano | Indica atracação que movimenta carga | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · tipo de operação em lista de referência |

## dim_natureza_carga

Linhas: **5**  ·  Atributos: **3**

| Atributo | Tipo | Descrição | Domínio esperado | Domínio observado | Obrigatório | Linhagem |
|---|---|---|---|---|---|---|
| `sk_natureza` | inteiro | Chave sintética | livre (identificador ou texto descritivo) | 1.00 até 5.00 (mediana 3.00) | sim | `derivado` · chave primaria |
| `natureza_carga` | texto | Natureza da carga | esperado em: Carga Conteinerizada; Carga Geral; Granel Sólido; Granel Líquido e Gasoso; Sem carga declarada | Carga Conteinerizada; Carga Geral; Granel Líquido e Gasoso; Granel Sólido; Sem carga declarada | sim | `Carga.txt / Natureza da Carga` · cópia direta mais categoria para ausencia |
| `granel` | booleano | Indica carga a granel | livre (identificador ou texto descritivo) | verdadeiro ou falso | sim | `derivado` · prefixo do nome da natureza |

## Regras de negócio aplicadas na transformação

1. **Definição dos tempos.** T1 é a diferença entre atracação e chegada; T2 entre início de operação e atracação; T3 entre término e início de operação; T4 entre desatracação e término de operação. As definições seguem a Documentação do Estatístico Aquaviário da ANTAQ.
2. **Filtro de autorização na carga.** Só entram no cálculo de peso e TEU os itens com `FlagAutorizacao = S` e `FlagMCOperacaoCarga = 1`, que são os registros validados pela agência. Isso reduziu 2.467.854 itens para 2.294.271.
3. **Conciliação de grão.** A tabela de carga tem vários itens por atracação. Os itens são agregados por `IDAtracacao` antes da junção, caso contrário a tabela fato duplicaria atracações.
4. **Natureza predominante.** Quando uma atracação movimenta mais de um perfil de carga, prevalece o de maior peso bruto. O caso de perfil único é marcado em `flag_atracacao_exclusiva`, seguindo a definição de atracação exclusiva da ANTAQ.
5. **Valores ausentes não são imputados.** A ausência é marcada em coluna própria para que possa ser medida como indicador de qualidade, em vez de ficar oculta sob um valor substituto.
6. **Registros inválidos não são excluídos.** São marcados por flags, de modo que cada análise declare explicitamente qual subconjunto utilizou.
7. **Convenção temporal.** Atributos de tempo usam a data de desatracação, conforme convenção da própria ANTAQ.