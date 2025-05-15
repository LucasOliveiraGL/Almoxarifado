import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# Pasta de dados
PASTA_DADOS = Path("data")
PASTA_DADOS.mkdir(exist_ok=True)

CAMINHO_ESTOQUE = PASTA_DADOS / "estoque.csv"
CAMINHO_SAIDAS = PASTA_DADOS / "saidas.csv"
CAMINHO_ENTRADAS = PASTA_DADOS / "entradas.csv"

# Funções auxiliares
def carregar_estoque():
    try:
        df = pd.read_csv(CAMINHO_ESTOQUE)
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["codigo", "nome", "categoria", "quantidade", "estoque_minimo", "estoque_maximo"])

def salvar_estoque(df):
    df.to_csv(CAMINHO_ESTOQUE, index=False)

def carregar_saidas():
    try:
        return pd.read_csv(CAMINHO_SAIDAS)
    except FileNotFoundError:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "solicitante", "observacao"])

def salvar_saidas(df):
    df.to_csv(CAMINHO_SAIDAS, index=False)

def carregar_entradas():
    try:
        return pd.read_csv(CAMINHO_ENTRADAS)
    except FileNotFoundError:
        return pd.DataFrame(columns=["data", "codigo", "nome", "categoria", "quantidade", "tipo", "documento", "fornecedor", "observacao"])

def salvar_entradas(df):
    df.to_csv(CAMINHO_ENTRADAS, index=False)

def registrar_saida(codigo, quantidade, solicitante, observacao):
    df_estoque = carregar_estoque()
    df_saidas = carregar_saidas()

    item = df_estoque[df_estoque["codigo"] == codigo]
    if item.empty:
        return "Item não encontrado no estoque."

    qtd_disponivel = int(item["quantidade"].values[0])
    if quantidade > qtd_disponivel:
        return f"Estoque insuficiente. Disponível: {qtd_disponivel}"

    df_estoque.loc[df_estoque["codigo"] == codigo, "quantidade"] = qtd_disponivel - quantidade
    salvar_estoque(df_estoque)

    nova_saida = pd.DataFrame([{
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "codigo": codigo,
        "nome": item["nome"].values[0],
        "categoria": item["categoria"].values[0],
        "quantidade": quantidade,
        "solicitante": solicitante,
        "observacao": observacao
    }])
    df_saidas = pd.concat([df_saidas, nova_saida], ignore_index=True)
    salvar_saidas(df_saidas)

    return "Saída registrada com sucesso!"

def registrar_entrada(codigo, quantidade, tipo, documento, fornecedor, observacao):
    df_estoque = carregar_estoque()
    df_entradas = carregar_entradas()

    if codigo not in df_estoque["codigo"].values:
        return "Código não encontrado no estoque."

    idx = df_estoque[df_estoque["codigo"] == codigo].index[0]
    df_estoque.loc[idx, "quantidade"] += quantidade
    salvar_estoque(df_estoque)

    nova = pd.DataFrame([{
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

    return "Entrada registrada com sucesso!"

# Interface Streamlit
st.set_page_config(page_title="Sistema de Almoxarifado", layout="wide")
st.title("📦 Sistema de Almoxarifado")

aba = st.sidebar.radio("Menu", [
    "📋 Estoque", "🚚 Registrar Saída", "➕ Registrar Entrada",
    "📄 Relatório de Saídas", "🧾 Relatório de Entradas",
    "🆕 Cadastrar Item", "🛠 Editar / Remover"
])

if aba == "📋 Estoque":
    st.subheader("📋 Estoque Atual")
    df = carregar_estoque()
    if df.empty:
        st.warning("Estoque vazio.")
    else:
        df["Situação"] = df.apply(lambda row: "🔴 Baixo Estoque" if row["quantidade"] < row["estoque_minimo"] else "✅ Ok", axis=1)
        st.dataframe(df.style.applymap(
            lambda val: "background-color: #FFCCCC" if val == "🔴 Baixo Estoque" else "background-color: #CCFFCC", subset=["Situação"]
        ), use_container_width=True)

elif aba == "🚚 Registrar Saída":
    st.subheader("🚚 Registrar Saída de Item")
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
