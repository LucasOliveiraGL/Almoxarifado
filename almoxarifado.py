import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import gdown
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import altair as alt

# Iniciar sessão
if "logado" not in st.session_state:
    st.session_state["logado"] = False

# IDs públicos dos arquivos no Google Drive
ID_ESTOQUE = "1tWBClg4tzpt-kT8rp3MwdFRlKM-LBKRm"
ID_SAIDAS = "1T2rxhL_n7rI4-JPI78scY86noS7C4Pns"
ID_ENTRADAS = "1KhKIpEGhYYDB4oeKwWnIFVhnGtSWTrl-"

# Pasta de dados
PASTA_DADOS = Path("data")
PASTA_DADOS.mkdir(exist_ok=True)

CAMINHO_ESTOQUE = PASTA_DADOS / "estoque.csv"
CAMINHO_SAIDAS = PASTA_DADOS / "saidas.csv"
CAMINHO_ENTRADAS = PASTA_DADOS / "entradas.csv"

# Função para baixar arquivo do Google Drive (gdown)
def baixar_csv_do_drive(id_arquivo, destino_local):
    url = f"https://drive.google.com/uc?id={id_arquivo}"
    gdown.download(url, destino_local, quiet=True)

# Função para upload do arquivo atualizado para o Google Drive
def upload_para_drive(file_path, file_id):
    service_account_info = json.loads(st.secrets["gdrive_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(file_path, mimetype="text/csv")
    service.files().update(fileId=file_id, media_body=media).execute()

# ===============================
# Funções de carga e salvamento
# ===============================

def carregar_estoque():
    if not CAMINHO_ESTOQUE.exists():
        baixar_csv_do_drive(ID_ESTOQUE, CAMINHO_ESTOQUE)
    try:
        df = pd.read_csv(CAMINHO_ESTOQUE, encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df
    except Exception:
        return pd.DataFrame(columns=["codigo", "nome", "categoria", "quantidade", "estoque_minimo", "estoque_maximo"])

def salvar_estoque(df):
    df.to_csv(CAMINHO_ESTOQUE, index=False)
    upload_para_drive(CAMINHO_ESTOQUE, ID_ESTOQUE)

def carregar_saidas():
    if not CAMINHO_SAIDAS.exists():
        baixar_csv_do_drive(ID_SAIDAS, CAMINHO_SAIDAS)
    try:
        return pd.read_csv(CAMINHO_SAIDAS)
    except Exception:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "solicitante", "observacao"])

def salvar_saidas(df):
    df.to_csv(CAMINHO_SAIDAS, index=False)
    upload_para_drive(CAMINHO_SAIDAS, ID_SAIDAS)

def carregar_entradas():
    if not CAMINHO_ENTRADAS.exists():
        baixar_csv_do_drive(ID_ENTRADAS, CAMINHO_ENTRADAS)
    try:
        return pd.read_csv(CAMINHO_ENTRADAS)
    except Exception:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "tipo", "documento", "fornecedor", "observacao"])

def salvar_entradas(df):
    df.to_csv(CAMINHO_ENTRADAS, index=False)
    upload_para_drive(CAMINHO_ENTRADAS, ID_ENTRADAS)
    return "Entrada registrada com sucesso!"

# Interface Streamlit
st.set_page_config(page_title="Sistema de Almoxarifado", layout="wide")
st.title("📦 Sistema de Almoxarifado")

# Define abas permitidas
abas_disponiveis = ["📤 Registrar Saída"]

if st.session_state["logado"]:
    abas_disponiveis += [
        "📊 Visão Geral", "📋 Estoque", "➕ Registrar Entrada", "📄 Relatório de Saídas",
        "🧾 Relatório de Entradas", "🆕 Cadastrar Item", "🛠 Editar / Remover"
    ]
abas_disponiveis += ["🔐 Login Admin"]
aba = st.sidebar.radio("Menu", abas_disponiveis)

# Visão Geral com gráfico
if aba == "📊 Visão Geral":
    st.title("📊 Visão Geral de Movimentações")
    df_entradas = carregar_entradas()
    df_saidas = carregar_saidas()

    if df_entradas.empty and df_saidas.empty:
        st.warning("Sem dados de movimentações para exibir.")
    else:
        df_entradas["data"] = pd.to_datetime(df_entradas["data"])
        df_saidas["data"] = pd.to_datetime(df_saidas["data"])

        entradas_mes = df_entradas.groupby(df_entradas["data"].dt.to_period("M"))[["quantidade"]].sum().reset_index()
        entradas_mes["data"] = entradas_mes["data"].dt.to_timestamp()
        entradas_mes["tipo"] = "Entrada"

        saidas_mes = df_saidas.groupby(df_saidas["data"].dt.to_period("M"))[["quantidade"]].sum().reset_index()
        saidas_mes["data"] = saidas_mes["data"].dt.to_timestamp()
        saidas_mes["tipo"] = "Saída"

        df_total = pd.concat([entradas_mes, saidas_mes])

        grafico = alt.Chart(df_total).mark_bar().encode(
            x=alt.X("yearmonth(data):T", title="Mês"),
            y=alt.Y("quantidade:Q", title="Quantidade"),
            color=alt.Color("tipo:N", title="Movimentação"),
            tooltip=["data", "quantidade", "tipo"]
        ).properties(width=700, height=400)

        st.altair_chart(grafico, use_container_width=True)
