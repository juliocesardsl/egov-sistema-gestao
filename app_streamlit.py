import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SisEGOV - Streamlit", layout="wide")

st.title("SisEGOV - Visualização de banco de dados")

DB_PATH = "banco.db"

@st.cache_data
def list_tables(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

@st.cache_data
def read_table(db_path, table_name, limit=1000):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM \"{table_name}\" LIMIT {limit}", conn)
    conn.close()
    return df

st.sidebar.header("Conexão")
st.sidebar.write(f"Banco: {DB_PATH}")

tables = list_tables()
if not tables:
    st.warning("Nenhuma tabela encontrada no banco de dados.")
else:
    table = st.sidebar.selectbox("Tabela", tables)
    limit = st.sidebar.number_input("Limite de linhas", min_value=10, max_value=10000, value=200)

    df = read_table(DB_PATH, table, limit)

    st.subheader(f"Tabela: {table} (exibindo {len(df)} linhas)")
    st.dataframe(df)

    st.markdown("---")
    st.subheader("Estatísticas rápidas")
    st.write(df.describe(include='all'))

    st.subheader("Visualizações")
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        col = st.selectbox("Coluna numérica", numeric_cols)
        chart_type = st.selectbox("Tipo de gráfico", ["Line", "Bar", "Area", "Histogram"])
        if chart_type == "Histogram":
            st.bar_chart(df[col].dropna().value_counts().head(50))
        else:
            st.line_chart(df[col])
    else:
        st.info("Nenhuma coluna numérica para visualizar.")
