import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as ob
import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório atual ao path para importação correta dos módulos em src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.engine import gerar_dados_imoveis, identificar_outliers_subprecificados, calcular_metricas_bairro
from src.gemini_service import analisar_oportunidade
from src.firebase_service import (
    inicializar_firebase, 
    salvar_regiao_e_metricas, 
    salvar_imovel_com_insight, 
    recuperar_regioes_e_imoveis, 
    recuperar_historico_precos,
    modo_offline
)

# Carrega configurações
load_dotenv()

# Configuração da página Streamlit
st.set_page_config(
    page_title="ImobiIntel | Inteligência Imobiliária",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS Premium Injetada
st.markdown("""
    <style>
        /* Importação do Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Customização de Cards */
        .metric-card {
            background: linear-gradient(135deg, #1e1e2f 0%, #11111d 100%);
            border: 1px solid #2d2d44;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
            transition: transform 0.3s ease, border-color 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            border-color: #6c5ce7;
        }
        .metric-title {
            color: #a29bfe;
            font-size: 0.9rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .metric-value {
            color: #ffffff;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .metric-desc {
            color: #b2bec3;
            font-size: 0.8rem;
        }
        
        /* Destaques e IA */
        .ai-score-container {
            display: flex;
            align-items: center;
            background: rgba(108, 92, 231, 0.1);
            border: 1px solid rgba(108, 92, 231, 0.3);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .ai-score-badge {
            background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
            color: white;
            font-size: 2.2rem;
            font-weight: 800;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 15px rgba(108, 92, 231, 0.5);
            margin-right: 20px;
        }
        
        /* Tags de Oportunidades */
        .tag-opportunity {
            background-color: #ffeaa7;
            color: #d63031;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }
        
        /* Avisos do sistema */
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            display: inline-block;
        }
        .status-online {
            background-color: rgba(46, 204, 113, 0.2);
            color: #2ecc71;
            border: 1px solid #2ecc71;
        }
        .status-offline {
            background-color: rgba(241, 196, 15, 0.2);
            color: #f1c40f;
            border: 1px solid #f1c40f;
        }
    </style>
""", unsafe_allow_html=True)

# Inicialização e Carregamento dos Dados
@st.cache_data(ttl=600)  # Cache de 10 minutos para carregar dados
def carregar_dados_sistema():
    """
    Tenta carregar os dados do Firebase. Se o Firebase/Banco Local estiver vazio,
    gera a base de dados inicial, processa as oportunidades e salva no banco.
    """
    imoveis_banco = recuperar_regioes_e_imoveis()
    
    if not imoveis_banco:
        st.info("Inicializando base de dados de mercado no banco (primeiro acesso)...")
        # Gera os dados simulados
        df_simulado = gerar_dados_imoveis(n_imoveis=160, seed=42)
        df_analisado = identificar_outliers_subprecificados(df_simulado)
        
        # Salva as métricas por bairro
        metricas_bairro = calcular_metricas_bairro(df_simulado)
        for _, row in metricas_bairro.iterrows():
            salvar_regiao_e_metricas(row["bairro"], row.to_dict())
            
        # Salva cada imóvel
        for _, row in df_analisado.iterrows():
            bairro = row["bairro"]
            salvar_imovel_com_insight(bairro, row.to_dict())
            
        # Tenta carregar novamente após inserção
        imoveis_banco = recuperar_regioes_e_imoveis()
        
    return pd.DataFrame(imoveis_banco)

# Cabeçalho Principal do Dashboard
col_header_title, col_header_status = st.columns([0.8, 0.2])

with col_header_title:
    st.title("🏢 ImobiIntel - Inteligência de Mercado Imobiliário")
    st.subheader("Detecção de assimetrias de preços, análise de ROI e oportunidades preditivas via Inteligência Artificial.")

with col_header_status:
    # Mostra se o Firebase está conectado ou rodando offline
    st.write("")
    if not modo_offline:
        st.markdown('<div style="text-align: right;"><span class="status-badge status-online">● Firebase Firestore Ativo</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align: right;"><span class="status-badge status-offline">▲ Modo Local (JSON)</span></div>', unsafe_allow_html=True)

# Carrega os dados persistidos
try:
    df_imoveis = carregar_dados_sistema()
except Exception as e:
    st.error(f"Erro ao inicializar banco de dados: {e}")
    df_imoveis = pd.DataFrame()

if df_imoveis.empty:
    st.warning("Não há dados de imóveis disponíveis. Verifique as configurações de conexão.")
    st.stop()

# =====================================================================
# BARRA LATERAL - FILTROS E CONFIGURAÇÕES
# =====================================================================
st.sidebar.image("https://img.icons8.com/nolan/96/real-estate.png", width=70)
st.sidebar.title("Filtros de Mercado")

# Filtro 1: Região / Bairro
bairros_disponiveis = sorted(list(df_imoveis["bairro"].unique()))
bairros_selecionados = st.sidebar.multiselect(
    "Selecionar Bairros",
    options=bairros_disponiveis,
    default=bairros_disponiveis
)

# Filtro 2: Tipo de Imóvel
tipos_disponiveis = sorted(list(df_imoveis["tipo"].unique()))
tipos_selecionados = st.sidebar.multiselect(
    "Tipo de Imóvel",
    options=tipos_disponiveis,
    default=tipos_disponiveis
)

# Filtro 3: Preço Máximo
preco_min = float(df_imoveis["preco_venda"].min())
preco_max = float(df_imoveis["preco_venda"].max())
preco_max_selecionado = st.sidebar.slider(
    "Preço Máximo de Venda (R$)",
    min_value=preco_min,
    max_value=preco_max,
    value=preco_max,
    step=50000.0,
    format="R$ %d"
)

# Filtro 4: Apenas Oportunidades
apenas_oportunidades = st.sidebar.checkbox(
    "Filtrar apenas Oportunidades (Outliers)",
    value=False
)

# Aplicação dos Filtros no DataFrame
df_filtrado = df_imoveis[
    (df_imoveis["bairro"].isin(bairros_selecionados)) &
    (df_imoveis["tipo"].isin(tipos_selecionados)) &
    (df_imoveis["preco_venda"] <= preco_max_selecionado)
]

if apenas_oportunidades:
    df_filtrado = df_filtrado[df_filtrado["oportunidade_detectada"] == True]

# =====================================================================
# CARDS DE MÉTRICAS EM DESTAQUE (Indispensável)
# =====================================================================
st.markdown("### 📊 Visão Geral do Portfólio Filtrado")

# Cálculos de Métricas
total_imoveis_filt = len(df_filtrado)
df_oportunidades = df_filtrado[df_filtrado["oportunidade_detectada"] == True]
total_oportunidades_filt = len(df_oportunidades)

media_m2_geral = df_filtrado["preco_m2"].mean() if total_imoveis_filt > 0 else 0
roi_maximo = df_oportunidades["roi_estimado"].max() if total_oportunidades_filt > 0 else 0.0

# Busca a "Oportunidade do Dia"
# Definida como o imóvel outlier com o maior ROI estimado ou desconto percentual
oportunidade_dia = None
if total_oportunidades_filt > 0:
    oportunidade_dia = df_oportunidades.loc[df_oportunidades["roi_estimado"].idxmax()]

# Montagem das 3 colunas de cards
col_card1, col_card2, col_card3 = st.columns(3)

with col_card1:
    # Card 1: Oportunidade do Dia
    if oportunidade_dia is not None:
        id_op = oportunidade_dia["id"]
        bairro_op = oportunidade_dia["bairro"]
        desconto_op = oportunidade_dia["desconto_percentual"]
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">🔥 Oportunidade do Dia</div>
                <div class="metric-value">{id_op} - {bairro_op}</div>
                <div class="metric-desc">Preço: <b>R$ {oportunidade_dia['preco_venda']:,}</b> | Desconto: <span class="tag-opportunity">{desconto_op}% OFF</span></div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="metric-card">
                <div class="metric-title">🔥 Oportunidade do Dia</div>
                <div class="metric-value">Nenhuma</div>
                <div class="metric-desc">Ajuste os filtros para encontrar oportunidades.</div>
            </div>
        """, unsafe_allow_html=True)

with col_card2:
    # Card 2: Maior ROI Estimado
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📈 Maior ROI Estimado</div>
            <div class="metric-value">{roi_maximo:.1f}%</div>
            <div class="metric-desc">Maior taxa de retorno calculada para revenda no valor de mercado da região.</div>
        </div>
    """, unsafe_allow_html=True)

with col_card3:
    # Card 3: Média de Preço Geral
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💰 Preço Médio Geral do m²</div>
            <div class="metric-value">R$ {media_m2_geral:,.2f}</div>
            <div class="metric-desc">Média do valor por m² considerando os {total_imoveis_filt} imóveis filtrados.</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# =====================================================================
# GRÁFICOS INTERATIVOS (Dispersão e ROI por Bairro)
# =====================================================================
st.markdown("### 📈 Análise Gráfica Interativa")
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.markdown("#### Distribuição de Preço vs. Área (Identificação de Outliers)")
    if not df_filtrado.empty:
        # Cria coluna personalizada para rótulo legível do gráfico
        df_plot_disp = df_filtrado.copy()
        df_plot_disp["Tipo Oportunidade"] = df_plot_disp["oportunidade_detectada"].map(
            {True: "Oportunidade (Outlier Subprecificado)", False: "Preço Padrão de Mercado"}
        )
        
        fig_disp = px.scatter(
            df_plot_disp,
            x="area_m2",
            y="preco_venda",
            color="Tipo Oportunidade",
            color_discrete_map={
                "Oportunidade (Outlier Subprecificado)": "#ff7675",
                "Preço Padrão de Mercado": "#74b9ff"
            },
            size=df_plot_disp["roi_estimado"] + 5, # Tamanho do ponto varia com o ROI
            hover_data={
                "id": True,
                "bairro": True,
                "preco_m2": ":,.2f",
                "roi_estimado": ":.2f",
                "area_m2": True,
                "preco_venda": ":,"
            },
            labels={
                "area_m2": "Área Útil (m²)",
                "preco_venda": "Preço de Venda (R$)",
                "roi_estimado": "ROI Estimado (%)"
            },
            template="plotly_dark"
        )
        # Customização estética do gráfico
        fig_disp.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_disp, use_container_width=True)
    else:
        st.info("Nenhum dado para exibir no gráfico de dispersão.")

with col_graf2:
    st.markdown("#### Lucro Médio Estimado por Bairro nas Oportunidades")
    # Filtra apenas as oportunidades reais e calcula o lucro médio estimado por bairro
    if not df_oportunidades.empty:
        df_lucro_bairro = df_oportunidades.groupby("bairro")["lucro_estimado"].mean().reset_index()
        df_lucro_bairro = df_lucro_bairro.sort_values(by="lucro_estimado", ascending=False)
        
        fig_barra = px.bar(
            df_lucro_bairro,
            x="bairro",
            y="lucro_estimado",
            labels={
                "bairro": "Bairro",
                "lucro_estimado": "Lucro Médio Estimado (R$)"
            },
            color="lucro_estimado",
            color_continuous_scale="Viridis",
            template="plotly_dark"
        )
        fig_barra.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_barra, use_container_width=True)
    else:
        st.info("Adicione ou filtre oportunidades para ver a comparação de lucro por bairro.")

st.write("")

# =====================================================================
# TABELA DETALHADA E INTELIGÊNCIA ARTIFICIAL (GEMINI)
# =====================================================================
st.markdown("### 🔍 Detalhamento das Oportunidades e Análise da IA")

if df_oportunidades.empty:
    st.info("Nenhum imóvel identificado como oportunidade subprecificada atende aos critérios dos filtros.")
else:
    # Exibe tabela estruturada das oportunidades detectadas
    colunas_tabela = [
        "id", "bairro", "tipo", "area_m2", "quartos", "vagas", 
        "preco_venda", "preco_m2", "preco_mercado_estimado", 
        "lucro_estimado", "roi_estimado", "desconto_percentual"
    ]
    
    # Formatação de colunas para exibição amigável
    df_exibicao = df_oportunidades[colunas_tabela].copy()
    df_exibicao.columns = [
        "ID", "Bairro", "Tipo", "Área (m²)", "Quartos", "Vagas", 
        "Preço de Venda (R$)", "Preço/m² (R$)", "Valor Mercado (R$)", 
        "Lucro Estimado (R$)", "ROI Estimado (%)", "Desconto (%)"
    ]
    
    st.dataframe(
        df_exibicao.style.format({
            "Preço de Venda (R$)": "R$ {:,.0f}",
            "Preço/m² (R$)": "R$ {:,.2f}",
            "Valor Mercado (R$)": "R$ {:,.0f}",
            "Lucro Estimado (R$)": "R$ {:,.0f}",
            "ROI Estimado (%)": "{:.1f}%",
            "Desconto (%)": "{:.1f}%"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.write("")
    
    # Seção para seleção de imóvel específico e geração de Insights do Gemini
    st.markdown("#### 🤖 Auditoria e Insights de Viabilidade do Gemini")
    
    lista_ids = sorted(list(df_oportunidades["id"].unique()))
    imovel_id_selecionado = st.selectbox(
        "Selecione um imóvel para auditar e ver a análise da IA do Gemini:",
        options=lista_ids
    )
    
    if imovel_id_selecionado:
        # Recupera a linha do imóvel selecionado
        imovel_dados = df_oportunidades[df_oportunidades["id"] == imovel_id_selecionado].iloc[0].to_dict()
        bairro_selecionado = imovel_dados["bairro"]
        
        # Recupera métricas regionais do bairro correspondente para enviar ao Gemini
        # Podemos buscar do DataFrame
        df_bairro = df_imoveis[df_imoveis["bairro"] == bairro_selecionado]
        ref_regiao = {
            "media_preco_m2": df_bairro["preco_m2"].mean(),
            "mediana_preco_m2": df_bairro["preco_m2"].median(),
            "std_preco_m2": df_bairro["preco_m2"].std() if len(df_bairro) > 1 else df_bairro["preco_m2"].mean() * 0.1
        }
        
        # Verifica se o imóvel selecionado já possui análise de IA persistida no banco
        insight_salvo = imovel_dados.get("insight_ia")
        
        col_dados_imovel, col_analise_ia = st.columns([0.4, 0.6])
        
        with col_dados_imovel:
            st.markdown(f"##### 📋 Ficha Técnica - {imovel_id_selecionado}")
            st.write(f"**Bairro:** {imovel_dados['bairro']}")
            st.write(f"**Tipo:** {imovel_dados['tipo']}")
            st.write(f"**Área Útil:** {imovel_dados['area_m2']} m²")
            st.write(f"**Tipologia:** {imovel_dados['quartos']} Quartos | {imovel_dados['vagas']} Vagas")
            st.write(f"**Dias no Mercado:** {imovel_dados['dias_mercado']} dias")
            st.markdown("---")
            st.write(f"**Preço de Aquisição:** R$ {imovel_dados['preco_venda']:,}")
            st.write(f"**Preço de Mercado Projetado:** R$ {imovel_dados['preco_mercado_estimado']:,}")
            st.write(f"**Lucro Estimado na Revenda:** R$ {imovel_dados['lucro_estimado']:,}")
            st.write(f"**Retorno sobre Investimento (ROI):** {imovel_dados['roi_estimado']}%")
            
            # Gráfico de histórico de preços fictício para simulação
            st.markdown("##### 📈 Histórico de Preços Recentes")
            historico = recuperar_historico_precos(bairro_selecionado, imovel_id_selecionado)
            if historico:
                df_hist = pd.DataFrame(historico)
                df_hist["data_formatada"] = pd.to_datetime(df_hist["data"]).dt.strftime("%d/%m/%Y %H:%M")
                
                fig_hist = px.line(
                    df_hist,
                    x="data_formatada",
                    y="preco_venda",
                    markers=True,
                    labels={"preco_venda": "Preço de Venda (R$)", "data_formatada": "Data de Registro"},
                    template="plotly_dark"
                )
                fig_hist.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.write("Sem registros adicionais no histórico de preços.")

        with col_analise_ia:
            st.markdown("##### 🧠 Relatório de Viabilidade da IA")
            
            # Se já existe o insight persistido, mostra
            if insight_salvo and isinstance(insight_salvo, dict) and "score_oportunidade" in insight_salvo:
                score = insight_salvo["score_oportunidade"]
                justificativa = insight_salvo["justificativa"]
                risco = insight_salvo["analise_risco"]
                fatores = insight_salvo.get("principais_fatores", [])
                
                # Exibe o Score de Oportunidade
                cor_score = "#2ecc71" if score >= 80 else ("#f1c40f" if score >= 50 else "#e74c3c")
                st.markdown(f"""
                    <div class="ai-score-container">
                        <div class="ai-score-badge" style="background: linear-gradient(135deg, {cor_score} 0%, #2d3436 100%); box-shadow: 0 0 15px {cor_score}50;">
                            {score}
                        </div>
                        <div>
                            <div style="font-weight: 700; font-size: 1.2rem; color: #ffffff;">Score de Oportunidade do Gemini</div>
                            <div style="font-size: 0.9rem; color: #b2bec3;">Este score avalia a assimetria do preço, a atratividade do bairro e o ROI estimado.</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.write("**Justificativa do Investimento:**")
                st.info(justificativa)
                
                st.write("**Análise de Risco Regional:**")
                st.warning(risco)
                
                st.write("**Principais Fatores Relevantes:**")
                for fat in fatores:
                    st.markdown(f"- {fat}")
                    
                # Botão para refazer a análise com Gemini
                if st.button("🔄 Recalcular Análise via Gemini API"):
                    with st.spinner("Conectando ao Gemini API e gerando relatório preditivo..."):
                        novo_insight = analisar_oportunidade(imovel_dados, ref_regiao)
                        if novo_insight:
                            # Salva o novo insight gerado no Firestore/JSON Local
                            salvar_imovel_com_insight(bairro_selecionado, imovel_dados, novo_insight)
                            st.success("Análise de IA atualizada e salva com sucesso no banco!")
                            st.cache_data.clear() # Limpa cache para carregar dados novos
                            st.rerun()
            else:
                # Se não existe o insight (imóvel recém-gerado ou erro anterior), oferece botão para gerar
                st.warning("Este imóvel ainda não possui um relatório de IA gerado no banco de dados.")
                
                if st.button("🤖 Gerar Relatório de Viabilidade com Gemini"):
                    with st.spinner("Solicitando ao Analista de Investimentos Gemini para auditar o imóvel..."):
                        novo_insight = analisar_oportunidade(imovel_dados, ref_regiao)
                        if novo_insight:
                            # Salva no banco de dados
                            salvar_imovel_com_insight(bairro_selecionado, imovel_dados, novo_insight)
                            st.success("Relatório de IA gerado e salvo com sucesso no banco!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Não foi possível gerar a análise. Verifique a chave da API do Gemini.")
