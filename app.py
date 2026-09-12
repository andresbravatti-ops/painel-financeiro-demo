import streamlit as st
import pandas as pd
import json
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA DO STREAMLIT (DEMO)
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
# 3. BANCO DE DADOS FICTÍCIO PARA DEMONSTRAÇÃO COM CLIENTES
# =====================================================================
mes_atual_str = datetime.now().strftime("%m/%Y")

def carregar_dados_demo():
    return {
        "rendimentos": [
            {"Data": "01/03/2026 08:00", "Mês/Ano": mes_atual_str, "Origem / Categoria": "Salário Principal", "Valor (R$)": 12000.0}
        ],
        "fixas": [
            {"Excluir": False, "Descrição": "Aluguel", "Valor (R$)": 2500.0},
            {"Excluir": False, "Descrição": "Condomínio", "Valor (R$)": 600.0},
            {"Excluir": False, "Descrição": "Internet / Celular", "Valor (R$)": 200.0}
        ],
        "parceladas": [
            {"Descrição": "Notebook de Trabalho", "Valor Parcela": 350.0, "Total Parcelas": 10, "Mês Início": mes_atual_str}
        ],
        "variaveis": [
            {"Data": "05/03/2026 12:00", "Categoria": "Mercado / Alimentação", "Valor (R$)": 1200.0},
            {"Data": "08/03/2026 15:30", "Categoria": "Combustível", "Valor (R$)": 400.0}
        ],
        "reserva_emergencia": [
            {"Ativo / Descrição": "Reserva Liquidez Diária (100% CDI)", "Aporte Acumulado (R$)": 15000.0, "Saldo Atual (R$)": 15800.0}
        ],
        "objetivos_curto": [
            {"Objetivo": "Viagem de Férias", "Ativo / Liquidez": "Conta Remunerada", "Meta Global (R$)": 10000.0, "Aporte Acumulado (R$)": 4000.0, "Saldo Atual (R$)": 4150.0}
        ],
        "objetivos_medio": [
            {"Categoria / Estratégia": "1. Estação de Transbordo (Acumulação)", "Ativo Vinculado": "Conta Remunerada", "Aporte Acumulado (R$)": 2000.0, "Saldo Atual (R$)": 2050.0},
            {"Categoria / Estratégia": "2. Proteção Inflação (Âncora)", "Ativo Vinculado": "Tesouro IPCA+", "Aporte Acumulado (R$)": 5000.0, "Saldo Atual (R$)": 5300.0},
            {"Categoria / Estratégia": "3. Taxa Travada (Prazo Fixo)", "Ativo Vinculado": "CDB com Vencimento", "Aporte Acumulado (R$)": 3000.0, "Saldo Atual (R$)": 3150.0},
            {"Categoria / Estratégia": "4. Isenção de IR (Prazo Fixo)", "Ativo Vinculado": "LCI / LCA", "Aporte Acumulado (R$)": 3000.0, "Saldo Atual (R$)": 3120.0}
        ],
        "previdencia": [
            {"Instituição / Descrição": "Previdência Privada Empresa", "Desconto Mensal Folha (R$)": 500.0, "Total Aportes Anteriores / Acumulados (R$)": 40000.0, "Saldo Atual (R$)": 48000.0}
        ],
        "carteira_renda_fixa_lp": [
            {"Ativo / Descrição": "Tesouro Selic", "Saldo Atual (R$)": 10000.0}
        ],
        "carteira_variavel_lp": [
            {"Classe": "Ações", "Ticker": "PETR4.SA", "Quantidade de Cotas": 200.0},
            {"Classe": "Fundos Imobiliários (FIIs)", "Ticker": "KNRI11.SA", "Quantidade de Cotas": 100.0},
            {"Classe": "ETFs", "Ticker": "BOVA11.SA", "Quantidade de Cotas": 50.0}
        ]
    }

# =====================================================================
# 4. FUNÇÕES DE COTAÇÃO E PREÇOS (B3)
# =====================================================================
@st.cache_data(ttl=300)
def obter_preco_b3(ticker):
    if not ticker or pd.isna(ticker):
        return 0.0, 0.0
    try:
        t = str(ticker).strip().upper()
        if not t.endswith(".SA") and len(t) <= 6:
            t += ".SA"
        dados = yf.Ticker(t).history(period="1mo")
        if not dados.empty and len(dados) >= 1:
            preco_atual = float(dados['Close'].iloc[-1])
            preco_inicial = float(dados['Close'].iloc[0])
            rentabilidade_ativo = ((preco_atual / preco_inicial) - 1.0) * 100.0
            return preco_atual, rentabilidade_ativo
    except:
        pass
    return 0.0, 0.0

@st.cache_data(ttl=600)
def obter_benchmark_ibov():
    try:
        ibov = yf.Ticker("^BVSP").history(period="1mo")
        if not ibov.empty:
            inicio = float(ibov['Close'].iloc[0])
            fim = float(ibov['Close'].iloc[-1])
            return ((fim / inicio) - 1.0) * 100.0
    except:
        pass
    return 0.0

@st.cache_data(ttl=3600)
def obter_benchmark_cdi():
    try:
        selic_anual = 0.1125
        cdi_mensal = (((1 + selic_anual) ** (1 / 12)) - 1) * 100.0
        return cdi_mensal
    except:
        return 0.95

# =====================================================================
# 5. INICIALIZAÇÃO DA MEMÓRIA DE SESSÃO (DEMO)
# =====================================================================
if "dados_carregados" not in st.session_state:
    dados_salvos = carregar_dados_demo()
    
    st.session_state.df_rendimentos = pd.DataFrame(dados_salvos["rendimentos"])
    st.session_state.df_fixas = pd.DataFrame(dados_salvos["fixas"])
    st.session_state.df_parceladas = pd.DataFrame(dados_salvos["parceladas"])
    st.session_state.df_variaveis = pd.DataFrame(dados_salvos["variaveis"])
    st.session_state.df_reserva = pd.DataFrame(dados_salvos["reserva_emergencia"])
    st.session_state.df_obj_curto = pd.DataFrame(dados_salvos["objetivos_curto"])
    st.session_state.df_obj_medio = pd.DataFrame(dados_salvos["objetivos_medio"])
    st.session_state.df_previdencia = pd.DataFrame(dados_salvos["previdencia"])
    st.session_state.df_rf_lp = pd.DataFrame(dados_salvos["carteira_renda_fixa_lp"])
    st.session_state.df_rv_lp = pd.DataFrame(dados_salvos["carteira_variavel_lp"])

    st.session_state.dados_carregados = True

if "Mês/Ano" not in st.session_state.df_rendimentos.columns:
    st.session_state.df_rendimentos["Mês/Ano"] = mes_atual_str

# =====================================================================
# 6. CÁLCULOS ANTECIPADOS GERAIS
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
total_alim = 0.0
total_comb = 0.0
total_outros_var = 0.0

if not st.session_state.df_variaveis.empty:
    total_variaveis = float(pd.to_numeric(st.session_state.df_variaveis["Valor (R$)"], errors="coerce").sum())
    
    df_alim = st.session_state.df_variaveis[st.session_state.df_variaveis["Categoria"] == "Mercado / Alimentação"]
    if not df_alim.empty:
        total_alim = float(pd.to_numeric(df_alim["Valor (R$)"], errors="coerce").sum())
        
    df_comb = st.session_state.df_variaveis[st.session_state.df_variaveis["Categoria"] == "Combustível"]
    if not df_comb.empty:
        total_comb = float(pd.to_numeric(df_comb["Valor (R$)"], errors="coerce").sum())
        
    df_outros = st.session_state.df_variaveis[st.session_state.df_variaveis["Categoria"] == "Outros"]
    if not df_outros.empty:
        total_outros_var = float(pd.to_numeric(df_outros["Valor (R$)"], errors="coerce").sum())

total_despesas_geral = total_fixas + total_parceladas + total_variaveis
sobra_mes_geral = total_rendimentos_geral - total_despesas_geral

# =====================================================================
# 7. CABEÇALHO E MODO DEMONSTRAÇÃO
# =====================================================================
st.warning("✨ **MODO DEMONSTRAÇÃO (PORTFÓLIO):** Este é um ambiente público de testes para futuros clientes conhecerem o painel. Os dados inseridos aqui são simulados.")

col_tit1, col_tit2 = st.columns([4, 1])
with col_tit1:
    st.title("💰 Painel Financeiro — Demonstração")
with col_tit2:
    st.write("")
    estado_atual_priv = st.session_state.ocultar_valores
    novo_estado_priv = st.toggle("👁️ Ocultar Valores R$", value=estado_atual_priv, key="toggle_privacidade_topo")
    if novo_estado_priv != estado_atual_priv:
        st.session_state.ocultar_valores = novo_estado_priv
        st.rerun()

st.divider()

# =====================================================================
# 8. ABAS PRINCIPAIS (PAINEL & INVESTIMENTOS)
# =====================================================================
aba_painel, aba_investimentos = st.tabs(["🏠 Painel Financeiro Principal", "📈 Gestão e Projeção de Investimentos"])

with aba_painel:
    st.subheader("1️⃣ Rendimento Mensal")
    if not st.session_state.df_rendimentos.empty:
        st.dataframe(st.session_state.df_rendimentos, use_container_width=True, hide_index=True)
    rendimento_formatado = fmt_moeda(total_rendimentos_geral)
    st.info(f"**Total de Rendimentos do Mês ({mes_atual_str}):** {rendimento_formatado}")

    st.divider()

    st.subheader("2️⃣ Contas e Despesas")
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        st.write("**Contas Fixas:**")
        if not st.session_state.df_fixas.empty:
            st.dataframe(st.session_state.df_fixas[["Descrição", "Valor (R$)"]], use_container_width=True, hide_index=True)
    with col_ex2:
        st.write("**Contas Parceladas:**")
        if not st.session_state.df_parceladas.empty:
            st.dataframe(st.session_state.df_parceladas, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("3️⃣ Resumo Geral do Mês")
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Total Rendimentos", fmt_moeda(total_rendimentos_geral))
    col_res2.metric("Total Despesas", fmt_moeda(total_despesas_geral))
    col_res3.metric("Sobrando para Investir", fmt_moeda(sobra_mes_geral))

    st.divider()

    st.subheader("4️⃣ Alocação Inteligente de Investimentos")
    col1, col2, col3, col4 = st.columns(4)
    with col1: pct_reserva = st.slider("Reserva (%)", 0, 100, 50, key="slider_reserva")
    with col2: pct_curto = st.slider("Curto Prazo (%)", 0, 100, 20, key="slider_curto")
    with col3: pct_medio = st.slider("Médio Prazo (%)", 0, 100, 10, key="slider_medio")
    with col4: pct_longo = st.slider("Longo Prazo (%)", 0, 100, 20, key="slider_longo")

with aba_investimentos:
    sub_reserva, sub_longo = st.tabs(["🛡️ Reserva de Emergência", "🏛️ Carteira Longo Prazo"])
    
    with sub_reserva:
        st.write("### 🛡️ Reserva de Emergência (Meta de 6 Meses)")
        if not st.session_state.df_reserva.empty:
            st.dataframe(st.session_state.df_reserva, use_container_width=True, hide_index=True)
        tot_sal_res = st.session_state.df_reserva["Saldo Atual (R$)"].sum()
        custo_mensal_total = total_fixas + total_variaveis
        meta_reserva_ideal = custo_mensal_total * 6
        progresso_reserva = min((tot_sal_res / meta_reserva_ideal * 100.0) if meta_reserva_ideal > 0 else 0.0, 100.0)
        st.metric("Meta Ideal da Reserva (6x Custo)", fmt_moeda(meta_reserva_ideal))
        st.progress(float(progresso_reserva / 100.0), text=f"Progresso: {progresso_reserva:.1f}%")

    with sub_longo:
        st.write("### 🏛️ Carteira de Longo Prazo (B3)")
        if not st.session_state.df_rv_lp.empty:
            df_rv = st.session_state.df_rv_lp.copy()
            precos, valores = [], []
            for _, row in df_rv.iterrows():
                p, _ = obter_preco_b3(row["Ticker"])
                precos.append(p)
                valores.append(float(row["Quantidade de Cotas"]) * p)
            df_rv["Preço Atual (R$)"] = precos
            df_rv["Valor Acumulado (R$)"] = valores
            st.dataframe(df_rv, use_container_width=True, hide_index=True)