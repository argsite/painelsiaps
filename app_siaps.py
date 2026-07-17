import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def carregar_e_limpar(arquivo, eh_siaps=False):
    arquivo.seek(0)
    df = pd.read_excel(arquivo, header=None)
    
    idx_cabecalho = 17 if eh_siaps else 0
    df.columns = df.iloc[idx_cabecalho].astype(str).str.strip()
    df = df.iloc[idx_cabecalho + 1:].reset_index(drop=True)
    
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        df = df[df['CPF_key'].str.match(r'^\d{11}$') & (df['CPF_key'] != '00000000000')]
    return df

st.title('🏥 Dashboard APS - Hipertensão')

with st.sidebar:
    st.header("Uploads")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Linha 18)', type=['xls', 'xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xls', 'xlsx'])

if arq_siaps:
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    
    # Criar indicadores de presença
    df_siaps['Contém no SIAPS'] = 'X'
    
    if arq_cad:
        df_cad = carregar_e_limpar(arq_cad)
        df_cad['Contém na Complementar'] = 'X'
        
        # Merge (Outer para garantir que teremos a lista total)
        df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))
    else:
        df_final = df_siaps
        df_final['Contém na Complementar'] = ''

    # Função para buscar valor priorizando a origem correta
    def get_val(row, col_siaps, col_cad):
        # Tenta pegar da complementar, se não tiver, da SIAPS
        val = row.get(f"{col_cad}_cad") if f"{col_cad}_cad" in row else row.get(col_cad)
        if pd.isna(val) or val == '':
            val = row.get(f"{col_siaps}_siaps") if f"{col_siaps}_siaps" in row else row.get(col_siaps)
        return val

    # Seleção e Ordenação Final das colunas conforme sua solicitação
    # Criamos um novo DataFrame com a estrutura exata
    df_exibicao = pd.DataFrame()
    df_exibicao['Nome Completo'] = df_final.get('Nome', df_final.get('Nome Completo_cad', ''))
    df_exibicao['CPF'] = df_final['CPF_key']
    df_exibicao['CNS'] = df_final.get('CNS_cad', '')
    df_exibicao['Data Nascimento'] = df_final.get('Data Nascimento_cad', '')
    df_exibicao['Idade'] = df_final.get('Idade_cad', '')
    df_exibicao['Endereço'] = df_final.get('Endereço_cad', '')
    df_exibicao['Equipe Área'] = df_final.get('Equipe Área_cad', '')
    df_exibicao['Microárea'] = df_final.get('Microárea_cad', '')
    df_exibicao['Equipe Vínculo'] = df_final.get('Equipe Vínculo_cad', '')
    df_exibicao['A'] = df_final.get('A_siaps', '')
    df_exibicao['B'] = df_final.get('B_siaps', '')
    df_exibicao['C'] = df_final.get('C_siaps', '')
    df_exibicao['D'] = df_final.get('D_siaps', '')
    df_exibicao['Contém no SIAPS'] = df_final['Contém no SIAPS'].fillna('')
    df_exibicao['Contém na Complementar'] = df_final['Contém na Complementar'].fillna('')

    st.subheader("Lista Nominal (Organizada)")
    st.dataframe(df_exibicao, use_container_width=True)
else:
    st.info('Envie a planilha do SIAPS na barra lateral.')
