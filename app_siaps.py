import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def limpar_df(df, linha_cabecalho):
    # Remove linhas vazias iniciais e define o cabeçalho
    df = df.iloc[linha_cabecalho:].reset_index(drop=True)
    df.columns = df.iloc[0].astype(str).str.strip()
    df = df.iloc[1:].reset_index(drop=True)
    return df

def carregar_e_limpar(arquivo, eh_siaps=False):
    arquivo.seek(0)
    # Lê sem cabeçalho para ter controle total
    df = pd.read_excel(arquivo, header=None)
    
    # Linha 17 (índice) é o cabeçalho para SIAPS; 0 para complementar
    idx = 17 if eh_siaps else 0
    df = limpar_df(df, idx)
    
    # Localiza CPF (ajuste de nomes)
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        df = df[df['CPF_key'].str.match(r'^\d{11}$') & (df['CPF_key'] != '00000000000')]
    return df

st.title('🏥 Dashboard APS - Hipertensão')

with st.sidebar:
    st.header("Uploads")
    arq_siaps = st.file_uploader('1. Planilha SIAPS', type=['xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xlsx'])

if arq_siaps and arq_cad:
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    df_cad = carregar_e_limpar(arq_cad)
    
    df_siaps['Contém no SIAPS'] = 'X'
    df_cad['Contém na Complementar'] = 'X'
    
    df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))

    # Mapeamento robusto para capturar colunas da planilha complementar
    def get_col(nome_final, options):
        for opt in options:
            match = next((c for c in df_final.columns if opt.lower() in c.lower()), None)
            if match: return df_final[match]
        return pd.Series([''] * len(df_final))

    df_lista = pd.DataFrame({
        'Nome Completo': get_col('Nome', ['Nome', 'Paciente', 'Cidadão']),
        'CPF': df_final['CPF_key'],
        'CNS': get_col('CNS', ['CNS', 'Cartão', 'SUS']),
        'Data Nascimento': get_col('Nascimento', ['Nascimento', 'Data']),
        'Idade': get_col('Idade', ['Idade']),
        'Endereço': get_col('Endereço', ['Endereço', 'Logradouro', 'Endereço Residencial']),
        'Equipe Área': get_col('Equipe', ['Equipe Área', 'Equipe']),
        'Microárea': get_col('Microárea', ['Microárea', 'Micro']),
        'Equipe Vínculo': get_col('Equipe Vínculo', ['Vínculo', 'Vinculo']),
        'A': df_final.get('A', ''),
        'B': df_final.get('B', ''),
        'C': df_final.get('C', ''),
        'D': df_final.get('D', ''),
        'Contém no SIAPS': df_final['Contém no SIAPS'].fillna(''),
        'Contém na Complementar': df_final['Contém na Complementar'].fillna('')
    })

    # Painel
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Total Pacientes', len(df_lista))
    for i, ind in enumerate(['A', 'B', 'C', 'D']):
        val = df_lista[ind].astype(str).str.upper().value_counts().get('X', 0) if ind in df_lista.columns else 0
        [c2, c3, c4, c5][i].metric(f'Ind {ind}', val)

    st.dataframe(df_lista, use_container_width=True)
else:
    st.info('Por favor, faça o upload de ambas as planilhas para unificar os dados.')
