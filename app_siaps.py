import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

# --- Funções ---
def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def carregar_arquivo(arquivo):
    arquivo.seek(0)
    nome = arquivo.name.lower()
    if nome.endswith('.xls'):
        return pd.read_excel(arquivo, engine='xlrd')
    return pd.read_excel(arquivo, engine='openpyxl')

def preparar_dados(df):
    df.columns = [str(c).strip() for c in df.columns]
    # Busca coluna CPF ignorando maiúsculas/minúsculas
    col_cpf = next((c for c in df.columns if c.upper() == 'CPF'), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
    else:
        df['CPF_key'] = None
    return df

# --- Interface ---
st.title('🏥 Dashboard APS - Hipertensão')

with st.sidebar:
    st.header("Uploads")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Resultado)', type=['xls', 'xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xls', 'xlsx'])

if arq_siaps:
    df_siaps = preparar_dados(carregar_arquivo(arq_siaps))
    
    # Validação de chave
    if 'CPF_key' not in df_siaps.columns or df_siaps['CPF_key'].isnull().all():
        st.error("Erro: A planilha SIAPS não possui uma coluna 'CPF'.")
    else:
        # Lógica de unificação
        if arq_cad:
            df_cad = preparar_dados(carregar_arquivo(arq_cad))
            if 'CPF_key' not in df_cad.columns or df_cad['CPF_key'].isnull().all():
                st.warning("Aviso: A planilha complementar não possui coluna 'CPF'. Exibindo apenas dados do SIAPS.")
                df_final = df_siaps
            else:
                df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='left', suffixes=('_siaps', '_cad'))
        else:
            df_final = df_siaps

        # --- Painel de Métricas ---
        st.subheader('Painel de monitoramento')
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('Total de pacientes', len(df_final))
        
        indicadores = ['A', 'B', 'C', 'D']
        colunas_metricas = [c2, c3, c4, c5]
        
        for i, ind in enumerate(indicadores):
            if ind in df_final.columns:
                val = df_final[ind].astype(str).str.strip().str.upper().value_counts().get('X', 0)
                colunas_metricas[i].metric(f'Indicador {ind}', val)

        # --- Gráfico ---
        st.subheader('Distribuição de Boas Práticas')
        dados_grafico = []
        for ind in indicadores:
            if ind in df_final.columns:
                total = df_final[ind].astype(str).str.strip().str.upper().value_counts().get('X', 0)
                dados_grafico.append({'Indicador': ind, 'Total': total})
        
        if dados_grafico:
            fig = px.bar(pd.DataFrame(dados_grafico), x='Indicador', y='Total', text='Total')
            st.plotly_chart(fig, use_container_width=True)

        st.subheader('Lista Nominal Unificada')
        st.dataframe(df_final, use_container_width=True)
else:
    st.info('Envie a planilha do SIAPS na barra lateral para começar.')
