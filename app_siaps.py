import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

# --- Funções de Processamento ---
def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def carregar_e_limpar(arquivo, eh_siaps=False):
    arquivo.seek(0)
    df = pd.read_excel(arquivo, header=None)
    idx_cabecalho = 17 if eh_siaps else 0
    df.columns = [str(c).strip() for c in df.iloc[idx_cabecalho]]
    df = df.iloc[idx_cabecalho + 1:].reset_index(drop=True)
    
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        df = df[df['CPF_key'].str.match(r'^\d{11}$') & (df['CPF_key'] != '00000000000')]
    return df

# --- Interface ---
st.title('🏥 Dashboard APS - Hipertensão')

with st.sidebar:
    st.header("Uploads")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Linha 18)', type=['xls', 'xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xls', 'xlsx'])

if arq_siaps:
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    df_siaps['Contém no SIAPS'] = 'X'
    
    if arq_cad:
        df_cad = carregar_e_limpar(arq_cad)
        df_cad['Contém na Complementar'] = 'X'
        df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))
    else:
        df_final = df_siaps
        df_final['Contém na Complementar'] = ''

    # --- Montagem da Lista Nominal Final ---
    cols_map = {
        'Nome Completo': df_final.get('Nome Completo_cad', ''),
        'CPF': df_final['CPF_key'],
        'CNS': df_final.get('CNS_cad', ''),
        'Data Nascimento': df_final.get('Data Nascimento_cad', ''),
        'Idade': df_final.get('Idade_cad', ''),
        'Endereço': df_final.get('Endereço_cad', ''),
        'Equipe Área': df_final.get('Equipe Área_cad', ''),
        'Microárea': df_final.get('Microárea_cad', ''),
        'Equipe Vínculo': df_final.get('Equipe Vínculo_cad', ''),
        'A': df_final.get('A_siaps', ''),
        'B': df_final.get('B_siaps', ''),
        'C': df_final.get('C_siaps', ''),
        'D': df_final.get('D_siaps', ''),
        'Contém no SIAPS': df_final['Contém no SIAPS'].fillna(''),
        'Contém na Complementar': df_final['Contém na Complementar'].fillna('')
    }
    df_lista = pd.DataFrame(cols_map)

    # --- Painel de Monitoramento ---
    st.subheader('Painel de Monitoramento')
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Total de pacientes', len(df_lista))
    
    # Cálculo das métricas
    for i, ind in enumerate(['A', 'B', 'C', 'D']):
        if ind in df_lista.columns:
            val = df_lista[ind].astype(str).str.strip().str.upper().value_counts().get('X', 0)
            [c2, c3, c4, c5][i].metric(f'Indicador {ind}', val)

    # --- Gráfico ---
    st.subheader('Distribuição de Boas Práticas')
    dados_graf = [{'Indicador': ind, 'Total': df_lista[ind].astype(str).str.strip().str.upper().value_counts().get('X', 0)} for ind in ['A', 'B', 'C', 'D'] if ind in df_lista.columns]
    if dados_graf:
        st.plotly_chart(px.bar(pd.DataFrame(dados_graf), x='Indicador', y='Total', text='Total'), use_container_width=True)

    # --- Tabela Final ---
    st.subheader('Lista Nominal Unificada')
    st.dataframe(df_lista, use_container_width=True)

else:
    st.info('Envie a planilha do SIAPS na barra lateral para começar.')
