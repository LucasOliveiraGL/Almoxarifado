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
        st.write("Conteúdo carregado:", df)
                                     
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

# Nova aba: Visão Geral com gráfico
if "📊 Visão Geral" not in st.session_state.get("abas", []):
    if st.session_state["logado"]:
        st.session_state["abas"] = ["📤 Registrar Saída", "📊 Visão Geral", "📋 Estoque", "➕ Registrar Entrada", "📄 Relatório de Saídas", "🧾 Relatório de Entradas", "🆕 Cadastrar Item", "🛠 Editar / Remover"]
    else:
        st.session_state["abas"] = ["📤 Registrar Saída", "🔐 Login Admin"]

aba = st.sidebar.radio("Menu", st.session_state["abas"])

abas_disponiveis += ["🔐 Login Admin"]
aba = st.sidebar.radio("Menu", abas_disponiveis)

if aba == "📊 Visão Geral":
    st.title("📊 Visão Geral de Movimentações")
    df_entradas = pd.read_csv(CAMINHO_ENTRADAS, encoding="utf-8-sig")
    df_saidas = pd.read_csv(CAMINHO_SAIDAS, encoding="utf-8-sig")

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

if aba == "🔐 Login Admin":
    st.subheader("🔐 Login do Administrador")
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
        if entrar:
            if usuario == "Bruna" and senha == "Merco.2025":
                st.session_state["logado"] = True
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")

if aba == "📋 Estoque":
    st.subheader("📋 Estoque Atual")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        df["Situação"] = df.apply(lambda row: "🔴 Baixo Estoque" if row["quantidade"] < row["estoque_minimo"] else "✅ Ok", axis=1)
        st.dataframe(df.style.applymap(
            lambda val: "background-color: #FFCCCC" if val == "🔴 Baixo Estoque" else "background-color: #4a4a4a", subset=["Situação"]  #CCFFCC
        ), use_container_width=True)

elif aba == "📤 Registrar Saída":
    st.subheader("📤 Registrar Saída de Item")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        item_escolhido = st.selectbox("Selecione o item:", df["nome"])
        item = df[df["nome"] == item_escolhido].iloc[0]
        qtd_disponivel = int(item["quantidade"])

        if qtd_disponivel > 0:
            qtd_saida = st.number_input("Quantidade a dar saída:", min_value=1, max_value=qtd_disponivel)
            solicitante = st.text_input("Solicitante")
            observacao = st.text_area("Observação")
            if st.button("Registrar Saída"):
                msg = registrar_saida(item["codigo"], qtd_saida, solicitante, observacao)
                if isinstance(msg, str):
                    if "sucesso" in msg.lower():
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.error("Erro inesperado ao registrar ação.")
        else:
            st.warning("Não há estoque disponível para este item.")


elif aba == "➕ Registrar Entrada":
    st.subheader("➕ Registrar Entrada de Itens")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        item_escolhido = st.selectbox("Selecione o item:", df["nome"])
        item = df[df["nome"] == item_escolhido].iloc[0]
        tipo_entrada = st.radio("Tipo de Entrada", ["Nota Fiscal", "Manual"])
        quantidade = st.number_input("Quantidade", min_value=1)
        documento = st.text_input("Nº Nota Fiscal ou Documento", value="" if tipo_entrada == "Manual" else "")
        fornecedor = st.text_input("Fornecedor (opcional)")
        observacao = st.text_area("Observação (opcional)")
        if st.button("Registrar Entrada"):
            msg = registrar_entrada(
                item["codigo"], quantidade, tipo_entrada,
                documento, fornecedor, observacao
            )
            if isinstance(msg, str):
                if "sucesso" in msg.lower():
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.error("Erro inesperado ao registrar ação.")

elif aba == "📄 Relatório de Saídas":
    st.subheader("📄 Relatório de Saídas")
    df = carregar_saidas()
    if df.empty:
        st.info("Nenhuma saída registrada.")
    else:
        df["data"] = pd.to_datetime(df["data"])
        data_inicio = st.date_input("Data inicial", value=df["data"].min().date())
        data_fim = st.date_input("Data final", value=df["data"].max().date())
        filtro = (df["data"].dt.date >= data_inicio) & (df["data"].dt.date <= data_fim)
        st.dataframe(df[filtro], use_container_width=True)

elif aba == "🧾 Relatório de Entradas":
    st.subheader("🧾 Relatório de Entradas")
    df = carregar_entradas()
    if df.empty:
        st.info("Nenhuma entrada registrada.")
    else:
        df["data"] = pd.to_datetime(df["data"])
        data_inicio = st.date_input("Data inicial", value=df["data"].min().date())
        data_fim = st.date_input("Data final", value=df["data"].max().date())
        filtro = (df["data"].dt.date >= data_inicio) & (df["data"].dt.date <= data_fim)
        st.dataframe(df[filtro], use_container_width=True)

elif aba == "🆕 Cadastrar Item":
    st.subheader("🆕 Cadastrar Novo Item")
    with st.form("form_cadastro"):
        codigo = st.text_input("Código do Item")
        nome = st.text_input("Nome do Item")
        categoria = st.text_input("Categoria")
        quantidade = st.number_input("Quantidade Inicial", min_value=0, step=1)
        estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, step=1)
        estoque_maximo = st.number_input("Estoque Máximo", min_value=0, step=1)
        submitted = st.form_submit_button("Salvar Item")
        if submitted:
            df = carregar_estoque()
            if codigo in df["codigo"].values:
                st.error("Código já cadastrado.")
            else:
                novo = pd.DataFrame([{
                    "codigo": codigo, "nome": nome, "categoria": categoria,
                    "quantidade": quantidade, "estoque_minimo": estoque_minimo, "estoque_maximo": estoque_maximo
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_estoque(df)
                st.success("Item cadastrado com sucesso!")

elif aba == "🛠 Editar / Remover":
    st.subheader("🛠 Editar ou Remover Itens")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        item_escolhido = st.selectbox("Selecione o item:", df["nome"])
        item_idx = df[df["nome"] == item_escolhido].index[0]
        with st.form("form_edicao"):
            codigo = st.text_input("Código", value=df.loc[item_idx, "codigo"])
            nome = st.text_input("Nome", value=df.loc[item_idx, "nome"])
            categoria = st.text_input("Categoria", value=df.loc[item_idx, "categoria"])
            quantidade = st.number_input("Quantidade", value=int(df.loc[item_idx, "quantidade"]), step=1)
            estoque_minimo = st.number_input("Estoque Mínimo", value=int(df.loc[item_idx, "estoque_minimo"]), step=1)
            estoque_maximo = st.number_input("Estoque Máximo", value=int(df.loc[item_idx, "estoque_maximo"]), step=1)
            salvar = st.form_submit_button("Salvar Alterações")
            remover = st.form_submit_button("Remover Item")
            if salvar:
                df.loc[item_idx] = [codigo, nome, categoria, quantidade, estoque_minimo, estoque_maximo]
                salvar_estoque(df)
                st.success("Item atualizado com sucesso.")
            if remover:
                df = df.drop(index=item_idx)
                salvar_estoque(df)
                st.success("Item removido.")
