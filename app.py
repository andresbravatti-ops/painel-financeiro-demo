import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import yfinance as yf
import plotly.graph_objects as go
import requests

# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA DO STREAMLIT (VERSÃO DEMO)
# =====================================================================
st.set_page_config(
    page_title="Painel Financeiro — Demonstração",
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
# 3. FUNÇÃO DE RESET (ZERA OS DADOS PARA O PRÓXIMO TESTE)
# =====================================================================
def reiniciar_dados_demo():
    st.session_state.df_rendimentos = pd.DataFrame(columns=["Data", "Mês/Ano", "Origem / Categoria", "Valor (R$)"])
    st.session_state.df_fixas = pd.DataFrame(columns=["Excluir", "Descrição", "Valor (R$)"])
    st.session_state.df_parceladas = pd.DataFrame(columns=["Descrição", "Valor Parcela", "Total Parcelas", "Mês Início"])
    st.session_state.df_variaveis = pd.DataFrame(columns=["Data", "Categoria", "Valor (R$)"])
    st.session_state.df_reserva = pd.DataFrame([
        {"Ativo / Descrição": "Reserva Liquidez Diária (100% CDI)", "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0}
    ])
    st.session_state.df_obj_curto = pd.DataFrame([
        {"Objetivo": "Troca de Carro", "Ativo / Liquidez": "Conta Remunerada 100% CDI", "Meta Global (R$)": 15000.0, "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0}
    ])
    st.session_state.df_obj_medio = pd.DataFrame([
        {"Categoria / Estratégia": "1. Estação de Transbordo (Acumulação)", "Ativo Vinculado": "Conta Remunerada", "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0},
        {"Categoria / Estratégia": "2. Proteção Inflação (Âncora)", "Ativo Vinculado": "Tesouro IPCA+", "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0},
        {"Categoria / Estratégia": "3. Taxa Travada (Prazo Fixo)", "Ativo Vinculado": "CDB com Vencimento", "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0},
        {"Categoria / Estratégia": "4. Isenção de IR (Prazo Fixo)", "Ativo Vinculado": "LCI / LCA", "Aporte Acumulado (R$)": 0.0, "Saldo Atual (R$)": 0.0}
    ])
    st.session_state.df_previdencia = pd.DataFrame([
        {"Instituição / Descrição": "Previdência Privada Cooperativa", "Desconto Mensal Folha (R$)": 560.0, "Total Aportes Anteriores / Acumulados (R$)": 150000.0, "Saldo Atual (R$)": 223000.0}
    ])
    st.session_state.df_rf_lp = pd.DataFrame([
        {"Ativo / Descrição": "Tesouro Selic", "Saldo Atual (R$)": 0.0}
    ])
    st.session_state.df_rv_lp = pd.DataFrame([
        {"Classe": "Ações", "Ticker": "PETR4.SA", "Quantidade de Cotas": 0.0},
        {"Classe": "Fundos Imobiliários (FIIs)", "Ticker": "KNRI11.SA", "Quantidade de Cotas": 0.0},
        {"Classe": "ETFs", "Ticker": "BOVA11.SA", "Quantidade de Cotas": 0.0}
    ])

# =====================================================================
# 4. INTEGRAÇÃO E DISPARO DE ALERTAS PARA O TELEGRAM (PESSOAL)
# =====================================================================
def enviar_alerta_telegram(mensagem):
    TOKEN = "8867415251:AAFi5kbDPwm3BazmSVn5FMLW7E1WcjPTd1A"
    CHAT_ID = "8951392410"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    
    try:
        resposta = requests.post(url, json=payload, timeout=10)
        if resposta.status_code == 200:
            return True
        else:
            print(f"Erro ao enviar Telegram. Status: {resposta.status_code} - Resposta: {resposta.text}")
            return False
    except Exception as e:
        print(f"ERRO EXATO NO TELEGRAM: {e}")
        return False

# =====================================================================
# 5. CONTROLE DE ACESSO E AUTENTICAÇÃO (SENHA FIXA: 123456)
# =====================================================================
if "autenticado" not in st.session_state:
    if st.query_params.get("auth") == "true":
        st.session_state.autenticado = True
    else:
        st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito — Painel Financeiro Demo")
    st.markdown("Digite sua senha para desbloquear o painel:")

    senha_correta = "123456"
    senha_digitada = st.text_input("Senha", type="password", key="input_senha_login")

    if st.button("Entrar", key="btn_login"):
        if senha_digitada == senha_correta:
            st.session_state.autenticado = True
            st.query_params["auth"] = "true"
            st.rerun()
        else:
            st.error("❌ Senha incorreta.")

    st.stop()

# =====================================================================
# 6. INICIALIZAÇÃO DA MEMÓRIA DE SESSÃO DO STREAMLIT (DEMO)
# =====================================================================
mes_atual_str = datetime.now().strftime("%m/%Y")

if "dados_carregados_demo" not in st.session_state:
    reiniciar_dados_demo()
    st.session_state.dados_carregados_demo = True

if "Mês/Ano" not in st.session_state.df_rendimentos.columns:
    st.session_state.df_rendimentos["Mês/Ano"] = mes_atual_str

# =====================================================================
# 7. CÁLCULOS ANTECIPADOS GERAIS (ORÇAMENTO DO MÊS)
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
# 8. ESTILO VISUAL CSS CUSTOMIZADO
# =====================================================================
st.markdown("""
    <style>
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #CCCCCC !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        padding: 4px 12px !important;
        height: auto !important;
    }
    div.stButton > button:hover {
        background-color: #F0F2F6 !important;
        border-color: #999999 !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# 9. CABEÇALHO DO PAINEL, BOTÃO DE PRIVACIDADE E BOTÃO DE RESET (DEMO)
# =====================================================================
st.warning("✨ **AMBIENTE DE SIMULAÇÃO INTERATIVO:** Sinta-se à vontade para testar os lançamentos, as projeções e os gráficos em tempo real.")

col_tit1, col_tit2, col_tit3 = st.columns([2.5, 1.2, 1.3])
with col_tit1:
    st.title("💰 Painel Financeiro — Demo")
with col_tit2:
    st.write("")
    estado_atual_priv = st.session_state.ocultar_valores
    novo_estado_priv = st.toggle("👁️ Ocultar Valores R$", value=estado_atual_priv, key="toggle_privacidade_topo")
    if novo_estado_priv != estado_atual_priv:
        st.session_state.ocultar_valores = novo_estado_priv
        st.rerun()
with col_tit3:
    st.write("")
    if st.button("🔄 Reiniciar Demonstração"):
        reiniciar_dados_demo()
        st.success("Painel reiniciado com sucesso!")
        st.rerun()

st.markdown("Acompanhe o orçamento do mês e gerencie seus objetivos estratégicos de investimento.")

# =====================================================================
# 10. BOTÃO DE ENVIO DO RELATÓRIO COMPLETO PARA O TELEGRAM
# =====================================================================
if st.button("🤖 Enviar Relatório Financeiro Completo para o Telegram"):
    rend = total_rendimentos_geral
    desp = total_despesas_geral
    sobra = sobra_mes_geral
    
    teto_alim_envio = st.session_state.get("teto_alim", 2500.0)
    teto_comb_envio = st.session_state.get("teto_comb", 1200.0)
    
    saldo_alim = teto_alim_envio - total_alim
    saldo_comb = teto_comb_envio - total_comb
    
    p_res = st.session_state.get("slider_reserva", 50)
    p_cur = st.session_state.get("slider_curto", 20)
    p_med = st.session_state.get("slider_medio", 10)
    p_lon = st.session_state.get("slider_longo", 20)
    
    v_res_envio = sobra * (p_res / 100) if sobra > 0 else 0.0
    v_cur_envio = sobra * (p_cur / 100) if sobra > 0 else 0.0
    v_med_envio = sobra * (p_med / 100) if sobra > 0 else 0.0
    v_lon_envio = sobra * (p_lon / 100) if sobra > 0 else 0.0
    
    mensagem_relatorio = (
        "RELATORIO FINANCEIRO DA DEMO\n\n"
        f"Rendimentos: R$ {rend:,.2f}\n"
        f"Despesas Totais: R$ {desp:,.2f}\n"
        f"Sobra para Investir: R$ {sobra:,.2f}\n\n"
        "--- DISTRIBUIÇÃO DE APORTES ---\n"
        f"• Reserva ({p_res}%): R$ {v_res_envio:,.2f}\n"
        f"• Curto Prazo ({p_cur}%): R$ {v_cur_envio:,.2f}\n"
        f"• Médio Prazo ({p_med}%): R$ {v_med_envio:,.2f}\n"
        f"• Longo Prazo ({p_lon}%): R$ {v_lon_envio:,.2f}\n\n"
        "--- CONTROLE DE VARIÁVEIS ---\n"
        f"Total Variáveis: R$ {total_variaveis:,.2f}\n"
        f"• Alimentação: R$ {total_alim:,.2f} (Saldo disp: R$ {saldo_alim:,.2f})\n"
        f"• Combustível: R$ {total_comb:,.2f} (Saldo disp: R$ {saldo_comb:,.2f})\n"
        f"• Outros: R$ {total_outros_var:,.2f}"
    )
    
    sucesso = enviar_alerta_telegram(mensagem_relatorio)
    if sucesso:
        st.success("Relatório completo enviado com sucesso para o seu Telegram!")
    else:
        st.error("Erro ao enviar. Verifique o console.")

st.divider()

# =====================================================================
# 11. FUNÇÕES DE COTAÇÃO, PREÇOS E BENCHMARKS (B3, IBOV, CDI)
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
# 12. ABAS PRINCIPAIS DO SISTEMA (PAINEL PRINCIPAL & INVESTIMENTOS)
# =====================================================================
aba_painel, aba_investimentos = st.tabs(["🏠 Painel Financeiro Principal", "📈 Gestão e Projeção de Investimentos"])

with aba_painel:
    # 12.1. BLOCO DE RENDIMENTOS
    st.subheader("1️⃣ Rendimento Mensal")
    col_r1, col_r2, col_r3, col_r4 = st.columns([1.5, 1.2, 1, 1])
    with col_r1: origem_renda = st.selectbox("Origem do Rendimento", ["Salário 1", "Salário 2", "Renda Extra / Variável", "Outros"])
    with col_r2: val_renda = st.number_input("Valor (R$)", min_value=0.0, step=100.0, format="%.2f", key="input_renda_val")
    with col_r3: mes_lancamento = st.text_input("Mês / Ano", value=mes_atual_str)
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
        with st.expander("📋 Ver / Gerenciar Histórico de Rendimentos (Edição permitida apenas no mês atual)", expanded=False):
            df_rend_view = st.session_state.df_rendimentos.copy()
            df_rend_view.insert(0, "Excluir", False)
            
            def status_linha_renda(row):
                return "Atual" if str(row.get("Mês/Ano", "")) == mes_atual_str else "Passado (Bloqueado)"
            
            df_rend_view["Status Mês"] = df_rend_view.apply(status_linha_renda, axis=1)

            df_rend_editado = st.data_editor(
                df_rend_view,
                column_config={
                    "Excluir": st.column_config.CheckboxColumn("🗑️ Excluir", default=False),
                    "Data": st.column_config.TextColumn("Data de Lançamento", disabled=True),
                    "Mês/Ano": st.column_config.TextColumn("Mês/Ano", disabled=True),
                    "Origem / Categoria": st.column_config.TextColumn("Origem", disabled=True),
                    "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0),
                    "Status Mês": st.column_config.TextColumn("Status", disabled=True)
                },
                hide_index=True, use_container_width=True, key="editor_rendimentos_flexivel"
            )

            df_final_rend = []
            tentativa_alteracao_passado = False
            for idx, row in df_rend_editado.iterrows():
                original = st.session_state.df_rendimentos.iloc[idx]
                is_mes_atual = (str(original["Mês/Ano"]) == mes_atual_str)
                
                if row["Excluir"] == True:
                    if is_mes_atual:
                        continue
                    else:
                        st.warning(f"⚠️ O rendimento de '{original['Origem / Categoria']}' ({original['Mês/Ano']}) pertence ao passado e não pode ser deletado!")
                
                if not is_mes_atual and float(row["Valor (R$)"]) != float(original["Valor (R$)"]):
                    tentativa_alteracao_passado = True
                    val_final = float(original["Valor (R$)"])
                else:
                    val_final = float(row["Valor (R$)"]) if is_mes_atual else float(original["Valor (R$)"])

                df_final_rend.append({
                    "Data": original["Data"],
                    "Mês/Ano": original["Mês/Ano"],
                    "Origem / Categoria": original["Origem / Categoria"],
                    "Valor (R$)": val_final
                })

            if st.button("💾 Salvar Alterações / Exclusões de Rendimentos"):
                st.session_state.df_rendimentos = pd.DataFrame(df_final_rend)
                if tentativa_alteracao_passado:
                    st.warning("⚠️ Você tentou alterar valores em meses passados. Essas alterações foram descartadas e os valores originais foram preservados.")
                else:
                    st.success("Histórico de rendimentos atualizado com sucesso!")
                st.rerun()

            st.write("---")
            st.write("🗑️ **Zona de Perigo: Limpar Histórico de Rendimentos**")
            confirmar_limpeza = st.checkbox("Confirmo que desejo apagar todo o histórico de rendimentos (Atenção: esta ação é irreversível)", key="chk_confirma_limpeza")
            if confirmar_limpeza:
                if st.button("🚨 Apagar Todo o Histórico de Rendimentos"):
                    st.session_state.df_rendimentos = pd.DataFrame(columns=["Data", "Mês/Ano", "Origem / Categoria", "Valor (R$)"])
                    st.success("Histórico de rendimentos apagado com segurança.")
                    st.rerun()

    rendimento_formatado = fmt_moeda(total_rendimentos_geral)
    st.info(f"**Total de Rendimentos do Mês ({mes_atual_str}):** {rendimento_formatado}")

    st.divider()

    # 12.2. BLOCO DE CONTAS E DESPESAS (FIXAS, PARCELADAS, VARIÁVEIS)
    st.subheader("2️⃣ Lançamento de Contas e Despesas")
    aba_fixas, aba_parceladas, aba_variaveis = st.tabs(["📌 Contas Fixas", "💳 Contas Parceladas", "🛒 Variáveis"])

    with aba_fixas:
        if not st.session_state.df_fixas.empty:
            with st.expander("📋 Ver / Editar Lista de Contas Fixas", expanded=False):
                df_editado = st.data_editor(
                    st.session_state.df_fixas,
                    column_config={
                        "Excluir": st.column_config.CheckboxColumn("🗑️ Excluir", default=False),
                        "Descrição": st.column_config.TextColumn("Descrição"),
                        "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0, step=10.0)
                    },
                    hide_index=True, use_container_width=True, key="editor_fixas"
                )
                st.session_state.df_fixas = df_editado
                if st.button("🗑️ Remover Fixas Selecionadas"):
                    st.session_state.df_fixas = st.session_state.df_fixas[st.session_state.df_fixas["Excluir"] == False]
                    st.rerun()

        with st.form("form_fixas", clear_on_submit=True):
            st.write("Adicionar Conta Fixa:")
            c1, c2 = st.columns(2)
            with c1: desc_fixa = st.text_input("Descrição")
            with c2: val_fixa = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
            if st.form_submit_button("Adicionar") and desc_fixa:
                nova_linha = pd.DataFrame([[False, desc_fixa, float(val_fixa)]], columns=["Excluir", "Descrição", "Valor (R$)"])
                st.session_state.df_fixas = pd.concat([st.session_state.df_fixas, nova_linha], ignore_index=True)
                st.rerun()

        fixas_fmt = fmt_moeda(total_fixas)
        st.info(f"**Total de Contas Fixas:** {fixas_fmt}")

    with aba_parceladas:
        if not st.session_state.df_parceladas.empty:
            df_p_view = st.session_state.df_parceladas.copy()
            
            def calcular_status_parcelamento(row):
                try:
                    mes_inicio_str = str(row['Mês Início'])
                    partes = mes_inicio_str.split('/')
                    mes_i = int(partes[0])
                    ano_i = int(partes[1])
                    total_parc = int(row['Total Parcelas'])
                    
                    mes_f = mes_i + total_parc - 1
                    ano_f = ano_i
                    while mes_f > 12:
                        mes_f -= 12
                        ano_f += 1
                        
                    mes_quitacao_str = f"{mes_f:02d}/{ano_f}"
                    
                    hoje = datetime.now()
                    mes_atual = hoje.month
                    ano_atual = hoje.year
                    
                    if (ano_f < ano_atual) or (ano_f == ano_atual and mes_f < mes_atual):
                        status = "🔴 Quitado (Para Deletar)"
                    else:
                        status = "🟢 Em Andamento"
                        
                    return pd.Series([mes_quitacao_str, status])
                except Exception:
                    return pd.Series(["Data Inválida", "Erro"])

            df_p_view[['Mês Quitação', 'Status']] = df_p_view.apply(calcular_status_parcelamento, axis=1)
            df_p_view.insert(0, "Excluir", False)

            with st.expander("📋 Ver / Gerenciar Lista de Contas Parceladas", expanded=True):
                quitadas_count = (df_p_view['Status'] == "🔴 Quitado (Para Deletar)").sum()
                if quitadas_count > 0:
                    st.warning(f"⚠️ Atenção: Existem **{quitadas_count}** contas parceladas com status **Quitado** que podem ser removidas da lista!")
                else:
                    st.success("✅ Nenhuma conta parcelada quitada pendente de remoção no momento.")

                df_editado_p = st.data_editor(
                    df_p_view,
                    column_config={
                        "Excluir": st.column_config.CheckboxColumn("🗑️ Excluir", default=False),
                        "Descrição": st.column_config.TextColumn("Descrição", disabled=True),
                        "Valor Parcela": st.column_config.NumberColumn("Valor Parcela", format="R$ %.2f", disabled=True),
                        "Total Parcelas": st.column_config.NumberColumn("Total", disabled=True),
                        "Mês Início": st.column_config.TextColumn("Início", disabled=True),
                        "Mês Quitação": st.column_config.TextColumn("Quitação", disabled=True),
                        "Status": st.column_config.TextColumn("Status", disabled=True)
                    },
                    hide_index=True, use_container_width=True, key="editor_parceladas_interativo"
                )

                if st.button("🗑️ Remover Parceladas Selecionadas"):
                    linhas_para_manter = df_editado_p["Excluir"] == False
                    st.session_state.df_parceladas = df_editado_p[linhas_para_manter][['Descrição', 'Valor Parcela', 'Total Parcelas', 'Mês Início']].reset_index(drop=True)
                    st.success("Contas selecionadas removidas com sucesso!")
                    st.rerun()

        with st.form("form_parceladas", clear_on_submit=True):
            st.write("Adicionar Nova Conta Parcelada:")
            p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
            with p1: desc_parc = st.text_input("Descrição Compra")
            with p2: val_parc = st.number_input("Valor Parcela", min_value=0.0, step=10.0, format="%.2f")
            with p3: total_parc = st.number_input("Total Parcelas", min_value=1, value=5, step=1)
            with p4: mes_inicio_parc = st.text_input("Mês Início", value=mes_atual_str)
            
            if st.form_submit_button("Adicionar Parcela") and desc_parc:
                nova_p = pd.DataFrame([[desc_parc, float(val_parc), int(total_parc), mes_inicio_parc]], columns=["Descrição", "Valor Parcela", "Total Parcelas", "Mês Início"])
                st.session_state.df_parceladas = pd.concat([st.session_state.df_parceladas, nova_p], ignore_index=True)
                st.rerun()

        parceladas_fmt = fmt_moeda(total_parceladas)
        st.info(f"**Total de Contas Parceladas do Mês:** {parceladas_fmt}")

    with aba_variaveis:
        st.write("### ⚙️ Definição de Setpoints (Tetos de Gastos Variáveis)")
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            teto_alim = st.number_input("Teto Alimentação / Mercado (R$)", min_value=0.0, step=100.0, value=2500.0, format="%.2f", key="teto_alim")
        with col_st2:
            teto_comb = st.number_input("Teto Combustível (R$)", min_value=0.0, step=100.0, value=1200.0, format="%.2f", key="teto_comb")

        st.divider()

        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1: cat_escolhida = st.selectbox("Categoria", ["Mercado / Alimentação", "Combustível", "Outros"])
        with col_v2: val_gasto = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", key="input_gasto")
        with col_v3:
            st.write("")
            st.write("")
            btn_lancar = st.button("Lançar Gasto")

        if btn_lancar and val_gasto > 0:
            data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
            novo_gasto = pd.DataFrame([[data_hoje, cat_escolhida, float(val_gasto)]], columns=["Data", "Categoria", "Valor (R$)"])
            st.session_state.df_variaveis = pd.concat([st.session_state.df_variaveis, novo_gasto], ignore_index=True)
            st.rerun()

        if not st.session_state.df_variaveis.empty:
            with st.expander(f"🛒 Ver Histórico de Gastos Variáveis", expanded=False):
                st.dataframe(st.session_state.df_variaveis, use_container_width=True)
                
                st.write("---")
                confirmar_limp_var = st.checkbox("Confirmo que desejo limpar o histórico de variáveis", key="chk_limp_var")
                if confirmar_limp_var:
                    if st.button("🗑️ Limpar Histórico de Variáveis (Virada de Mês)"):
                        st.session_state.df_variaveis = pd.DataFrame(columns=["Data", "Categoria", "Valor (R$)"])
                        st.rerun()

        st.write("")
        st.write("### 📊 Raio-X dos Gastos Variáveis")
        
        c1_val = fmt_moeda(total_variaveis)
        c2_val = fmt_moeda(total_alim)
        c3_val = fmt_moeda(total_comb)
        c4_val = fmt_moeda(total_outros_var)
        teto_alim_fmt = fmt_moeda(teto_alim)
        teto_comb_fmt = fmt_moeda(teto_comb)
        
        st.info(
            f"**Total Variáveis:** {c1_val}  |  "
            f"**Alimentação / Mercado:** {c2_val} (Teto: {teto_alim_fmt})  |  "
            f"**Combustível:** {c3_val} (Teto: {teto_comb_fmt})  |  "
            f"**Outros:** {c4_val}"
        )

    st.divider()

    # 12.3. BLOCO DE RESUMO GERAL E ROBÔ DE SAÚDE FINANCEIRA
    st.subheader("3️⃣ Resumo Geral do Mês")
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Total Rendimentos", fmt_moeda(total_rendimentos_geral))
    col_res2.metric("Total Despesas", fmt_moeda(total_despesas_geral))

    if sobra_mes_geral >= 0:
        col_res3.metric("Sobrando para Investir", fmt_moeda(sobra_mes_geral), delta="Positivo")
    else:
        col_res3.metric("Saldo do Mês", fmt_moeda(sobra_mes_geral), delta="Negativo", delta_color="inverse")

    st.write("")
    st.write("### 🤖 Robô de Raio-X: Diagnóstico de Saúde Financeira")
    
    if total_rendimentos_geral > 0:
        taxa_poupanca = (sobra_mes_geral / total_rendimentos_geral) * 100.0
        pct_fixas = (total_fixas / total_rendimentos_geral) * 100.0
        pct_parceladas = (total_parceladas / total_rendimentos_geral) * 100.0
        pct_variaveis = (total_variaveis / total_rendimentos_geral) * 100.0
    else:
        taxa_poupanca = pct_fixas = pct_parceladas = pct_variaveis = 0.0

    col_rx1, col_rx2, col_rx3, col_rx4 = st.columns(4)
    col_rx1.metric("Taxa de Poupança", f"{taxa_poupanca:.1f}%", delta="Ideal: > 20%")
    col_rx2.metric("Comprometimento Fixas", f"{pct_fixas:.1f}%", delta="Ideal: < 50%", delta_color="inverse")
    col_rx3.metric("Comprometimento Parcelas", f"{pct_parceladas:.1f}%", delta="Ideal: < 15%", delta_color="inverse")
    col_rx4.metric("Consumo Variável", f"{pct_variaveis:.1f}%", delta="Ideal: < 30%", delta_color="inverse")

    with st.container():
        st.markdown("---")
        if sobra_mes_geral < 0:
            st.error(
                "🚨 **ALERTA CRITICO DE DESEQUILÍBRIO (SAIU DOS TRILHOS):** "
                f"Suas despesas totais superam seus rendimentos em **{fmt_moeda(abs(sobra_mes_geral))}**! "
                "Isso compromete severamente sua qualidade de vida e segurança futura. "
                "**Ação imediata:** Reveja contas fixas e reduza drasticamente os gastos variáveis até zerar o déficit."
            )
        elif taxa_poupanca >= 20.0 and pct_fixas <= 50.0 and pct_parceladas <= 15.0:
            st.success(
                f"🟢 **DIAGNÓSTICO PRÓSPERO E SEGURO:** Parabéns! Você está gerindo seu mês com excelência. "
                f"Sua taxa de poupança está em **{taxa_poupanca:.1f}%**, garantindo alta capacidade de investimento para seus objetivos de médio e longo prazo, "
                "mantendo uma vida próspera e sem sufocos."
            )
        else:
            pontos_fortes, pontos_fracos, alertas = [], [], []
            if taxa_poupanca >= 15.0: pontos_fortes.append(f"Boa taxa de poupança mensal ({taxa_poupanca:.1f}%).")
            else: pontos_fracos.append(f"Taxa de poupança abaixo do ideal recomendável de 20% (atual: {taxa_poupanca:.1f}%).")

            if pct_fixas <= 50.0: pontos_fortes.append(f"Contas fixas sob controle ({pct_fixas:.1f}% da renda).")
            else: pontos_fracos.append(f"Custos fixos elevados ({pct_fixas:.1f}%), engessando o orçamento.")

            if pct_parceladas <= 15.0: pontos_fortes.append("Baixo endividamento com compras parceladas.")
            else: alertas.append(f"Cartão/Parcelamentos pesados consumindo {pct_parceladas:.1f}% da renda — risco de comprometer os próximos meses.")

            if pct_variaveis > 35.0: alertas.append(f"Gastos variáveis elevados ({pct_variaveis:.1f}%). Atenção com mercado e supérfluos.")

            msg_rx = "### 📋 Parecer Detalhado do Raio-X:\n"
            if pontos_fortes: msg_rx += "* **💪 Pontos Fortes:** " + " | ".join(pontos_fortes) + "\n"
            if pontos_fracos: msg_rx += "* **⚠️ Pontos de Atenção:** " + " | ".join(pontos_fracos) + "\n"
            if alertas: msg_rx += "* **🚨 Alertas de Risco (Rumo aos Trilhos):** " + " | ".join(alertas) + "\n"
            st.warning(msg_rx)

    st.divider()

    # 12.4. BLOCO DE ALOCAÇÃO INTELIGENTE DE INVESTIMENTOS
    st.subheader("4️⃣ Alocação Inteligente de Investimentos")
    col1, col2, col3, col4 = st.columns(4)
    with col1: 
        pct_reserva = st.slider("Reserva (%)", 0, 100, 50, key="slider_reserva")
        val_res_bloco4 = sobra_mes_geral * (pct_reserva / 100) if sobra_mes_geral > 0 else 0.0
        st.write(f"**{fmt_moeda(val_res_bloco4)}**")
    with col2: 
        pct_curto = st.slider("Curto Prazo (%)", 0, 100, 20, key="slider_curto")
        val_curto_bloco4 = sobra_mes_geral * (pct_curto / 100) if sobra_mes_geral > 0 else 0.0
        st.write(f"**{fmt_moeda(val_curto_bloco4)}**")
    with col3: 
        pct_medio = st.slider("Médio Prazo (%)", 0, 100, 10, key="slider_medio")
        val_medio_bloco4 = sobra_mes_geral * (pct_medio / 100) if sobra_mes_geral > 0 else 0.0
        st.write(f"**{fmt_moeda(val_medio_bloco4)}**")
    with col4: 
        pct_longo = st.slider("Longo Prazo (%)", 0, 100, 20, key="slider_longo")
        val_longo_bloco4 = sobra_mes_geral * (pct_longo / 100) if sobra_mes_geral > 0 else 0.0
        st.write(f"**{fmt_moeda(val_longo_bloco4)}**")

    soma_pct = pct_reserva + pct_curto + pct_medio + pct_longo
    if soma_pct != 100:
        st.error(f"⚠️ A soma deve dar exatamente 100% (Atual: {soma_pct}%)")

with aba_investimentos:
    sub_resumo_mes, sub_reserva, sub_curto_medio_prev, sub_longo, sub_proj, sub_analise_renda = st.tabs([
        "📋 Resumo e Metas do Mês",
        "🛡️ Reserva de Emergência",
        "🎯 Curto, Médio Prazo & Previdência",
        "🏛️ Carteira Longo Prazo",
        "🔮 Projeções",
        "📊 Análise de Renda & IPCA"
    ])

    # 12.5. SUB-ABA: RESUMO E METAS DO MÊS
    with sub_resumo_mes:
        st.write("### 📋 Resumo dos Valores Calculados no Painel Principal")
        st.info(f"Sobra livre disponível para alocação no mês ({mes_atual_str}): **{fmt_moeda(sobra_mes_geral)}**")
        
        v_res = sobra_mes_geral * (pct_reserva / 100) if sobra_mes_geral > 0 else 0.0
        v_cur = sobra_mes_geral * (pct_curto / 100) if sobra_mes_geral > 0 else 0.0
        v_med = sobra_mes_geral * (pct_medio / 100) if sobra_mes_geral > 0 else 0.0
        v_lon = sobra_mes_geral * (pct_longo / 100) if sobra_mes_geral > 0 else 0.0

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Reserva de Emergência", f"{pct_reserva}%", fmt_moeda(v_res))
        rc2.metric("Curto Prazo", f"{pct_curto}%", fmt_moeda(v_cur))
        rc3.metric("Médio Prazo", f"{pct_medio}%", fmt_moeda(v_med))
        rc4.metric("Longo Prazo", f"{pct_longo}%", fmt_moeda(v_lon))

    # 12.6. SUB-ABA: RESERVA DE EMERGÊNCIA (6 MESES)
    with sub_reserva:
        st.write("### 🛡️ Reserva de Emergência")
        sug_reserva = sobra_mes_geral * (pct_reserva / 100) if sobra_mes_geral > 0 else 0.0
        st.info(f"💡 **Aporte Sugerido para o Mês:** {fmt_moeda(sug_reserva)}")

        df_res = st.session_state.df_reserva.copy()
        df_res["Aporte Acumulado (R$)"] = pd.to_numeric(df_res["Aporte Acumulado (R$)"], errors="coerce").fillna(0.0)
        df_res["Saldo Atual (R$)"] = pd.to_numeric(df_res["Saldo Atual (R$)"], errors="coerce").fillna(0.0)
        df_res["Rendimento (R$)"] = df_res["Saldo Atual (R$)"] - df_res["Aporte Acumulado (R$)"]

        df_res_edit = st.data_editor(
            df_res[["Ativo / Descrição", "Aporte Acumulado (R$)", "Saldo Atual (R$)", "Rendimento (R$)"]],
            column_config={
                "Ativo / Descrição": st.column_config.TextColumn("Ativo / Banco"),
                "Aporte Acumulado (R$)": st.column_config.NumberColumn("Total Investido (R$)", format="R$ %.2f", min_value=0.0),
                "Saldo Atual (R$)": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f", min_value=0.0),
                "Rendimento (R$)": st.column_config.NumberColumn("Rendimento Ganho (R$)", format="R$ %.2f", disabled=True)
            },
            hide_index=True, use_container_width=True, key="editor_reserva"
        )

        st.session_state.df_reserva["Ativo / Descrição"] = df_res_edit["Ativo / Descrição"]
        st.session_state.df_reserva["Aporte Acumulado (R$)"] = df_res_edit["Aporte Acumulado (R$)"]
        st.session_state.df_reserva["Saldo Atual (R$)"] = df_res_edit["Saldo Atual (R$)"]

        tot_ap_res = st.session_state.df_reserva["Aporte Acumulado (R$)"].sum()
        tot_sal_res = st.session_state.df_reserva["Saldo Atual (R$)"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Investido", fmt_moeda(tot_ap_res))
        m2.metric("Saldo Atual Na Conta", fmt_moeda(tot_sal_res))
        m3.metric("Lucro / Rendimento", fmt_moeda(tot_sal_res - tot_ap_res))

        st.divider()
        custo_mensal_total = total_fixas + total_variaveis
        meta_reserva_ideal = custo_mensal_total * 6
        progresso_reserva = (tot_sal_res / meta_reserva_ideal * 100.0) if meta_reserva_ideal > 0 else 0.0
        progresso_reserva = min(progresso_reserva, 100.0)

        mr1, mr2 = st.columns(2)
        mr1.metric("Meta Ideal da Reserva (6x Custo Mensal)", fmt_moeda(meta_reserva_ideal))
        mr2.metric("Progresso Atual", f"{progresso_reserva:.1f}%")
        st.progress(float(progresso_reserva / 100.0), text=f"Termômetro da Meta de Reserva: {progresso_reserva:.1f}% concluído")

    # 12.7. SUB-ABA: CURTO, MÉDIO PRAZO E PREVIDÊNCIA
    with sub_curto_medio_prev:
        st.write("### 🟢 Curto Prazo (Ativo Único & Alta Liquidez)")
        sug_curto = sobra_mes_geral * (pct_curto / 100) if sobra_mes_geral > 0 else 0.0
        st.info(f"💡 **Aporte Sugerido para Curto Prazo no Mês:** {fmt_moeda(sug_curto)}")

        df_c = st.session_state.df_obj_curto.copy()
        df_c["Meta Global (R$)"] = pd.to_numeric(df_c["Meta Global (R$)"], errors="coerce").fillna(0.0)
        df_c["Aporte Acumulado (R$)"] = pd.to_numeric(df_c["Aporte Acumulado (R$)"], errors="coerce").fillna(0.0)
        df_c["Saldo Atual (R$)"] = pd.to_numeric(df_c["Saldo Atual (R$)"], errors="coerce").fillna(0.0)

        rend_c_list, prog_c_list, tempo_c_list = [], [], []
        tot_meta_c = df_c["Meta Global (R$)"].max() if not df_c.empty else 0.0

        for idx, row in df_c.iterrows():
            sal = float(row["Saldo Atual (R$)"])
            apo = float(row["Aporte Acumulado (R$)"])
            meta = float(row["Meta Global (R$)"])
            
            rend_c_list.append(sal - apo)
            prog = (sal / meta * 100.0) if meta > 0 else 0.0
            prog_c_list.append(f"{min(prog, 100.0):.1f}%")
            
            falta = meta - sal
            if falta <= 0:
                tempo_c_list.append("🎯 Concluída!")
            elif sug_curto > 0:
                meses_nec = falta / sug_curto
                anos = int(meses_nec // 12)
                meses = int(meses_nec % 12)
                if anos > 0:
                    tempo_c_list.append(f"~ {anos}a {meses}m")
                else:
                    tempo_c_list.append(f"~ {meses} meses")
            else:
                tempo_c_list.append("Sem aporte")

        df_c["Rendimento (R$)"] = rend_c_list
        df_c["Progresso (%)"] = prog_c_list
        df_c["Tempo p/ Meta"] = tempo_c_list

        df_c_edit = st.data_editor(
            df_c[["Objetivo", "Ativo / Liquidez", "Meta Global (R$)", "Aporte Acumulado (R$)", "Saldo Atual (R$)", "Rendimento (R$)", "Progresso (%)", "Tempo p/ Meta"]],
            num_rows="dynamic",
            column_config={
                "Objetivo": st.column_config.TextColumn("Objetivo (Ex: Carro)"),
                "Ativo / Liquidez": st.column_config.TextColumn("Ativo"),
                "Meta Global (R$)": st.column_config.NumberColumn("Meta (R$)", format="R$ %.2f"),
                "Aporte Acumulado (R$)": st.column_config.NumberColumn("Total Investido (R$)", format="R$ %.2f"),
                "Saldo Atual (R$)": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f"),
                "Rendimento (R$)": st.column_config.NumberColumn("Rendimento", format="R$ %.2f", disabled=True),
                "Progresso (%)": st.column_config.TextColumn("Progresso", disabled=True),
                "Tempo p/ Meta": st.column_config.TextColumn("Tempo p/ Meta", disabled=True)
            },
            hide_index=True, use_container_width=True, key="editor_curto"
        )

        st.session_state.df_obj_curto = df_c_edit[["Objetivo", "Ativo / Liquidez", "Meta Global (R$)", "Aporte Acumulado (R$)", "Saldo Atual (R$)"]]
        
        tot_sal_c_AT = df_c_edit["Saldo Atual (R$)"].sum()
        progresso_curto_total = (tot_sal_c_AT / tot_meta_c * 100.0) if tot_meta_c > 0 else 0.0
        progresso_curto_total = min(progresso_curto_total, 100.0)
        st.progress(float(progresso_curto_total / 100.0), text=f"Termômetro da Meta de Curto Prazo: {progresso_curto_total:.1f}% concluído")

        st.divider()
        st.write("### 🔵 Médio Prazo (Estrutura Enxuta em 4 Ativos)")
        sug_medio = sobra_mes_geral * (pct_medio / 100) if sobra_mes_geral > 0 else 0.0
        st.info(f"💡 **Aporte Sugerido para Médio Prazo no Mês:** {fmt_moeda(sug_medio)}")

        meta_medio_global = st.number_input("🎯 Meta Global do Médio Prazo (R$)", min_value=0.0, step=1000.0, value=50000.0, format="%.2f", key="input_meta_medio")

        df_m = st.session_state.df_obj_medio.copy()
        df_m["Aporte Acumulado (R$)"] = pd.to_numeric(df_m["Aporte Acumulado (R$)"], errors="coerce").fillna(0.0)
        df_m["Saldo Atual (R$)"] = pd.to_numeric(df_m["Saldo Atual (R$)"], errors="coerce").fillna(0.0)
        df_m["Rendimento (R$)"] = df_m["Saldo Atual (R$)"] - df_m["Aporte Acumulado (R$)"]

        df_m_edit = st.data_editor(
            df_m[["Categoria / Estratégia", "Ativo Vinculado", "Aporte Acumulado (R$)", "Saldo Atual (R$)", "Rendimento (R$)"]],
            column_config={
                "Categoria / Estratégia": st.column_config.TextColumn("Estratégia", disabled=True),
                "Ativo Vinculado": st.column_config.TextColumn("Ativo / Descrição"),
                "Aporte Acumulado (R$)": st.column_config.NumberColumn("Total Investido (R$)", format="R$ %.2f"),
                "Saldo Atual (R$)": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f"),
                "Rendimento (R$)": st.column_config.NumberColumn("Rendimento (R$)", format="R$ %.2f", disabled=True)
            },
            hide_index=True, use_container_width=True, key="editor_medio"
        )

        st.session_state.df_obj_medio["Ativo Vinculado"] = df_m_edit["Ativo Vinculado"]
        st.session_state.df_obj_medio["Aporte Acumulado (R$)"] = df_m_edit["Aporte Acumulado (R$)"]
        st.session_state.df_obj_medio["Saldo Atual (R$)"] = df_m_edit["Saldo Atual (R$)"]

        tot_ap_m = df_m_edit["Aporte Acumulado (R$)"].sum()
        tot_sal_m = df_m_edit["Saldo Atual (R$)"].sum()
        tot_rend_m = tot_sal_m - tot_ap_m

        st.write("")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Total Aportado (Médio Prazo)", fmt_moeda(tot_ap_m))
        mc2.metric("Saldo Total Atual (Médio Prazo)", fmt_moeda(tot_sal_m))
        mc3.metric("Rendimento Total", fmt_moeda(tot_rend_m))

        progresso_medio_total = (tot_sal_m / meta_medio_global * 100.0) if meta_medio_global > 0 else 0.0
        progresso_medio_total = min(progresso_medio_total, 100.0)
        st.progress(float(progresso_medio_total / 100.0), text=f"Termômetro da Meta de Médio Prazo: {progresso_medio_total:.1f}% concluído")

        st.divider()
        st.write("### 🏛️ Previdência Privada Cooperativa (Dobra Patronal)")
        st.info("ℹ️ O desconto em folha é multiplicado por 2 (dobra da empresa). O saldo atual considera seu patrimônio histórico acumulado.")

        df_prev = st.session_state.df_previdencia.copy()
        
        col_prev1, col_prev2 = st.columns(2)
        with col_prev1:
            desc_folha = st.number_input("Desconto Mensal em Folha (R$)", min_value=0.0, step=10.0, value=float(df_prev.loc[0, "Desconto Mensal Folha (R$)"] if not df_prev.empty else 560.0), format="%.2f")
        with col_prev2:
            aportes_anteriores = st.number_input("Total Aportes Anteriores / Acumulados (R$)", min_value=0.0, step=1000.0, value=float(df_prev.loc[0, "Total Aportes Anteriores / Acumulados (R$)"] if not df_prev.empty and "Total Aportes Anteriores / Acumulados (R$)" in df_prev.columns else 150000.0), format="%.2f")

        df_prev["Desconto Mensal Folha (R$)"] = desc_folha
        df_prev["Total Aportes Anteriores / Acumulados (R$)"] = aportes_anteriores

        df_prev_editado = st.data_editor(
            df_prev[["Instituição / Descrição", "Saldo Atual (R$)"]],
            num_rows="dynamic",
            column_config={
                "Instituição / Descrição": st.column_config.TextColumn("Instituição / Plano", required=True),
                "Saldo Atual (R$)": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f", min_value=0.0, step=100.0)
            },
            hide_index=True, use_container_width=True, key="editor_previdencia"
        )
        st.session_state.df_previdencia["Instituição / Descrição"] = df_prev_editado["Instituição / Descrição"]
        st.session_state.df_previdencia["Saldo Atual (R$)"] = df_prev_editado["Saldo Atual (R$)"]
        st.session_state.df_previdencia["Desconto Mensal Folha (R$)"] = desc_folha
        st.session_state.df_previdencia["Total Aportes Anteriores / Acumulados (R$)"] = aportes_anteriores

        aporte_mensal_com_dobra = desc_folha * 2.0
        saldo_total_prev = pd.to_numeric(st.session_state.df_previdencia["Saldo Atual (R$)"], errors="coerce").sum()
        total_investido_prev = aportes_anteriores + aporte_mensal_com_dobra
        rendimento_prev_rs = saldo_total_prev - total_investido_prev
        rentabilidade_prev_pct = (saldo_total_prev / total_investido_prev * 100.0 - 100.0) if total_investido_prev > 0 else 0.0

        st.write("")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Aporte Mensal (c/ Dobra)", fmt_moeda(aporte_mensal_com_dobra))
        p2.metric("Saldo Acumulado Total", fmt_moeda(saldo_total_prev))
        p3.metric("Rendimento Total (R$)", fmt_moeda(rendimento_prev_rs))
        p4.metric("Rentabilidade Geral (%)", f"{rentabilidade_prev_pct:.2f}%", delta="Lucro Histórico")

    # 12.8. SUB-ABA: CARTEIRA DE LONGO PRAZO
    with sub_longo:
        st.write("### 🏛️ Carteira de Longo Prazo (Buy & Hold / Rebalanceamento Ativo)")
        
        tot_longo_mes = sobra_mes_geral * (pct_longo / 100) if sobra_mes_geral > 0 else 0.0
        st.info(f"💎 **Valor Total Destinado a Longo Prazo no Mês:** {fmt_moeda(tot_longo_mes)}")

        st.write("#### ⚖️ Setpoints de Alocação de Longo Prazo (%)")
        col_lp1, col_lp2, col_lp3, col_lp4 = st.columns(4)
        with col_lp1:
            set_rf = st.slider("Reserva de Oportunidade (%)", 0, 100, 30, key="set_rf")
            st.write(f"**{fmt_moeda(tot_longo_mes * (set_rf/100))}**")
        with col_lp2:
            set_acoes = st.slider("Ações (%)", 0, 100, 40, key="set_acoes")
            st.write(f"**{fmt_moeda(tot_longo_mes * (set_acoes/100))}**")
        with col_lp3:
            set_fii = st.slider("Fundos Imobiliários (%)", 0, 100, 20, key="set_fii")
            st.write(f"**{fmt_moeda(tot_longo_mes * (set_fii/100))}**")
        with col_lp4:
            set_etf = st.slider("ETFs (%)", 0, 100, 10, key="set_etf")
            st.write(f"**{fmt_moeda(tot_longo_mes * (set_etf/100))}**")

        soma_set_lp = set_rf + set_acoes + set_fii + set_etf
        if soma_set_lp != 100:
            st.error(f"⚠️ A soma dos setpoints de Longo Prazo deve dar exatamente 100% (Atualmente em {soma_set_lp}%)")
        else:
            st.divider()
            st.write("#### 🛡️ 1. Fatia de Renda Fixa / Reserva de Oportunidade")
            aporte_sug_rf = tot_longo_mes * (set_rf / 100.0)
            st.info(f"💡 **Aporte Sugerido para esta fatia:** {fmt_moeda(aporte_sug_rf)}")

            df_rf = st.session_state.df_rf_lp.copy()
            df_rf["Saldo Atual (R$)"] = pd.to_numeric(df_rf["Saldo Atual (R$)"], errors="coerce").fillna(0.0)

            df_rf_edit = st.data_editor(
                df_rf,
                num_rows="dynamic",
                column_config={
                    "Ativo / Descrição": st.column_config.TextColumn("Ativo / Descrição (Ex: Tesouro Selic)"),
                    "Saldo Atual (R$)": st.column_config.NumberColumn("Saldo Atual (R$)", format="R$ %.2f", min_value=0.0, step=100.0)
                },
                hide_index=True, use_container_width=True, key="editor_rf_lp"
            )
            st.session_state.df_rf_lp = df_rf_edit
            tot_sal_rf = pd.to_numeric(df_rf_edit["Saldo Atual (R$)"], errors="coerce").sum()

            st.success(f"📊 **Saldo Total Acumulado em Renda Fixa:** {fmt_moeda(tot_sal_rf)}")

            st.divider()
            st.write("#### 📈 2. Fatia de Renda Variável (Ações, FIIs, ETFs)")
            aporte_sug_rv = tot_longo_mes * ((set_acoes + set_fii + set_etf) / 100.0)
            st.info(f"💡 **Aporte Sugerido para Renda Variável no Mês:** {fmt_moeda(aporte_sug_rv)}")

            df_rv = st.session_state.df_rv_lp.copy()
            df_rv["Quantidade de Cotas"] = pd.to_numeric(df_rv["Quantidade de Cotas"], errors="coerce").fillna(0.0)

            precos_atuais, valores_totais, rentabilidades_ativos = [], [], []
            for idx, row in df_rv.iterrows():
                ticker = str(row["Ticker"]).strip()
                cotas = float(row["Quantidade de Cotas"])
                preco, rent_ativo = obter_preco_b3(ticker)
                precos_atuais.append(preco)
                valores_totais.append(cotas * preco)
                rentabilidades_ativos.append(rent_ativo)

            df_rv["Preço Atual (R$)"] = precos_atuais
            df_rv["Valor Acumulado (R$)"] = valores_totais
            tot_sal_rv_temp = sum(valores_totais)

            p_indiv = [(val / tot_sal_rv_temp * 100.0) if tot_sal_rv_temp > 0 else 0.0 for val in valores_totais]
            df_rv["% Individual (RV)"] = [f"{p:.2f}%" for p in p_indiv]
            df_rv["Rentabilidade (30d)"] = [f"{r:+.2f}%" for r in rentabilidades_ativos]

            df_rv_edit = st.data_editor(
                df_rv[["Classe", "Ticker", "Quantidade de Cotas", "Preço Atual (R$)", "Valor Acumulado (R$)", "% Individual (RV)", "Rentabilidade (30d)"]],
                num_rows="dynamic",
                column_config={
                    "Classe": st.column_config.SelectboxColumn("Classe", options=["Ações", "Fundos Imobiliários (FIIs)", "ETFs"], required=True),
                    "Ticker": st.column_config.TextColumn("Ticker B3 (Ex: PETR4.SA)"),
                    "Quantidade de Cotas": st.column_config.NumberColumn("Qtd Cotas", min_value=0.0, step=1.0),
                    "Preço Atual (R$)": st.column_config.NumberColumn("Preço Atual B3", format="R$ %.2f", disabled=True),
                    "Valor Acumulado (R$)": st.column_config.NumberColumn("Valor Acumulado", format="R$ %.2f", disabled=True),
                    "% Individual (RV)": st.column_config.TextColumn("% na Renda Variável", disabled=True),
                    "Rentabilidade (30d)": st.column_config.TextColumn("Rentabilidade (30d)", disabled=True)
                },
                hide_index=True, use_container_width=True, key="editor_rv_lp"
            )

            st.session_state.df_rv_lp = df_rv_edit[["Classe", "Ticker", "Quantidade de Cotas"]]
            
            tot_sal_rv, val_acoes_real, val_fii_real, val_etf_real, rentabilidade_ponderada_rv = 0.0, 0.0, 0.0, 0.0, 0.0

            for idx, row in st.session_state.df_rv_lp.iterrows():
                cotas = float(row["Quantidade de Cotas"])
                preco, rent_ativo = obter_preco_b3(row["Ticker"])
                val = cotas * preco
                tot_sal_rv += val
                
                if tot_sal_rv > 0:
                    rentabilidade_ponderada_rv += rent_ativo * (val / (tot_sal_rv if tot_sal_rv > 0 else 1))

                classe_lower = str(row["Classe"]).lower()
                if "ação" in classe_lower or "acoes" in classe_lower or "ações" in classe_lower:
                    val_acoes_real += val
                elif "fundo" in classe_lower or "fii" in classe_lower:
                    val_fii_real += val
                elif "etf" in classe_lower:
                    val_etf_real += val

            st.success(f"📊 **Saldo Total em Renda Variável:** {fmt_moeda(tot_sal_rv)}  \n"
                       f"🔹 **Ações:** {fmt_moeda(val_acoes_real)} | 🔸 **FIIs:** {fmt_moeda(val_fii_real)} | 🟩 **ETFs:** {fmt_moeda(val_etf_real)}")

            patrimonio_total_lp = tot_sal_rf + tot_sal_rv
            
            st.divider()
            st.write("### 📊 Consolidado e 'Teste do Sofá' (Performance da Renda Variável)")
            
            col_sel_bench, col_vazio_b = st.columns([1.5, 2.5])
            with col_sel_bench:
                escolha_benchmark = st.selectbox("🎯 Escolha o Benchmark de Comparação (Buy & Hold):", ["Ibovespa (^BVSP)", "CDI (Renda Fixa / Livre de Risco)"])

            p_rf = (tot_sal_rf / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0
            p_rv = (tot_sal_rv / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0

            ibov_perf = obter_benchmark_ibov()
            cdi_perf = obter_benchmark_cdi()

            valor_benchmark_escolhido = ibov_perf if "Ibovespa" in escolha_benchmark else cdi_perf
            delta_performance = rentabilidade_ponderada_rv - valor_benchmark_escolhido

            c_lp1, c_lp2, c_lp3, c_lp4 = st.columns(4)
            c_lp1.metric("Patrimônio Total LP", fmt_moeda(patrimonio_total_lp))
            c_lp2.metric("Alocação Renda Fixa", fmt_moeda(tot_sal_rf), delta=f"{p_rf:.1f}% (Meta: {set_rf}%)")
            c_lp3.metric("Rentabilidade Renda Variável", f"{rentabilidade_ponderada_rv:+.2f}%", delta=f"Sua Carteira (30d)")
            c_lp4.metric(f"Benchmark: {escolha_benchmark.split()[0]}", f"{valor_benchmark_escolhido:+.2f}%", delta=f"{delta_performance:+.2f}% vs Carteira", delta_color="normal" if delta_performance >= 0 else "inverse")

            st.write("")
            st.write("#### 🍩 Gráfico de Rosca: Metas Setadas vs. Realidade Atual")

            p_real_rf = (tot_sal_rf / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0
            p_real_acoes = (val_acoes_real / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0
            p_real_fii = (val_fii_real / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0
            p_real_etf = (val_etf_real / patrimonio_total_lp * 100.0) if patrimonio_total_lp > 0 else 0.0

            labels_cat = ["Reserva Oportunidade (RF)", "Ações", "Fundos Imobiliários", "ETFs"]
            metas_cat = [float(set_rf), float(set_acoes), float(set_fii), float(set_etf)]
            reais_cat = [round(p_real_rf, 2), round(p_real_acoes, 2), round(p_real_fii, 2), round(p_real_etf, 2)]

            cores_paleta = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

            fig = go.Figure()
            fig.add_trace(go.Pie(labels=labels_cat, values=metas_cat, hole=0.45, domain={'x': [0, 1], 'y': [0, 1]}, name="Setpoint (Meta)", textinfo='label+percent', marker=dict(colors=cores_paleta, line=dict(color='#FFFFFF', width=2))))
            fig.add_trace(go.Pie(labels=labels_cat, values=reais_cat, hole=0.68, domain={'x': [0, 1], 'y': [0, 1]}, name="Real Atual", textinfo='percent', marker=dict(colors=cores_paleta, line=dict(color='#FFFFFF', width=2))))

            fig.update_layout(
                title_text="<b>Centro = Setpoint (Meta)</b> | <b>Borda de Fora = Real Atual</b>",
                annotations=[dict(text='Metas<br>vs<br>Real', x=0.5, y=0.5, font_size=13, showarrow=False)],
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
                height=520
            )

            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.write("### 🤖 Robô de Aporte Inteligente (Diagnóstico de Rebalanceamento)")
            st.info(f"💡 Com base no valor total que você vai aportar este mês em Longo Prazo (**{fmt_moeda(tot_longo_mes)}**) e nos seus Setpoints, veja onde o dinheiro deve ser aplicado:")

            classes_nomes = ["Renda Fixa / Oportunidade", "Ações", "Fundos Imobiliários (FIIs)", "ETFs"]
            meta_pcts = [set_rf, set_acoes, set_fii, set_etf]
            real_pcts = [p_real_rf, p_real_acoes, p_real_fii, p_real_etf]
            real_valores = [tot_sal_rf, val_acoes_real, val_fii_real, val_etf_real]
            
            patrimonio_proj_total = patrimonio_total_lp + tot_longo_mes
            recomendacoes = []
            for nome, meta_p, real_p, real_v in zip(classes_nomes, meta_pcts, real_pcts, real_valores):
                meta_valor_ideal = patrimonio_proj_total * (meta_p / 100.0)
                deficit = meta_valor_ideal - real_v
                recomendacoes.append({"Classe": nome, "Meta (%)": f"{meta_p:.1f}%", "Real (%)": f"{real_p:.2f}%", "Atual (R$)": real_v, "Meta Ideal (R$)": meta_valor_ideal, "Déficit / Excesso (R$)": deficit})

            df_rec = pd.DataFrame(recomendacoes).sort_values(by="Déficit / Excesso (R$)", ascending=False)
            st.dataframe(df_rec.style.format({"Atual (R$)": "R$ {:,.2f}", "Meta Ideal (R$)": "R$ {:,.2f}", "Déficit / Excesso (R$)": "R$ {:,.2f}"}), use_container_width=True, hide_index=True)

            maior_deficit = df_rec.iloc[0]
            if maior_deficit["Déficit / Excesso (R$)"] > 0:
                st.success(f"🎯 **Sugestão de Ouro para o Aporte de Hoje:** Direcione o seu aporte mensal de Longo Prazo para **{maior_deficit['Classe']}**, pois é a classe que está mais abaixo da proporção ideal (com déficit de R$ {maior_deficit['Déficit / Excesso (R$)']:,.2f}).")
            else:
                st.success("🎉 Sua carteira está perfeitamente alinhada com as metas! Distribua o aporte proporcionalmente entre os setpoints.")

            bate_ibov = rentabilidade_ponderada_rv >= ibov_perf
            bate_cdi = rentabilidade_ponderada_rv >= cdi_perf

            if bate_ibov and bate_cdi:
                st.success(
                    f"🏆 **STATUS EXECUTIVO DO TESTE DO SOFÁ:** **APROVADO COM LOUVOR!** "
                    f"Sua Renda Variável (`+{rentabilidade_ponderada_rv:.2f}%`) está **ganhando** de ambos os principais KPIs de referência: "
                    f"Ibovespa (`+{ibov_perf:.2f}%`) e CDI (`+{cdi_perf:.2f}%`). O seu trabalho ativo e a alocação estão compensando plenamente!"
                )
            elif not bate_ibov and not bate_cdi:
                st.error(
                    f"🚨 **STATUS EXECUTIVO DO TESTE DO SOFÁ:** **ALERTA DE PERFORMANCE!** "
                    f"Sua Renda Variável (`+{rentabilidade_ponderada_rv:.2f}%`) está **perdendo** para o Ibovespa (`+{ibov_perf:.2f}%`) "
                    f"e também para o CDI (`+{cdi_perf:.2f}%`). Vale a pena reavaliar a tese dos ativos ou focar os aportes em Renda Fixa."
                )
            else:
                st.warning(
                    f"⚠️ **STATUS EXECUTIVO DO TESTE DO SOFÁ:** **DESEMPENHO MISTO.** "
                    f"Sua Renda Variável (`+{rentabilidade_ponderada_rv:.2f}%`) rende acima de um, mas abaixo do outro "
                    f"(Ibov: `+{ibov_perf:.2f}%` | CDI: `+{cdi_perf:.2f}%`). Acompanhe o próximo ciclo de fechamento."
                )

    # 12.9. SUB-ABA: PROJEÇÕES FUTURAS
    with sub_proj:
        st.write("### 🔮 Projeção de Futuro Próspero e Seguro")
        st.markdown("Acompanhe o crescimento composto da sua **Previdência Privada** e da **Carteira de Longo Prazo** ao longo do tempo.")

        col_pr1, col_pr2 = st.columns(2)
        with col_pr1:
            anos_proj = st.number_input("⏳ Horizonte de Projeção (Anos)", min_value=1, max_value=40, value=10, step=1)
        with col_pr2:
            taxa_juros_anual = st.number_input("📈 Taxa de Retorno Anual (%)", min_value=1.0, max_value=30.0, value=10.0, step=0.5) / 100.0
            st.write("💡 *Dica:* 8% a 10% a.a. (acima da inflação) é uma taxa realista.")

        taxa_juros_mensal = ((1.0 + taxa_juros_anual) ** (1.0 / 12.0)) - 1.0

        saldo_atual_prev = pd.to_numeric(st.session_state.df_previdencia["Saldo Atual (R$)"], errors="coerce").sum()
        desc_folha_prev = float(st.session_state.df_previdencia.loc[0, "Desconto Mensal Folha (R$)"] if not st.session_state.df_previdencia.empty else 560.0)
        aporte_mensal_prev = desc_folha_prev * 2.0

        saldo_atual_lp = patrimonio_total_lp
        aporte_mensal_lp = tot_longo_mes

        meses_total = int(anos_proj * 12)

        val_futuro_prev = saldo_atual_prev * ((1 + taxa_juros_mensal) ** meses_total)
        if taxa_juros_mensal > 0:
            val_futuro_prev += aporte_mensal_prev * (((1 + taxa_juros_mensal) ** meses_total - 1) / taxa_juros_mensal)
        else:
            val_futuro_prev += aporte_mensal_prev * meses_total

        val_futuro_lp = saldo_atual_lp * ((1 + taxa_juros_mensal) ** meses_total)
        if taxa_juros_mensal > 0:
            val_futuro_lp += aporte_mensal_lp * (((1 + taxa_juros_mensal) ** meses_total - 1) / taxa_juros_mensal)
        else:
            val_futuro_lp += aporte_mensal_lp * meses_total

        patrimonio_futuro_total = val_futuro_prev + val_futuro_lp

        st.write("")
        st.markdown(f"#### 💰 Montantes Projetados para Daqui a **{anos_proj} Anos**:")
        
        pr_c1, pr_c2, pr_c3 = st.columns(3)
        pr_c1.metric("🏛️ Previdência Cooperativa", fmt_moeda(val_futuro_prev))
        pr_c2.metric("💎 Carteira de Longo Prazo", fmt_moeda(val_futuro_lp))
        pr_c3.metric("🎯 Patrimônio Total Futuro", fmt_moeda(patrimonio_futuro_total), delta="Acumulado Esperado")

        st.divider()

        st.write("#### 📊 Evolução Gráfica do Patrimônio (Projetado vs. Construção Real)")
        
        col_graf_sel, _ = st.columns([2, 2])
        with col_graf_sel:
            horizonte_tempo = st.selectbox(
                "📅 Escolha a Granularidade de Acompanhamento:",
                ["Mês a Mês (Curto Prazo)", "Trimestral (3 Meses)", "Semestral (6 Meses)", "Anual (1 Ano)", "Bianual (2 Anos)"]
            )

        if "Mês" in horizonte_tempo: passo_meses = 1
        elif "3" in horizonte_tempo: passo_meses = 3
        elif "6" in horizonte_tempo: passo_meses = 6
        elif "1 Ano" in horizonte_tempo: passo_meses = 12
        else: passo_meses = 24

        pontos_x, valores_prev_graf, valores_lp_graf, valores_real_graf = [], [], [], []
        patrimonio_real_hoje = saldo_atual_prev + saldo_atual_lp

        for m in range(0, meses_total + 1, passo_meses):
            if m == 0:
                p_prev = saldo_atual_prev
                p_lp = saldo_atual_lp
                p_real = patrimonio_real_hoje
                rotulo = "Início (Hoje)"
            else:
                p_prev = saldo_atual_prev * ((1 + taxa_juros_mensal) ** m) + (aporte_mensal_prev * (((1 + taxa_juros_mensal) ** m - 1) / taxa_juros_mensal) if taxa_juros_mensal > 0 else aporte_mensal_prev * m)
                p_lp = saldo_atual_lp * ((1 + taxa_juros_mensal) ** m) + (aporte_mensal_lp * (((1 + taxa_juros_mensal) ** m - 1) / taxa_juros_mensal) if taxa_juros_mensal > 0 else aporte_mensal_lp * m)
                
                p_real = patrimonio_real_hoje + ((aporte_mensal_prev + aporte_mensal_lp) * m)
                
                anos_decorridos = m // 12
                meses_decorridos = m % 12
                if anos_decorridos > 0 and meses_decorridos > 0:
                    rotulo = f"Ano {anos_decorridos} e {meses_decorridos}m"
                elif anos_decorridos > 0:
                    rotulo = f"Ano {anos_decorridos}"
                else:
                    rotulo = f"Mês {m}"

            pontos_x.append(rotulo)
            valores_prev_graf.append(round(p_prev, 2))
            valores_lp_graf.append(round(p_lp, 2))
            valores_real_graf.append(round(p_real, 2))

        fig_proj = go.Figure()

        fig_proj.add_trace(go.Bar(x=pontos_x, y=valores_prev_graf, name="Previdência Cooperativa", marker_color="#1f77b4"))
        fig_proj.add_trace(go.Bar(x=pontos_x, y=valores_lp_graf, name="Carteira de Longo Prazo", marker_color="#2ca02c"))

        fig_proj.add_trace(go.Scatter(
            x=pontos_x,
            y=valores_real_graf,
            name="Linha de Construção Real (Aportes)",
            mode="lines+markers",
            line=dict(color="#ff7f0e", width=3, dash="dash")
        ))

        fig_proj.update_layout(
            barmode='stack',
            title_text=f"<b>Projeção Empilhada vs. Linha de Construção Real (Horizonte de {anos_proj} Anos)</b>",
            xaxis_title="Período de Acompanhamento",
            yaxis_title="Patrimônio Acumulado (R$)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=520
        )

        st.plotly_chart(fig_proj, use_container_width=True)

        diff_juros_total = patrimonio_futuro_total - valores_real_graf[-1]
        
        st.success(
            f"💡 **Diagnóstico Dinâmico de Projeção:** No final do horizonte de {anos_proj} anos, "
            f"a sua projeção composta está **dentro e acima** da linha de construção real, gerando um ganho adicional de "
            f"**{fmt_moeda(diff_juros_total)}** exclusivamente vindos do poder dos juros compostos!"
        )

    # 12.10. SUB-ABA: ANÁLISE DE RENDA & IPCA
    with sub_analise_renda:
        st.write("### 📊 Análise de Evolução da Renda & Comparativo com o IPCA")
        st.markdown("Acompanhe o crescimento da sua renda (gráfico em meses ou anos) e verifique se o seu aumento salarial superou a inflação acumulada de 12 meses, garantindo ganho real de poder de compra.")

        if st.session_state.df_rendimentos.empty:
            st.info("ℹ️ Nenhum rendimento lançado no histórico até o momento. Cadastre rendas na aba principal para visualizar os gráficos e análises.")
        else:
            df_analise = st.session_state.df_rendimentos.copy()
            df_analise["Valor (R$)"] = pd.to_numeric(df_analise["Valor (R$)"], errors="coerce").fillna(0.0)
            
            def extrair_ano(val):
                try:
                    partes = str(val).split("/")
                    return partes[1] if len(partes) > 1 else "2026"
                except:
                    return "2026"
            
            df_analise["Ano"] = df_analise["Mês/Ano"].apply(extrair_ano)

            tipo_visao_renda = st.radio("📈 Escolha a Visão do Gráfico de Renda:", ["Visão Mensal", "Visão Anual"], horizontal=True)

            if tipo_visao_renda == "Visão Mensal":
                df_grp_mes = df_analise.groupby("Mês/Ano")["Valor (R$)"].sum().reset_index()
                fig_renda = go.Figure(go.Bar(
                    x=df_grp_mes["Mês/Ano"],
                    y=df_grp_mes["Valor (R$)"],
                    marker_color="#2ca02c",
                    text=[fmt_moeda(v) for v in df_grp_mes["Valor (R$)"]],
                    textposition="auto"
                ))
                fig_renda.update_layout(title_text="<b>Evolução da Renda Acumulada por Mês</b>", xaxis_title="Mês/Ano", yaxis_title="Renda Total (R$)", height=450)
                st.plotly_chart(fig_renda, use_container_width=True)
            else:
                df_grp_ano = df_analise.groupby("Ano")["Valor (R$)"].sum().reset_index()
                fig_renda = go.Figure(go.Bar(
                    x=df_grp_ano["Ano"],
                    y=df_grp_ano["Valor (R$)"],
                    marker_color="#1f77b4",
                    text=[fmt_moeda(v) for v in df_grp_ano["Valor (R$)"]],
                    textposition="auto"
                ))
                fig_renda.update_layout(title_text="<b>Evolução da Renda Acumulada por Ano</b>", xaxis_title="Ano", yaxis_title="Renda Total (R$)", height=450)
                st.plotly_chart(fig_renda, use_container_width=True)

            st.divider()
            st.write("### ⚖️ Análise Analítica: Crescimento Salarial vs. IPCA (Poder de Compra)")
            
            ipca_12m = 4.44
            st.info(f"ℹ️ Referência oficial do **IPCA Acumulado de 12 Meses**: **{ipca_12m:.2f}%**")

            df_anual_comp = df_analise.groupby("Ano")["Valor (R$)"].sum().reset_index().sort_values("Ano")
            
            if len(df_anual_comp) >= 2:
                penultimo_ano = df_anual_comp.iloc[-2]
                ultimo_ano = df_anual_comp.iloc[-1]
                
                val_ant = penultimo_ano["Valor (R$)"]
                val_atual = ultimo_ano["Valor (R$)"]
                
                crescimento_renda_pct = ((val_atual / val_ant) - 1.0) * 100.0 if val_ant > 0 else 0.0
                diferenca_ipca = crescimento_renda_pct - ipca_12m

                ar1, ar2, ar3 = st.columns(3)
                ar1.metric(f"Renda Total ({penultimo_ano['Ano']})", fmt_moeda(val_ant))
                ar2.metric(f"Renda Total ({ultimo_ano['Ano']})", fmt_moeda(val_atual), delta=f"{crescimento_renda_pct:+.2f}%")
                ar3.metric("Inflação IPCA (12M)", f"{ipca_12m:.2f}%", delta=f"Diferencial: {diferenca_ipca:+.2f}pp", delta_color="normal" if diferenca_ipca >= 0 else "inverse")

                st.write("")
                if crescimento_renda_pct > ipca_12m:
                    st.success(
                        f"🏆 **DIAGNÓSTICO POSITIVO DE PODER DE COMPRA:** Sua renda cresceu **{crescimento_renda_pct:.2f}%** "
                        f"de um ano para o outro, superando com folga a inflação do período (**{ipca_12m:.2f}%**). "
                        f"Isso significa que você obteve um **aumento real de poder de compra** de **+{diferenca_ipca:.2f} pontos percentuais**!"
                    )
                elif abs(crescimento_renda_pct - ipca_12m) <= 0.3:
                    st.warning(
                        f"⚖️ **DIAGNÓSTICO DE EMPATE (ESTABILIDADE):** Sua renda cresceu **{crescimento_renda_pct:.2f}%**, "
                        f"ficando rigorosamente emparelhada com a inflação de **{ipca_12m:.2f}%**. "
                        "Seu poder de compra permaneceu estável, sem ganhos ou perdas reais significativas."
                    )
                else:
                    st.error(
                        f"🚨 **ALERTA DE PERDA DE PODER DE COMPRA:** Sua renda variou **{crescimento_renda_pct:.2f}%**, "
                        f"ficando abaixo da inflação acumulada de **{ipca_12m:.2f}%**. "
                        f"Houve uma defasagem real de **{diferenca_ipca:.2f}pp**, indicando perda de poder de compra no período."
                    )
            else:
                st.warning("⚠️ É necessário possuir lançamentos de rendimentos registrados em pelo menos **dois anos diferentes** para efetuar o comparativo analítico automático contra o IPCA.")
