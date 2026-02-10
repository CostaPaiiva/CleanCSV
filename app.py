# Importa a biblioteca Streamlit para criar a interface web
import streamlit as st
# Importa a biblioteca pandas para manipulação de dados em DataFrames
import pandas as pd
# Importa a biblioteca numpy para operações numéricas, embora não explicitamente usada na seleção, é comum com pandas
import numpy as np
# Importa o módulo io para trabalhar com fluxos de bytes/arquivos em memória
import io
# Importa o módulo re para expressões regulares, usado em funções de utilidade
import re
# Importa a biblioteca chardet para detecção de codificação de arquivos
import chardet
# Importa o parser de data da biblioteca dateutil para análise flexível de datas
from dateutil import parser

# Configurações iniciais da página Streamlit, como título e layout
st.set_page_config(page_title="Limpeza de Dados CSV", layout="wide")


# Utilitários


# Define uma função para detectar a codificação de um arquivo a partir de seus bytes
def detect_encoding(file_bytes: bytes) -> str:
    # Usa a biblioteca chardet para detectar a codificação dos bytes do arquivo
    result = chardet.detect(file_bytes)
    # Extrai a codificação do resultado, ou assume "utf-8" se não for detectada
    enc = result.get("encoding") or "utf-8"
    # Retorna a codificação detectada ou padrão
    return enc

# Define uma função para normalizar o nome de uma coluna
def normalize_colname(name: str) -> str:
    # Importa a biblioteca re para expressões regulares (já importada no topo, mas re-importada aqui localmente)
    import re
    # Converte o nome para string, remove espaços extras no início/fim e converte para minúsculas
    name = str(name).strip().lower()
    # Substitui um ou mais espaços por um único underscore
    name = re.sub(r"\s+", "_", name)
    # Remove todos os caracteres que não são letras, números ou underscores
    name = re.sub(r"[^\w_]", "", name)
    # Substitui múltiplos underscores consecutivos por um único underscore e remove underscores no início/fim
    name = re.sub(r"_+", "_", name).strip("_")
    # Se o nome resultar em uma string vazia após a normalização, define como "col"
    if name == "":
        name = "col"
    # Retorna o nome da coluna normalizado
    return name



# Define uma função chamada make_unique que recebe uma lista de nomes
def make_unique(names):
    """Garante nomes únicos: a, a_2, a_3...""" # Docstring: explica o propósito da função
    seen = {} # Inicializa um dicionário vazio para armazenar a contagem de cada nome
    out = [] # Inicializa uma lista vazia para armazenar os nomes únicos resultantes
    # Itera sobre cada nome na lista de nomes de entrada
    for n in names:
        # Verifica se o nome atual ainda não foi visto (não está no dicionário seen)
        if n not in seen:
            seen[n] = 1 # Se não foi visto, adiciona-o ao dicionário com contagem 1
            out.append(n) # Adiciona o nome original à lista de saída
        # Se o nome já foi visto
        else:
            seen[n] += 1 # Incrementa a contagem desse nome no dicionário
            out.append(f"{n}_{seen[n]}") # Adiciona o nome com um sufixo numérico (ex: "nome_2") à lista de saída
    return out # Retorna a lista de nomes únicos

def try_parse_datetime(series: pd.Series, sample_size=200) -> bool:
    # Define uma função para tentar inferir se uma série Pandas contém datas
    # A função recebe uma série Pandas e um tamanho de amostra (padrão 200)
    # E retorna True se uma alta porcentagem da amostra for convertível para data, False caso contrário

    # Extrai valores não nulos da série e converte-os para string
    s = series.dropna().astype(str)
    # Se a série resultante estiver vazia após remover nulos, não há o que verificar, retorna False
    if s.empty:
        return False
    # Seleciona uma amostra aleatória dos valores (ou todos se o tamanho da série for menor que sample_size)
    # O random_state garante reprodutibilidade da amostra
    s = s.sample(min(sample_size, len(s)), random_state=42)
    # Inicializa um contador para o número de valores que puderam ser parseados como data
    ok = 0
    # Itera sobre cada valor na amostra
    for v in s:
        try:
            # Tenta fazer o parse do valor para datetime usando o parser flexível da dateutil
            # fuzzy=True permite ignorar partes da string que não são datas (ex: "relatório 2023-01-01")
            _ = parser.parse(v, fuzzy=True)
            # Se o parse for bem-sucedido, incrementa o contador 'ok'
            ok += 1
        except Exception:
            # Se ocorrer um erro ao tentar o parse (o valor não é uma data válida), ignora
            pass
    # Retorna True se pelo menos 70% (0.7) dos valores da amostra puderam ser parseados como data, caso contrário False
    return (ok / len(s)) >= 0.7

# Define uma função chamada to_datetime_safe que recebe uma série Pandas
def to_datetime_safe(series: pd.Series) -> pd.Series:
    # Tenta converter a série para o tipo datetime do Pandas
    # errors="coerce" fará com que valores que não podem ser convertidos se tornem NaT (Not a Time)
    # infer_datetime_format=True permite que o Pandas tente inferir o formato da data para uma conversão mais rápida
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)

def coerce_numeric(series: pd.Series) -> pd.Series:
    # tenta converter removendo separadores comuns
    s = series.astype(str).str.strip()
    # troca vírgula decimal por ponto quando parece numérico
    s = s.str.replace(".", "", regex=False)  # remove separador de milhar comum (.)
    s = s.str.replace(",", ".", regex=False)  # decimal vírgula -> ponto
    return pd.to_numeric(s, errors="coerce")

# Define uma função chamada download_button_csv que recebe um DataFrame, um nome de arquivo e um separador
def download_button_csv(df: pd.DataFrame, filename="dados_tratados.csv", sep=";"):
    # Converte o DataFrame para uma string CSV, sem o índice, usando o separador especificado, e codifica para bytes com BOM (para Excel)
    csv_bytes = df.to_csv(index=False, sep=sep).encode("utf-8-sig")  # <- utf-8-sig pro Excel
    # Cria um botão de download no Streamlit
    st.download_button(
        "⬇️ Baixar CSV tratado (Excel)", # Texto exibido no botão
        data=csv_bytes,                 # Dados a serem baixados
        file_name=filename,             # Nome do arquivo quando baixado
        mime="text/csv",                # Tipo MIME do arquivo
        use_container_width=True        # O botão ocupa a largura total do contêiner
    )


# Define uma função chamada df_info_summary que recebe um DataFrame e retorna um novo DataFrame com um resumo das colunas
def df_info_summary(df: pd.DataFrame) -> pd.DataFrame:
    # Retorna um novo DataFrame com informações sumarizadas de cada coluna do DataFrame de entrada
    return pd.DataFrame({
        "coluna": df.columns,                                       # Lista os nomes das colunas
        "dtype": [str(df[c].dtype) for c in df.columns],            # Lista os tipos de dados de cada coluna (como string)
        "nulos": [int(df[c].isna().sum()) for c in df.columns],     # Conta o número de valores nulos em cada coluna
        "percent_nulos": [float(df[c].isna().mean() * 100) for c in df.columns], # Calcula o percentual de nulos em cada coluna
        "unicos": [int(df[c].nunique(dropna=True)) for c in df.columns], # Conta o número de valores únicos (ignorando nulos) em cada coluna
    })


# Estado

# Verifica se a chave 'df_original' não existe no st.session_state (estado da sessão do Streamlit)
if "df_original" not in st.session_state:
    # Se não existir, inicializa 'df_original' como None no estado da sessão
    st.session_state.df_original = None
# Verifica se a chave 'df' não existe no st.session_state
if "df" not in st.session_state:
    # Se não existir, inicializa 'df' como None no estado da sessão (este será o DataFrame atual modificado)
    st.session_state.df = None
# Verifica se a chave 'log' não existe no st.session_state
if "log" not in st.session_state:
    # Se não existir, inicializa 'log' como uma lista vazia no estado da sessão (para registrar as ações)
    st.session_state.log = []

# Define uma função chamada 'log_step' que aceita uma mensagem (string)
def log_step(msg: str):
    # Adiciona a mensagem fornecida à lista 'log' no estado da sessão
    st.session_state.log.append(msg)


# UI

# Define o título principal da aplicação Streamlit
st.title("🧼 Limpeza de Dados (CSV)")
# Adiciona uma pequena descrição/legenda abaixo do título
st.caption("Upload → Diagnóstico → Limpeza em etapas → Download do CSV tratado")

# Inicia um bloco de código que será renderizado na barra lateral do Streamlit
with st.sidebar:
    # Adiciona um cabeçalho para a seção de upload na barra lateral
    st.header("📥 Upload")
    # Cria um widget de upload de arquivo para arquivos CSV
    uploaded = st.file_uploader("Selecione um arquivo CSV", type=["csv"])

    # Adiciona um divisor visual na barra lateral
    st.divider()
    # Adiciona um cabeçalho para a seção de configurações de leitura
    st.header("⚙️ Configurações de leitura")
    # Cria um seletor para o separador de colunas do CSV, com "," como padrão
    sep = st.selectbox("Separador", options=[",", ";", "\t", "|"], index=0)
    # Cria um seletor para o separador decimal (apenas para referência na UI, não afeta leitura diretamente aqui)
    decimal = st.selectbox("Decimal (apenas referência)", options=[".", ","], index=0)
    # Cria uma caixa de seleção para indicar se o CSV tem cabeçalho, marcada como verdadeira por padrão
    has_header = st.checkbox("Arquivo tem cabeçalho?", value=True)
    # Cria um campo de texto para o usuário inserir valores a serem considerados como NA (Not Applicable/Nulo)
    na_values_text = st.text_input("Valores para considerar como NA (separe por vírgula)", "NA,NaN,null,NULL,")
    # Processa a string de NA_values para criar uma lista de strings, removendo espaços e entradas vazias
    na_values = [x.strip() for x in na_values_text.split(",") if x.strip() != ""]
    # Adiciona outro divisor visual na barra lateral
    st.divider()

    # Cria um botão "Resetar tudo" na barra lateral
    if st.button("🔄 Resetar tudo", use_container_width=True):
        # Quando clicado, redefine o DataFrame original para None no estado da sessão
        st.session_state.df_original = None
        # Redefine o DataFrame atual para None no estado da sessão
        st.session_state.df = None
        # Limpa o log de ações no estado da sessão
        st.session_state.log = []
        # Força o Streamlit a reroduzir o script desde o início, limpando a UI e o estado
        st.rerun()


# Carregar CSV

# Verifica se um arquivo foi carregado (uploaded é diferente de None) E se o DataFrame atual ainda não foi carregado na sessão
if uploaded is not None and st.session_state.df is None:
    # Obtém o conteúdo do arquivo carregado como bytes
    file_bytes = uploaded.getvalue()
    # Detecta a codificação do arquivo usando a função 'detect_encoding'
    enc = detect_encoding(file_bytes)

    try:
        # Tenta ler o arquivo CSV usando pandas.read_csv
        df = pd.read_csv(
            # Cria um fluxo de bytes em memória a partir dos bytes do arquivo
            io.BytesIO(file_bytes),
            # Define o separador de colunas conforme selecionado na UI
            sep=sep,
            # Define a codificação detectada
            encoding=enc,
            # Define o cabeçalho: 0 se 'has_header' for True, None caso contrário
            header=0 if has_header else None,
            # Define os valores a serem considerados como NA (nulos)
            na_values=na_values
        )
    except Exception:
        # Em caso de erro na leitura com a codificação detectada, tenta um fallback simples
        df = pd.read_csv(
            # Cria um fluxo de bytes em memória a partir dos bytes do arquivo
            io.BytesIO(file_bytes),
            # Define o separador de colunas conforme selecionado na UI
            sep=sep,
            # Usa "utf-8" como codificação de fallback
            encoding="utf-8",
            # Define o cabeçalho: 0 se 'has_header' for True, None caso contrário
            header=0 if has_header else None,
            # Define os valores a serem considerados como NA (nulos)
            na_values=na_values
        )

    # Se o arquivo não tiver cabeçalho (has_header é False)
    if not has_header:
        # Atribui nomes de coluna genéricos (ex: "col_0", "col_1")
        df.columns = [f"col_{i}" for i in range(df.shape[1])]

    # Armazena uma cópia do DataFrame original no estado da sessão
    st.session_state.df_original = df.copy()
    # Armazena uma cópia do DataFrame atual (que será modificado) no estado da sessão
    st.session_state.df = df.copy()
    # Reinicia o log de ações
    st.session_state.log = []
    # Registra a ação de carregamento do arquivo no log
    log_step(f"Arquivo carregado com {df.shape[0]} linhas e {df.shape[1]} colunas. (encoding detectado: {enc})")

# Atribui o DataFrame atual da sessão (st.session_state.df) à variável local 'df'
df = st.session_state.df

# Verifica se o DataFrame 'df' é None (o que significa que nenhum arquivo foi carregado ainda)
if df is None:
    # Exibe uma mensagem informativa na interface do Streamlit
    st.info("Faça o upload de um CSV na barra lateral para começar.")
    # Interrompe a execução do script Streamlit neste ponto, aguardando o upload do arquivo
    st.stop()


# Visão geral

# Cria duas colunas na interface do Streamlit, com proporções de largura 2 para 1 e um espaçamento "large"
colA, colB = st.columns([2, 1], gap="large")

# Inicia um bloco de código que será renderizado na primeira coluna (colA)
with colA:
    # Adiciona um subtítulo à coluna
    st.subheader("Prévia do dataset")
    # Exibe uma prévia das primeiras 50 linhas do DataFrame 'df' em um widget de tabela, usando a largura total do contêiner
    st.dataframe(df.head(50), use_container_width=True)

# Inicia um bloco de código que será renderizado na segunda coluna (colB)
with colB:
    # Adiciona um subtítulo à coluna
    st.subheader("📊 Resumo")
    # Exibe o número de linhas do DataFrame
    st.write(f"**Linhas:** {df.shape[0]}")
    # Exibe o número de colunas do DataFrame
    st.write(f"**Colunas:** {df.shape[1]}")
    # Exibe o número de linhas duplicadas no DataFrame (convertido para inteiro)
    st.write(f"**Duplicadas (linhas):** {int(df.duplicated().sum())}")
    # Exibe o número total de células nulas em todo o DataFrame (convertido para inteiro)
    st.write(f"**Células nulas (total):** {int(df.isna().sum().sum())}")
    # Adiciona uma linha vazia para espaçamento visual
    st.write("")
    # Adiciona uma legenda para a tabela de resumo por coluna
    st.caption("Detalhe por coluna:")
    # Exibe um DataFrame com um resumo detalhado por coluna (criado pela função df_info_summary)
    # usando a largura total do contêiner e com altura fixa de 260 pixels
    st.dataframe(df_info_summary(df), use_container_width=True, height=260)

# Adiciona um divisor visual horizontal na interface do Streamlit
st.divider()

# Etapas (Acordeões)

# 1) Padronizar nomes de colunas
with st.expander("1) 🏷️ Padronizar nomes de colunas", expanded=False):
    # Exibe uma mensagem de sugestão para o usuário sobre como padronizar nomes de colunas
    st.write("Sugestão: remover espaços, padronizar para minúsculas e trocar espaços por `_`.")
    # Cria um DataFrame temporário para pré-visualizar a mudança dos nomes das colunas
    preview_cols = pd.DataFrame({
        # Coluna "antes" mostra os nomes atuais das colunas do DataFrame
        "antes": st.session_state.df.columns,
        # Coluna "depois" mostra como os nomes ficariam após a normalização usando a função normalize_colname
        "depois": [normalize_colname(c) for c in st.session_state.df.columns]
    })
    # Exibe o DataFrame de pré-visualização na interface do Streamlit, ocupando a largura total do contêiner
    st.dataframe(preview_cols, use_container_width=True)

    # Calcula o número de nomes de coluna que se tornariam duplicados após a normalização
    dups = pd.Series([normalize_colname(c) for c in df.columns]).duplicated().sum()
    # Exibe o número de possíveis nomes duplicados que serão tratados pela função make_unique
    st.write(f"Possíveis nomes duplicados após padronizar: **{int(dups)}**")

    # Cria um botão para aplicar a padronização dos nomes das colunas
    if st.button("Aplicar padronização de nomes", key="apply_colnames"):
        # Armazena os nomes das colunas atuais em uma lista
        old_cols = list(df.columns)
        # Gera uma nova lista de nomes de colunas padronizados usando a função normalize_colname
        new_cols = [normalize_colname(c) for c in old_cols]
        # Garante que os novos nomes de colunas sejam únicos, adicionando sufixos se necessário (ex: "col_2")
        new_cols = make_unique(new_cols)

        # Cria uma cópia do DataFrame para evitar modificar o DataFrame original diretamente em caso de re-execução
        df = df.copy()
        # Atribui os novos nomes padronizados e únicos às colunas do DataFrame
        df.columns = new_cols
        # Atualiza o DataFrame na sessão do Streamlit com as colunas renomeadas
        st.session_state.df = df

        # Registra a ação no log de passos
        log_step("Nomes de colunas padronizados e tornados únicos.")
        # Exibe uma mensagem de sucesso para o usuário
        st.success("Aplicado!")
        # Força o Streamlit a reroduzir o script para atualizar a interface com os novos nomes de colunas
        st.rerun()


# 2) Remover espaços extras em textos
with st.expander("2) ✂️ Limpar textos (trim, espaços duplicados)", expanded=False):
    # Filtra as colunas do DataFrame que possuem o tipo de dado 'object' (geralmente strings/textos)
    text_cols = [c for c in df.columns if df[c].dtype == "object"]
    # Cria um multiselect no Streamlit para o usuário selecionar quais colunas de texto aplicar a limpeza
    # Por padrão, pré-seleciona as primeiras 10 colunas de texto (ou todas se houver menos de 10)
    selected = st.multiselect("Selecione colunas de texto", options=text_cols, default=text_cols[:10])
    # Cria uma caixa de seleção para permitir ao usuário decidir se deseja substituir múltiplos espaços por um único
    replace_multi_space = st.checkbox("Trocar múltiplos espaços por 1 espaço", value=True)
    # Cria um botão para aplicar as operações de limpeza de texto
    if st.button("Aplicar limpeza de texto", key="apply_text"):
        # Itera sobre cada coluna selecionada pelo usuário para aplicar a limpeza
        for c in selected:
            # Converte a coluna para o tipo de string do pandas (permite valores nulos)
            s = df[c].astype("string")
            # Remove espaços em branco do início e do fim de cada string na série
            s = s.str.strip()
            # Verifica se a opção de substituir múltiplos espaços foi selecionada
            if replace_multi_space:
                # Substitui um ou mais espaços consecutivos por um único espaço
                s = s.str.replace(r"\s+", " ", regex=True)
            # Atualiza a coluna original no DataFrame com a série de strings limpa
            df[c] = s
        # Atualiza o DataFrame na sessão do Streamlit com as alterações
        st.session_state.df = df
        # Registra a ação de limpeza de texto no log de passos
        log_step(f"Limpeza de texto aplicada em {len(selected)} colunas (strip + normalização de espaços).")
        # Exibe uma mensagem de sucesso para o usuário
        st.success("Aplicado!")

# 3) Tipagem automática (datas e números)
with st.expander("3) 🔢 Tipagem automática (detectar datas e números)", expanded=False):
    # Exibe uma mensagem informativa para o usuário sobre o propósito desta seção.
    st.write("Converte colunas `object` que parecem números/datas.")
    # Cria uma caixa de seleção para permitir ao usuário decidir se tenta converter colunas para números.
    # O valor padrão é True (marcado).
    convert_numbers = st.checkbox("Tentar converter números (ex: '1.234,56')", value=True)
    # Cria uma caixa de seleção para permitir ao usuário decidir se tenta converter colunas para datas.
    # O valor padrão é True (marcado).
    convert_dates = st.checkbox("Tentar converter datas", value=True)

    # Cria um botão para aplicar as operações de tipagem automática.
    if st.button("Aplicar tipagem automática", key="apply_types"):
        # Inicializa um contador para o número de colunas cujo tipo de dado foi alterado.
        changed = 0

        # Bloco de código para tentar converter colunas para números.
        # Verifica se o usuário optou por converter números.
        if convert_numbers:
            # Itera sobre cada coluna no DataFrame.
            for c in df.columns:
                # Verifica se o tipo de dado da coluna atual é 'object' (geralmente strings).
                if df[c].dtype == "object":
                    # Tenta converter a coluna para um tipo numérico usando a função `coerce_numeric`.
                    converted = coerce_numeric(df[c])
                    # Calcula o número de valores não nulos na coluna original.
                    non_null = df[c].notna().sum()
                    # Verifica se há valores não nulos na coluna.
                    if non_null > 0:
                        # Calcula a proporção de valores que foram convertidos com sucesso para numéricos (não nulos na série convertida)
                        # em relação aos valores não nulos da série original.
                        ratio = converted.notna().sum() / non_null
                        # Se a proporção for 70% ou mais (o que significa que a maioria dos valores é numérica),
                        # aplica a conversão ao DataFrame.
                        if ratio >= 0.7:
                            # Atualiza a coluna no DataFrame com a série numérica convertida.
                            df[c] = converted
                            # Incrementa o contador de colunas alteradas.
                            changed += 1

        # Bloco de código para tentar converter colunas para datas.
        # Verifica se o usuário optou por converter datas.
        if convert_dates:
            # Itera sobre cada coluna no DataFrame.
            for c in df.columns:
                # Verifica se o tipo de dado da coluna atual é 'object' (geralmente strings que podem conter datas).
                if df[c].dtype == "object":
                    # Tenta inferir se a coluna contém datas utilizando a função `try_parse_datetime`.
                    # Se `try_parse_datetime` retornar True, significa que a coluna provavelmente é de data.
                    # Se a função try_parse_datetime retornar True (indicando que a coluna parece conter datas)
                    if try_parse_datetime(df[c]):
                        # Tenta converter a coluna para o tipo datetime de forma segura, tratando erros
                        dt = to_datetime_safe(df[c])
                        # Verifica se a proporção de valores não nulos após a conversão para datetime é >= 70% dos valores não nulos originais
                        if dt.notna().sum() >= 0.7 * df[c].notna().sum():
                            # Atribui a série de datetime convertida de volta à coluna original no DataFrame
                            df[c] = dt
                            # Incrementa o contador de colunas alteradas com sucesso
                            changed += 1


        # Atualiza o DataFrame na sessão do Streamlit com as alterações de tipagem.
        st.session_state.df = df
        # Registra a ação de tipagem automática no log, indicando quantas colunas foram alteradas.
        log_step(f"Tipagem automática aplicada. Colunas convertidas: {changed}.")
        # Exibe uma mensagem de sucesso na interface do Streamlit, mostrando o número de colunas convertidas.
        st.success(f"Aplicado! Colunas convertidas: {changed}")

# 4) Duplicadas
with st.expander("4) 🧩 Remover linhas duplicadas", expanded=False):
    dups = int(df.duplicated().sum())
    st.write(f"Duplicadas detectadas: **{dups}**")
    keep = st.selectbox("Manter qual ocorrência?", options=["first", "last"], index=0)
    if st.button("Remover duplicadas", key="apply_dups", disabled=(dups == 0)):
        before = df.shape[0]
        df = df.drop_duplicates(keep=keep)
        st.session_state.df = df
        log_step(f"Linhas duplicadas removidas (keep='{keep}'). {before - df.shape[0]} linhas removidas.")
        st.success("Aplicado!")

# 5) Valores nulos
with st.expander("5) 🕳️ Tratamento de valores nulos", expanded=False):
    st.write("Escolha uma estratégia por tipo de coluna.")
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])]
    dt_cols  = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    st.markdown("**Numéricas:**")
    num_strategy = st.selectbox("Estratégia (numéricas)", ["Não mexer", "Remover linhas com NA", "Preencher com 0", "Preencher com média", "Preencher com mediana"], index=0)
    num_sel = st.multiselect("Colunas numéricas", options=num_cols, default=num_cols)

    st.markdown("**Categóricas/Textos:**")
    cat_strategy = st.selectbox("Estratégia (categóricas)", ["Não mexer", "Remover linhas com NA", "Preencher com 'DESCONHECIDO'", "Preencher com moda (mais frequente)"], index=0)
    cat_sel = st.multiselect("Colunas categóricas", options=cat_cols, default=cat_cols)

    st.markdown("**Datas:**")
    dt_strategy = st.selectbox("Estratégia (datas)", ["Não mexer", "Remover linhas com NA", "Preencher com data mínima", "Preencher com data máxima"], index=0)
    dt_sel = st.multiselect("Colunas datetime", options=dt_cols, default=dt_cols)

    if st.button("Aplicar tratamento de nulos", key="apply_na"):
        before = df.shape[0]

        # numéricas
        if num_strategy != "Não mexer" and len(num_sel) > 0:
            if num_strategy == "Remover linhas com NA":
                df = df.dropna(subset=num_sel)
            else:
                for c in num_sel:
                    if num_strategy == "Preencher com 0":
                        df[c] = df[c].fillna(0)
                    elif num_strategy == "Preencher com média":
                        df[c] = df[c].fillna(df[c].mean())
                    elif num_strategy == "Preencher com mediana":
                        df[c] = df[c].fillna(df[c].median())

        # categóricas
        if cat_strategy != "Não mexer" and len(cat_sel) > 0:
            if cat_strategy == "Remover linhas com NA":
                df = df.dropna(subset=cat_sel)
            else:
                for c in cat_sel:
                    if cat_strategy == "Preencher com 'DESCONHECIDO'":
                        df[c] = df[c].fillna("DESCONHECIDO")
                    elif cat_strategy == "Preencher com moda (mais frequente)":
                        moda = df[c].mode(dropna=True)
                        fill = moda.iloc[0] if len(moda) else "DESCONHECIDO"
                        df[c] = df[c].fillna(fill)

        # datas
        if dt_strategy != "Não mexer" and len(dt_sel) > 0:
            if dt_strategy == "Remover linhas com NA":
                df = df.dropna(subset=dt_sel)
            else:
                for c in dt_sel:
                    if dt_strategy == "Preencher com data mínima":
                        if df[c].dropna().empty:
                            continue
                        df[c] = df[c].fillna(df[c].min())
                    elif dt_strategy == "Preencher com data máxima":
                        if df[c].dropna().empty:
                            continue
                        df[c] = df[c].fillna(df[c].max())

        st.session_state.df = df
        removed = before - df.shape[0]
        log_step(f"Tratamento de nulos aplicado. Linhas removidas: {removed}.")
        st.success(f"Aplicado! Linhas removidas: {removed}")

# 6) Outliers (opcional)
with st.expander("6) 📉 Outliers (IQR) - opcional", expanded=False):
    st.write("Remove linhas com outliers em colunas numéricas usando IQR (Q1-1.5*IQR, Q3+1.5*IQR).")
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cols_out = st.multiselect("Colunas para avaliar outliers", options=num_cols, default=[])
    iqr_factor = st.slider("Fator IQR", min_value=1.0, max_value=3.0, value=1.5, step=0.1)

    if st.button("Remover outliers", key="apply_outliers", disabled=(len(cols_out) == 0)):
        before = df.shape[0]
        mask = pd.Series(True, index=df.index)
        for c in cols_out:
            s = df[c]
            q1 = s.quantile(0.25)
            q3 = s.quantile(0.75)
            iqr = q3 - q1
            low = q1 - iqr_factor * iqr
            high = q3 + iqr_factor * iqr
            mask &= s.between(low, high) | s.isna()
        df = df[mask].copy()
        st.session_state.df = df
        removed = before - df.shape[0]
        log_step(f"Outliers removidos por IQR em {len(cols_out)} colunas. Linhas removidas: {removed}.")
        st.success(f"Aplicado! Linhas removidas: {removed}")

# 7) Remover colunas (opcional)
with st.expander("7) 🧹 Remover colunas desnecessárias - opcional", expanded=False):
    drop_cols = st.multiselect("Selecione colunas para remover", options=list(df.columns), default=[])
    if st.button("Remover colunas selecionadas", key="apply_dropcols", disabled=(len(drop_cols) == 0)):
        df = df.drop(columns=drop_cols, errors="ignore")
        st.session_state.df = df
        log_step(f"Colunas removidas: {drop_cols}")
        st.success("Aplicado!")

st.divider()

# ---------------------------
# Log e Download final
# ---------------------------
left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("🧾 Log do que foi feito")
    if len(st.session_state.log) == 0:
        st.info("Nenhuma etapa aplicada ainda.")
    else:
        for i, msg in enumerate(st.session_state.log, start=1):
            st.write(f"{i}. {msg}")

with right:
    st.subheader("✅ Exportar")
    nome_saida = st.text_input("Nome do arquivo de saída", value="dados_tratados.csv")
    download_button_csv(st.session_state.df, filename=nome_saida, sep=";")


st.caption("Dica: se quiser voltar ao início, use **Resetar tudo** na barra lateral.")
