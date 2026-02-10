import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import chardet
from dateutil import parser

st.set_page_config(page_title="Limpeza de Dados CSV", layout="wide")

# ---------------------------
# Utilitários
# ---------------------------

def detect_encoding(file_bytes: bytes) -> str:
    result = chardet.detect(file_bytes)
    enc = result.get("encoding") or "utf-8"
    return enc

def normalize_colname(name: str) -> str:
    import re
    name = str(name).strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^\w_]", "", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if name == "":
        name = "col"
    return name


def make_unique(names):
    """Garante nomes únicos: a, a_2, a_3..."""
    seen = {}
    out = []
    for n in names:
        if n not in seen:
            seen[n] = 1
            out.append(n)
        else:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
    return out

def try_parse_datetime(series: pd.Series, sample_size=200) -> bool:
    # tentativa rápida e segura: checa se % alto vira datetime ao tentar parsear amostra
    s = series.dropna().astype(str)
    if s.empty:
        return False
    s = s.sample(min(sample_size, len(s)), random_state=42)
    ok = 0
    for v in s:
        try:
            _ = parser.parse(v, fuzzy=True)
            ok += 1
        except Exception:
            pass
    return (ok / len(s)) >= 0.7

def to_datetime_safe(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)

def coerce_numeric(series: pd.Series) -> pd.Series:
    # tenta converter removendo separadores comuns
    s = series.astype(str).str.strip()
    # troca vírgula decimal por ponto quando parece numérico
    s = s.str.replace(".", "", regex=False)  # remove separador de milhar comum (.)
    s = s.str.replace(",", ".", regex=False)  # decimal vírgula -> ponto
    return pd.to_numeric(s, errors="coerce")

def download_button_csv(df: pd.DataFrame, filename="dados_tratados.csv", sep=";"):
    csv_bytes = df.to_csv(index=False, sep=sep).encode("utf-8-sig")  # <- utf-8-sig pro Excel
    st.download_button(
        "⬇️ Baixar CSV tratado (Excel)",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True
    )


def df_info_summary(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "coluna": df.columns,
        "dtype": [str(df[c].dtype) for c in df.columns],
        "nulos": [int(df[c].isna().sum()) for c in df.columns],
        "percent_nulos": [float(df[c].isna().mean() * 100) for c in df.columns],
        "unicos": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })

# ---------------------------
# Estado
# ---------------------------
if "df_original" not in st.session_state:
    st.session_state.df_original = None
if "df" not in st.session_state:
    st.session_state.df = None
if "log" not in st.session_state:
    st.session_state.log = []

def log_step(msg: str):
    st.session_state.log.append(msg)

# ---------------------------
# UI
# ---------------------------
st.title("🧼 Limpeza de Dados (CSV)")
st.caption("Upload → Diagnóstico → Limpeza em etapas → Download do CSV tratado")

with st.sidebar:
    st.header("📥 Upload")
    uploaded = st.file_uploader("Selecione um arquivo CSV", type=["csv"])

    st.divider()
    st.header("⚙️ Configurações de leitura")
    sep = st.selectbox("Separador", options=[",", ";", "\t", "|"], index=0)
    decimal = st.selectbox("Decimal (apenas referência)", options=[".", ","], index=0)
    has_header = st.checkbox("Arquivo tem cabeçalho?", value=True)
    na_values_text = st.text_input("Valores para considerar como NA (separe por vírgula)", "NA,NaN,null,NULL,")
    na_values = [x.strip() for x in na_values_text.split(",") if x.strip() != ""]
    st.divider()

    if st.button("🔄 Resetar tudo", use_container_width=True):
        st.session_state.df_original = None
        st.session_state.df = None
        st.session_state.log = []
        st.rerun()

# ---------------------------
# Carregar CSV
# ---------------------------
if uploaded is not None and st.session_state.df is None:
    file_bytes = uploaded.getvalue()
    enc = detect_encoding(file_bytes)

    try:
        df = pd.read_csv(
            io.BytesIO(file_bytes),
            sep=sep,
            encoding=enc,
            header=0 if has_header else None,
            na_values=na_values
        )
    except Exception:
        # fallback simples
        df = pd.read_csv(
            io.BytesIO(file_bytes),
            sep=sep,
            encoding="utf-8",
            header=0 if has_header else None,
            na_values=na_values
        )

    if not has_header:
        df.columns = [f"col_{i}" for i in range(df.shape[1])]

    st.session_state.df_original = df.copy()
    st.session_state.df = df.copy()
    st.session_state.log = []
    log_step(f"Arquivo carregado com {df.shape[0]} linhas e {df.shape[1]} colunas. (encoding detectado: {enc})")

df = st.session_state.df

if df is None:
    st.info("Faça o upload de um CSV na barra lateral para começar.")
    st.stop()

# ---------------------------
# Visão geral
# ---------------------------
colA, colB = st.columns([2, 1], gap="large")

with colA:
    st.subheader("Prévia do dataset")
    st.dataframe(df.head(50), use_container_width=True)

with colB:
    st.subheader("📊 Resumo")
    st.write(f"**Linhas:** {df.shape[0]}")
    st.write(f"**Colunas:** {df.shape[1]}")
    st.write(f"**Duplicadas (linhas):** {int(df.duplicated().sum())}")
    st.write(f"**Células nulas (total):** {int(df.isna().sum().sum())}")
    st.write("")
    st.caption("Detalhe por coluna:")
    st.dataframe(df_info_summary(df), use_container_width=True, height=260)

st.divider()

# ---------------------------
# Etapas (Acordeões)
# ---------------------------

# 1) Padronizar nomes de colunas
with st.expander("1) 🏷️ Padronizar nomes de colunas", expanded=False):
    st.write("Sugestão: remover espaços, padronizar para minúsculas e trocar espaços por `_`.")
    preview_cols = pd.DataFrame({
        "antes": st.session_state.df.columns,
        "depois": [normalize_colname(c) for c in st.session_state.df.columns]
    })
    st.dataframe(preview_cols, use_container_width=True)
    
    dups = pd.Series([normalize_colname(c) for c in df.columns]).duplicated().sum()
    st.write(f"Possíveis nomes duplicados após padronizar: **{int(dups)}**")

    if st.button("Aplicar padronização de nomes", key="apply_colnames"):
        old_cols = list(df.columns)
        new_cols = [normalize_colname(c) for c in old_cols]
        new_cols = make_unique(new_cols)

        df = df.copy()
        df.columns = new_cols
        st.session_state.df = df

        log_step("Nomes de colunas padronizados e tornados únicos.")
        st.success("Aplicado!")
        st.rerun()


# 2) Remover espaços extras em textos
with st.expander("2) ✂️ Limpar textos (trim, espaços duplicados)", expanded=False):
    text_cols = [c for c in df.columns if df[c].dtype == "object"]
    selected = st.multiselect("Selecione colunas de texto", options=text_cols, default=text_cols[:10])
    replace_multi_space = st.checkbox("Trocar múltiplos espaços por 1 espaço", value=True)
    if st.button("Aplicar limpeza de texto", key="apply_text"):
        for c in selected:
            s = df[c].astype("string")
            s = s.str.strip()
            if replace_multi_space:
                s = s.str.replace(r"\s+", " ", regex=True)
            df[c] = s
        st.session_state.df = df
        log_step(f"Limpeza de texto aplicada em {len(selected)} colunas (strip + normalização de espaços).")
        st.success("Aplicado!")

# 3) Tipagem automática (datas e números)
with st.expander("3) 🔢 Tipagem automática (detectar datas e números)", expanded=False):
    st.write("Converte colunas `object` que parecem números/datas.")
    convert_numbers = st.checkbox("Tentar converter números (ex: '1.234,56')", value=True)
    convert_dates = st.checkbox("Tentar converter datas", value=True)

    if st.button("Aplicar tipagem automática", key="apply_types"):
        changed = 0

        # números
        if convert_numbers:
            for c in df.columns:
                if df[c].dtype == "object":
                    # tenta converter e mede ganho
                    converted = coerce_numeric(df[c])
                    # critério: se converter >= 70% dos não-nulos vira numérico, aplica
                    non_null = df[c].notna().sum()
                    if non_null > 0:
                        ratio = converted.notna().sum() / non_null
                        if ratio >= 0.7:
                            df[c] = converted
                            changed += 1

        # datas
        if convert_dates:
            for c in df.columns:
                if df[c].dtype == "object":
                    if try_parse_datetime(df[c]):
                        dt = to_datetime_safe(df[c])
                        if dt.notna().sum() >= 0.7 * df[c].notna().sum():
                            df[c] = dt
                            changed += 1

        st.session_state.df = df
        log_step(f"Tipagem automática aplicada. Colunas convertidas: {changed}.")
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
