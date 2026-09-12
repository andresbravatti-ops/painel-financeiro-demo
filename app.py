import streamlit as st
import pandas as pd
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA DO STREAMLIT (VERSÃO DEMO INTERATIVA)
# =====================================================================
st.set_page_config(
    page_title="Painel Financeiro Demo — Gestão & Investimentos",
    page_icon="💰",
    layout="wide"
)

# =====================================================================
# 2. SISTEMA DE PRIVACIDADE (OCULTAR / EXIBIR VALORES R$)
# =====================================================================
if "ocultar_valores" not in st.session_state:
    st.session_state.ocultar_valores = False

def fmt_moeda(valor):
    if st.session_state.ocultar_valores:
        return "R$ ••••••"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================================================================
# 3. FUNÇÃO DE RESET (ZERA OS DADOS PARA O PRÓXIMO CLIENTE)
# =====================================================================
def reiniciar_dados_demo():
    st.session_state.df_rendimentos = pd.DataFrame(columns=["Data", "Mês/Ano", "Origem / Categoria", "Valor (R$)"])
    st.session_state.df_fixas = pd.DataFrame(columns=["Excluir", "Descrição", "Valor (R$)"])
    st.session_state.df_parceladas = pd.DataFrame(columns=["Descrição", "Valor Parcela", "Total Parcelas", "Mês Início"])
    st.session_state.df_variaveis = pd.DataFrame(columns=["Data", "Categoria", "Valor (R$)"])
    st.session_state.df_reserva = pd.DataFrame(columns=["Ativo / Descrição", "Aporte Acumulado (R$)", "Saldo Atual (R$)"])
    st.session_state.df_obj_curto = pd.DataFrame(columns=["Objetivo", "Ativo / Liquidez", "Meta Global (R$)", "Aporte Acumulado (R$)", "Saldo Atual (R$)"])
    st.session_state.df_obj_medio = pd.DataFrame(columns=["Categoria / Estratégia", "Ativo Vinculado", "Aporte Acumulado (R$)", "Saldo Atual (R$)"])
    st.session_state.df_previdencia = pd.DataFrame(columns=["Instituição / Descrição", "Desconto Mensal Folha (R$)", "Total Aportes Anteriores / Acumulados (R$)", "Saldo Atual (R$)"])
    st.session_state.df_rf_lp = pd.DataFrame(columns=["Ativo / Descrição", "Saldo Atual (R$)"])
    st.session_state.df_rv_lp = pd.DataFrame(columns=["Classe", "Ticker", "Quantidade de Cotas"])

# =====================================================================
# 4. INICIALIZAÇÃO DA MEMÓRIA DE SESSÃO
# =====================================================================
mes_atual_str = datetime.now().strftime("%m/%Y")

if "dados_carregados_demo" not in st.session_state:
    reiniciar_dados_demo()
    # Adiciona alguns dados iniciais leves para o app não nascer totalmente vazio na primeira abertura
    st.session_state.df_rendimentos = pd.DataFrame([[datetime.now().strftime("%d/%m/%Y %H:%M"), mes_atual_str, "Salário Exemplo", 10000.0]], columns=["Data", "Mês/Ano", "Origem / Categoria", "Valor (R$)"])
    st.session_state.dados_carregados_demo = True

if "Mês/Ano" not in st.session_state.df_rendimentos.columns:
    st.session_state.df_rendimentos["Mês/Ano"] = mes_atual_str

# =====================================================================
# 5. CÁLCULOS GERAIS DO MÊS
# =====================================================================
total_rendimentos_geral = 0.0
if not st.session_state.df_rendimentos.empty:
    df_mes_atual = st.session_state.df_rendimentos[st.session_state.df_rendimentos["Mês/Ano"] == mes_atual_str]
    if not df_mes_atual.empty:
        total_rendimentos_geral = float(pd.to_numeric(df_mes_atual["Valor (R$)"], errors="coerce").sum())

total_fixas = 0.0
if not st.session_state.df_fixas.empty:
    total_fixas = float(pd.to_numeric(st.session_state.df_fixas["Valor (R$)"], errors="coerce").sum())

total_parceladas = 0.0
if not st.session_state.df_parceladas.empty:
    total_parceladas = float(pd.to_numeric(st.session_state.df_parceladas["Valor Parcela"], errors="coerce").sum())

total_variaveis = 0.0
if not st.session_state.df_variaveis.empty:
    total_variaveis = float(pd.to_numeric(st.session_state.df_variaveis["Valor (R$)"], errors="coerce").sum())

total_despesas_geral = total_fixas + total_parceladas + total_variaveis
sobra_mes_geral = total_rendimentos_geral - total_despesas_geral

# =====================================================================
# 6. CABEÇALHO E PAINEL DE CONTROLE DA DEMO (COM BOTÃO DE RESET)
# =====================================================================
st.warning("✨ **MODO DEMONSTRAÇÃO INTERATIVO:** O cliente pode testar lançamentos e ver os gráficos em tempo real.")

col_tit1, col_tit2 = st.columns([3, 1])
with col_tit1:
    st.title("💰 Painel Financeiro — Demonstração")
with col_tit2:
    st.write("")
    if st.button("🔄 Zerar / Reiniciar Demonstração"):
        reiniciar_dados_demo()
        st.success("Painel reiniciado com sucesso para o próximo cliente!")
        st.rerun()

st.divider()

# =====================================================================
# 7. ESTRUTURA PRINCIPAL DO APP (INTERATIVA)
# =====================================================================
aba_painel, aba_investimentos = st.tabs(["🏠 Painel Financeiro Principal", "📈 Gestão e Projeção de Investimentos"])

with aba_painel:
    st.subheader("1️⃣ Rendimento Mensal")
    col_r1, col_r2, col_r3, col_r4 = st.columns([1.5, 1.2, 1, 1])
    with col_r1: origem_renda = st.selectbox("Origem do Rendimento", ["Salário André", "Salário Juliana", "Renda Extra", "Outros"])
    with col_r2: val_renda = st.number_input("Valor (R$)", min_value=0.0, step=100.0, format="%.2f", key="input_renda_demo")
    with col_r3: mes_lancamento = st.text_input("Mês / Ano", value=mes_atual_str, key="input_mes_demo")
    with col_r4:
        st.write("")
        st.write("")
        btn_lancar_renda = st.button("Lançar Renda")

    if btn_lancar_renda and val_renda > 0:
        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
        novo_rendimento = pd.DataFrame([[data_hoje, mes_lancamento, origem_renda, float(val_renda)]], columns=["Data", "Mês/Ano", "Origem / Categoria", "Valor (R$)"])
        st.session_state.df_rendimentos = pd.concat([st.session_state.df_rendimentos, novo_rendimento], ignore_index=True)
        st.rerun()

    if not st.session_state.df_rendimentos.empty:
        st.dataframe(st.session_state.df_rendimentos, use_container_width=True, hide_index=True)

    st.info(f"**Total de Rendimentos do Mês ({mes_atual_str}):** {fmt_moeda(total_rendimentos_geral)}")

    st.divider()

    st.subheader("2️⃣ Resumo Geral do Mês")
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Total Rendimentos", fmt_moeda(total_rendimentos_geral))
    col_res2.metric("Total Despesas", fmt_moeda(total_despesas_geral))
    col_res3.metric("Sobrando para Investir", fmt_moeda(sobra_mes_geral))

with aba_investimentos:
    st.write("### 🛡️ Gestão de Investimentos e Metas")
    st.info(f"Sobra disponível para alocação no mês: **{fmt_moeda(sobra_mes_geral)}**")
