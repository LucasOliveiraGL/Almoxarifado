import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import gdown

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

# Função para baixar do Drive

def baixar_csv_do_drive(id_arquivo, destino_local):
    url = f"https://drive.google.com/uc?id={id_arquivo}"
    gdown.download(url, destino_local, quiet=True)

# Funções auxiliares

def carregar_estoque():
    if not CAMINHO_ESTOQUE.exists():
        baixar_csv_do_drive(ID_ESTOQUE, CAMINHO_ESTOQUE)
    try:
        df = pd.read_csv(CAMINHO_ESTOQUE)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df
    except Exception:
        return pd.DataFrame(columns=["codigo", "nome", "categoria", "quantidade", "estoque_minimo", "estoque_maximo"])

def salvar_estoque(df):
    df.to_csv(CAMINHO_ESTOQUE, index=False)

def carregar_saidas():
    if not CAMINHO_SAIDAS.exists():
        baixar_csv_do_drive(ID_SAIDAS, CAMINHO_SAIDAS)
    try:
        return pd.read_csv(CAMINHO_SAIDAS)
    except Exception:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "solicitante", "observacao"])

def salvar_saidas(df):
    df.to_csv(CAMINHO_SAIDAS, index=False)

def carregar_entradas():
    if not CAMINHO_ENTRADAS.exists():
        baixar_csv_do_drive(ID_ENTRADAS, CAMINHO_ENTRADAS)
    try:
        return pd.read_csv(CAMINHO_ENTRADAS)
    except Exception:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "tipo", "documento", "fornecedor", "observacao"])

def salvar_entradas(df):
    df.to_csv(CAMINHO_ENTRADAS, index=False)
