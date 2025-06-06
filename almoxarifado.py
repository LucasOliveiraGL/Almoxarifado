import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import gdown
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import altair as alt
from io import BytesIO

#======= CONFIGS INICIAIS =======
st.set_page_config("Sistema de Almoxarifado", layout="wide")
st.title("📦 Sistema de Almoxarifado")

if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = ""
if "aba" not in st.session_state:
    st.session_state["aba"] = "📤 Registrar Saída"

ID_ESTOQUE = "1tWBClg4tzpt-kT8rp3MwdFRlKM-LBKRm"
ID_SAIDAS = "1T2rxhL_n7rI4-JPI78scY86noS7C4Pns"
ID_ENTRADAS = "1KhKIpEGhYYDB4oeKwWnIFVhnGtSWTrl-"
ID_LOG = "16n5_9vxy2xNyBw04cKvDFUo0jFST5OcG"
ID_USUARIOS = "11FDvvNeNAkIKeqHN0P_R_qDA7coXKZfT"

PASTA_DADOS = Path("data")
PASTA_DADOS.mkdir(exist_ok=True)
CAMINHO_ESTOQUE = PASTA_DADOS / "estoque.csv"
CAMINHO_SAIDAS = PASTA_DADOS / "saidas.csv"
CAMINHO_ENTRADAS = PASTA_DADOS / "entradas.csv"
CAMINHO_LOG = PASTA_DADOS / "log.csv"
CAMINHO_USUARIOS = PASTA_DADOS / "usuarios.json"

#======= FUNÇÕES UTILITÁRIAS =======
def baixar_csv_do_drive(id_arquivo, destino_local):
    url = f"https://drive.google.com/uc?id={id_arquivo}"
    gdown.download(url, destino_local, quiet=True)

def upload_para_drive(file_path, file_id):
    info = st.secrets["gdrive_service_account"]
    creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(file_path, mimetype="text/csv")
    service.files().update(fileId=file_id, media_body=media).execute()

def carregar_usuarios():
    caminho = str(CAMINHO_USUARIOS)
    if not os.path.exists(caminho):
        gdown.download(f"https://drive.google.com/uc?id={ID_USUARIOS}", caminho, quiet=True)
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)

def exportar_excel(df, nome_base):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    st.download_button("📥 Exportar Excel", buffer.getvalue(), file_name=f"{nome_base}.xlsx")

def carregar_estoque():
    try:
        if not CAMINHO_ESTOQUE.exists():
            baixar_csv_do_drive(ID_ESTOQUE, CAMINHO_ESTOQUE)
        df = pd.read_csv(CAMINHO_ESTOQUE, encoding="utf-8-sig")
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df
    except:
        return pd.DataFrame(columns=["codigo", "nome", "categoria", "quantidade", "estoque_minimo", "estoque_maximo"])

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

def registrar_log(acao, usuario, detalhes):
    colunas = ["data", "usuario", "acao", "detalhes"]
    nova_linha = pd.DataFrame([{
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuario": usuario,
        "acao": acao,
        "detalhes": detalhes
    }])
    try:
        if not CAMINHO_LOG.exists():
            baixar_csv_do_drive(ID_LOG, CAMINHO_LOG)
        df_log = pd.read_csv(CAMINHO_LOG)
    except:
        df_log = pd.DataFrame(columns=colunas)

    df_log = pd.concat([df_log, nova_linha], ignore_index=True)
    df_log.to_csv(CAMINHO_LOG, index=False)
    upload_para_drive(CAMINHO_LOG, ID_LOG)

def registrar_saida(codigo, quantidade, solicitante, observacao):
    df_estoque = carregar_estoque()
    df_saidas = carregar_saidas()
    item = df_estoque[df_estoque["codigo"] == codigo].iloc[0]
    if quantidade > item["quantidade"]:
        return "Estoque insuficiente."
    df_estoque.loc[df_estoque["codigo"] == codigo, "quantidade"] -= quantidade
    salvar_estoque(df_estoque)
    nova_saida = pd.DataFrame([{
        "data": datetime.now(),
        "codigo": codigo,
        "nome": item["nome"],
        "categoria": item["categoria"],
        "quantidade": quantidade,
        "solicitante": solicitante,
        "observacao": observacao
    }])
    df_saidas = pd.concat([df_saidas, nova_saida], ignore_index=True)
    salvar_saidas(df_saidas)
    registrar_log("saida", solicitante, f"{quantidade}x {item['nome']}")
    return "Saída registrada com sucesso!"

def registrar_entrada(codigo, quantidade, tipo, documento, fornecedor, observacao):
    df_estoque = carregar_estoque()
    df_entradas = carregar_entradas()
    idx = df_estoque[df_estoque["codigo"] == codigo].index[0]
    df_estoque.loc[idx, "quantidade"] += quantidade
    salvar_estoque(df_estoque)
    nova = pd.DataFrame([{
        "data": datetime.now(),
        "codigo": codigo,
        "nome": df_estoque.loc[idx, "nome"],
        "categoria": df_estoque.loc[idx, "categoria"],
        "quantidade": quantidade,
        "tipo": tipo,
        "documento": documento,
        "fornecedor": fornecedor,
        "observacao": observacao
    }])
    df_entradas = pd.concat([df_entradas, nova], ignore_index=True)
    salvar_entradas(df_entradas)
    registrar_log("entrada", st.session_state["usuario_logado"], f"{quantidade}x {df_estoque.loc[idx, 'nome']}")
    return "Entrada registrada com sucesso!"

# ======= MENU LATERAL COM BOTÕES ======= #
st.sidebar.markdown("### 📚 Menu")

# Define itens do menu com rótulo visível e valor interno da aba
menu_itens = [
    ("📤 Registrar Saída", "📤 Registrar Saída")
]

if st.session_state["logado"]:
    menu_itens += [
        ("📋 Estoque", "estoque"),
        ("➕ Registrar Entrada", "entrada"),
        ("📄 Relatório de Saídas", "relatorio_saidas"),
        ("🧾 Relatório de Entradas", "relatorio_entradas"),
        ("🆕 Cadastrar Item", "cadastrar"),
        ("🛠 Editar / Remover", "editar"),
        ("🚪 Logout", "logout")
    ]
else:
    menu_itens.append(("🔐 Login Admin", "🔐 Login Admin"))

# Inicializa aba padrão
if "aba" not in st.session_state:
    st.session_state["aba"] = "📤 Registrar Saída"

# Renderiza botões como menu
for label, chave in menu_itens:
    if st.sidebar.button(label):
        st.session_state["aba"] = chave

# Define aba ativa
aba = st.session_state["aba"]

# ======= CONTEÚDO DAS ABAS BASEADO NO SESSION_STATE["aba"] =======
usuarios_permitidos = carregar_usuarios()
# 🔐 Aba Login
if aba == "🔐 Login Admin":
    st.subheader("🔐 Login do Administrador")
    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
        if entrar:
            cred_valida = any(u["usuario"] == usuario and u["senha"] == senha for u in usuarios_permitidos["usuarios"])
            if cred_valida:
                st.session_state["logado"] = True
                st.session_state["usuario_logado"] = usuario
                st.session_state["aba"] = "📋 Estoque"  # Redireciona para estoque ao logar
                registrar_log("login", usuario, "Acesso autorizado")
                st.success("Login realizado com sucesso! Recarregando...")
                st.rerun()
            else:
                registrar_log("tentativa_login", usuario, "Acesso negado")
                st.error("Usuário ou senha inválidos.")

# 🚪 Logout
elif st.session_state["aba"] == "logout":
    registrar_log("logout", st.session_state.get("usuario_logado", "admin"), "Encerrando sessão")
    st.session_state["logado"] = False
    st.session_state["usuario_logado"] = ""
    st.session_state["aba"] = "login"
    st.success("Logout realizado.")
    st.rerun()

# 📤 Aba Registrar Saída
if aba == "📤 Registrar Saída":
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
            solicitante = st.text_input("Solicitante", value=st.session_state.get("usuario_logado", ""))
            observacao = st.text_area("Observação")
            if st.button("Registrar Saída"):
                msg = registrar_saida(item["codigo"], qtd_saida, solicitante, observacao)
                st.success(msg) if "sucesso" in msg.lower() else st.error(msg)
        else:
            st.warning("Não há estoque disponível para este item.")

# 📋 Estoque
elif st.session_state["aba"] == "estoque":
    st.subheader("📋 Estoque Atual")

    # Força sincronização do estoque com o Drive antes de carregar
    try:
        baixar_csv_do_drive(ID_ESTOQUE, str(CAMINHO_ESTOQUE))
    except Exception as e:
        st.error(f"Erro ao atualizar estoque do Drive: {e}")
    
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        def classificar_situacao(row):
            if row["quantidade"] == 0:
                return "⚠️ Sem Estoque"
            elif row["quantidade"] < row["estoque_minimo"]:
                return "🟡 Baixo Estoque"
            else:
                return "✅ Ok"

        df["Situação"] = df.apply(classificar_situacao, axis=1)

        def colorir_situacao(val):
            if val == "⚠️ Sem Estoque":
                return "background-color: #ffcccc; color: red"
            elif val == "🟡 Baixo Estoque":
                return "background-color: #ffffcc; color: orange"
            elif val == "✅ Ok":
                return "background-color: #4a4a4a; color: lightgreen"
            return ""

        st.dataframe(
            df.style.applymap(colorir_situacao, subset=["Situação"]),
            use_container_width=True,
            height=35 * len(df) + 80
        )

# ➕ Registrar Entrada
elif st.session_state["aba"] == "entrada":
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
                item["codigo"], quantidade, tipo_entrada, documento, fornecedor, observacao
            )
            st.success(msg) if "sucesso" in msg.lower() else st.error(msg)

# 📄 Relatório de Saídas
elif st.session_state["aba"] == "relatorio_saidas":
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
        exportar_excel(df[filtro], "relatorio_saidas")

# 🧾 Relatório de Entradas
elif st.session_state["aba"] == "relatorio_entradas":
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
        exportar_excel(df[filtro], "relatorio_entradas")

# 🆕 Cadastrar Item
elif st.session_state["aba"] == "cadastrar":
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
                    "codigo": codigo,
                    "nome": nome,
                    "categoria": categoria,
                    "quantidade": quantidade,
                    "estoque_minimo": estoque_minimo,
                    "estoque_maximo": estoque_maximo
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_estoque(df)
                registrar_log("cadastro", st.session_state["usuario_logado"], f"{quantidade}x {nome}")
                st.success("Item cadastrado com sucesso!")

# 🛠 Editar ou Remover
elif st.session_state["aba"] == "editar":
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
                registrar_log("editar", st.session_state["usuario_logado"], f"{codigo} atualizado")
                st.success("Item atualizado com sucesso.")
            if remover:
                nome_removido = df.loc[item_idx, "nome"]
                df = df.drop(index=item_idx)
                salvar_estoque(df)
                registrar_log("remover", st.session_state["usuario_logado"], f"{nome_removido} excluído")
                st.success("Item removido.")
