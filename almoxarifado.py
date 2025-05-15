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
from io import BytesIO

#=======
#BLOCO 1
#=======

if "logado" not in st.session_state:
    st.session_state["logado"] = False

ID_ESTOQUE = "1tWBClg4tzpt-kT8rp3MwdFRlKM-LBKRm"
ID_SAIDAS = "1T2rxhL_n7rI4-JPI78scY86noS7C4Pns"
ID_ENTRADAS = "1KhKIpEGhYYDB4oeKwWnIFVhnGtSWTrl-"

PASTA_DADOS = Path("data")
PASTA_DADOS.mkdir(exist_ok=True)
CAMINHO_ESTOQUE = PASTA_DADOS / "estoque.csv"
CAMINHO_SAIDAS = PASTA_DADOS / "saidas.csv"
CAMINHO_ENTRADAS = PASTA_DADOS / "entradas.csv"

def baixar_csv_do_drive(id_arquivo, destino_local):
    url = f"https://drive.google.com/uc?id={id_arquivo}"
    gdown.download(url, destino_local, quiet=True)

def upload_para_drive(file_path, file_id):
    info = st.secrets["gdrive_service_account"]
    creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(file_path, mimetype="text/csv")
    service.files().update(fileId=file_id, media_body=media).execute()

def carregar_estoque():
    if not CAMINHO_ESTOQUE.exists():
        baixar_csv_do_drive(ID_ESTOQUE, CAMINHO_ESTOQUE)
   #return pd.read_csv(CAMINHO_ESTOQUE, encoding="utf-8-sig")

def salvar_estoque(df):
    df.to_csv(CAMINHO_ESTOQUE, index=False)
    upload_para_drive(CAMINHO_ESTOQUE, ID_ESTOQUE)

def carregar_saidas():
    if not CAMINHO_SAIDAS.exists():
        baixar_csv_do_drive(ID_SAIDAS, CAMINHO_SAIDAS)
    return pd.read_csv(CAMINHO_SAIDAS)

def salvar_saidas(df):
    df.to_csv(CAMINHO_SAIDAS, index=False)
    upload_para_drive(CAMINHO_SAIDAS, ID_SAIDAS)

def carregar_entradas():
    if not CAMINHO_ENTRADAS.exists():
        baixar_csv_do_drive(ID_ENTRADAS, CAMINHO_ENTRADAS)
    return pd.read_csv(CAMINHO_ENTRADAS)

def salvar_entradas(df):
    df.to_csv(CAMINHO_ENTRADAS, index=False)
    upload_para_drive(CAMINHO_ENTRADAS, ID_ENTRADAS)

def registrar_saida(codigo, quantidade, solicitante, observacao):
    df_estoque = carregar_estoque()
    df_saidas = carregar_saidas()
    item = df_estoque[df_estoque["codigo"] == codigo].iloc[0]
    if quantidade > item["quantidade"]:
        return "Estoque insuficiente."
    df_estoque.loc[df_estoque["codigo"] == codigo, "quantidade"] -= quantidade
    salvar_estoque(df_estoque)
    nova_saida = pd.DataFrame([{
        "data": datetime.now(), "codigo": codigo,
        "nome": item["nome"], "categoria": item["categoria"],
        "quantidade": quantidade, "solicitante": solicitante,
        "observacao": observacao
    }])
    df_saidas = pd.concat([df_saidas, nova_saida], ignore_index=True)
    salvar_saidas(df_saidas)
    return "Saída registrada com sucesso!"

def registrar_entrada(codigo, quantidade, tipo, documento, fornecedor, observacao):
    df_estoque = carregar_estoque()
    df_entradas = carregar_entradas()
    idx = df_estoque[df_estoque["codigo"] == codigo].index[0]
    df_estoque.loc[idx, "quantidade"] += quantidade
    salvar_estoque(df_estoque)
    nova = pd.DataFrame([{
        "data": datetime.now(), "codigo": codigo,
        "nome": df_estoque.loc[idx, "nome"],
        "categoria": df_estoque.loc[idx, "categoria"],
        "quantidade": quantidade, "tipo": tipo,
        "documento": documento, "fornecedor": fornecedor,
        "observacao": observacao
    }])
    df_entradas = pd.concat([df_entradas, nova], ignore_index=True)
    salvar_entradas(df_entradas)
    return "Entrada registrada com sucesso!"

#=======
#BLOCO 2
#=======

# Interface
st.set_page_config("Sistema de Almoxarifado", layout="wide")
st.title("📦 Sistema de Almoxarifado")

abas = ["📤 Registrar Saída"]
if st.session_state["logado"]:
    abas += ["📊 Visão Geral", "📋 Estoque", "➕ Registrar Entrada", "📄 Relatório de Saídas",
             "🧾 Relatório de Entradas", "🆕 Cadastrar Item", "🛠 Editar / Remover", "🚪 Logout"]
else:
    abas += ["🔐 Login Admin"]

aba = st.sidebar.radio("Menu", abas)

if aba == "📋 Estoque":
    st.subheader("📋 Estoque Atual")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        df["Situação"] = df.apply(lambda row: "🔴 Baixo Estoque" if row["quantidade"] < row["estoque_minimo"] else "✅ Ok", axis=1)
        st.dataframe(df.style.applymap(
            lambda val: "background-color: #FFCCCC" if val == "🔴 Baixo Estoque" else "background-color: #4a4a4a",
            subset=["Situação"]
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
                st.success(msg) if "sucesso" in msg.lower() else st.error(msg)
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
            msg = registrar_entrada(item["codigo"], quantidade, tipo_entrada, documento, fornecedor, observacao)
            st.success(msg) if "sucesso" in msg.lower() else st.error(msg)

elif aba == "📄 Relatório de Saídas":
    st.subheader("📄 Relatório de Saídas")
    df = carregar_saidas()
    if df.empty:
        st.info("Nenhuma saída registrada.")
    else:
        df["data"] = pd.to_datetime(df["data"])
        data_inicio = st.date_input("Data inicial", value=df["data"].min().date(), key="saida_ini")
        data_fim = st.date_input("Data final", value=df["data"].max().date(), key="saida_fim")
        filtro = (df["data"].dt.date >= data_inicio) & (df["data"].dt.date <= data_fim)
        st.dataframe(df[filtro], use_container_width=True)

elif aba == "🧾 Relatório de Entradas":
    st.subheader("🧾 Relatório de Entradas")
    df = carregar_entradas()
    if df.empty:
        st.info("Nenhuma entrada registrada.")
    else:
        df["data"] = pd.to_datetime(df["data"])
        data_inicio = st.date_input("Data inicial", value=df["data"].min().date(), key="ent_ini")
        data_fim = st.date_input("Data final", value=df["data"].max().date(), key="ent_fim")
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
        if st.form_submit_button("Salvar Item"):
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

#=======
#BLOCO 3
#=======
def exportar_excel(df, nome_base):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Exportar para Excel", buffer.getvalue(), file_name=f"{nome_base}.xlsx")

def registrar_log(acao, usuario, detalhes):
    CAMINHO_LOG = Path("data") / "log.csv"
    colunas = ["data", "usuario", "acao", "detalhes"]
    nova_linha = pd.DataFrame([{
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario,
        "acao": acao,
        "detalhes": detalhes
    }])
    try:
        log_df = pd.read_csv(CAMINHO_LOG)
    except FileNotFoundError:
        log_df = pd.DataFrame(columns=colunas)

    log_df = pd.concat([log_df, nova_linha], ignore_index=True)
    log_df.to_csv(CAMINHO_LOG, index=False)
    # Opcional: subir para o Google Drive

# Exemplos de uso nos blocos anteriores:
# registrar_log("entrada", "Bruna", f"{quantidade}x {item['nome']}")
# registrar_log("saida", "Bruna", f"{quantidade}x {item['nome']} para {solicitante}")

# Dentro de relatórios:
# exportar_excel(df[filtro], "relatorio_entradas") ou "relatorio_saidas"
