import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

def normalizar_cpf(s):
    # Converte para string, limpa caracteres não numéricos e zera à esquerda para 11 dígitos
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def carregar_e_limpar(arquivo, eh_siaps=False):
    arquivo.seek(0)
    # Carrega ignorando o cabeçalho inicial para encontrar a linha correta
    df = pd.read_excel(arquivo, header=None)
    
    if eh_siaps:
        # Força o cabeçalho na linha 18 (índice 17)
        idx_cabecalho = 17
    else:
        # Tenta detectar automaticamente para a complementar
        idx_cabecalho = 0 
        
    df.columns = df.iloc[idx_cabecalho].astype(str).str.strip()
    df = df.iloc[idx_cabecalho + 1:].reset_index(drop=True)
    
    # Identifica coluna de CPF e remove linhas onde o CPF não é numérico (limpa rodapé)
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        # Filtra apenas linhas que possuem um CPF válido (remove rodapés explicativos)
        df = df[df['CPF_key'].str.match(r'^\d{11}$')]
        df = df[df['CPF_key'] != '00000000000']
    
    return df

st.title('🏥 Dashboard APS - Hipertensão')

with st.sidebar:
    st.header("Uploads")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Cabeçalho Linha 18)', type=['xls', 'xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xls', 'xlsx'])

if arq_siaps:
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    
    if 'CPF_key' not in df_siaps.columns:
        st.error("Não encontrei a coluna 'CPF' na linha 18.")
    else:
        if arq_cad:
            df_cad = carregar_e_limpar(arq_cad)
            df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='left', suffixes=('_siaps', '_cad'))
        else:
            df_final = df_siaps

        st.subheader("Painel de monitoramento")
        st.metric("Total de pacientes identificados", len(df_final))
        
        st.subheader("Lista Nominal (Limpa)")
        st.dataframe(df_final, use_container_width=True)
        
        # Download para conferência
        csv = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar CSV Consolidado", csv, "lista_consolidada.csv", "text/csv")
else:
    st.info('Por favor, envie a planilha do SIAPS na barra lateral.')
