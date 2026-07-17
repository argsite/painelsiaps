import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)

def carregar_e_limpar(arquivo, eh_siaps=False):
    arquivo.seek(0)
    df = pd.read_excel(arquivo, header=None)
    idx = 17 if eh_siaps else 0
    df.columns = [str(c).strip() for c in df.iloc[idx]]
    df = df.iloc[idx + 1:].reset_index(drop=True)
    
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        df = df[df['CPF_key'].str.match(r'^\d{11}$')]
        df = df[~df['CPF_key'].isin(['00000000000', ''])]
    return df

st.title('🏥 Dashboard APS - Hipertensão')

MAPA_INDICADORES = {'A': 'A - Consultas', 'B': 'B - P.A.', 'C': 'C - Peso/Altura', 'D': 'D - Visitas'}

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
    df_final = df_final[df_final['CPF_key'].str.match(r'^\d{11}$')]

    # Função corrigida para buscar colunas renomeadas pelo merge
    def get_indicador(key):
        # Procura por "A_siaps" ou "A" (caso não tenha sofrido merge)
        col_name = next((c for c in df_final.columns if c.startswith(f"{key}_siaps") or c == key), None)
        return df_final[col_name].fillna('') if col_name else ''

    def get_demografia(options):
        match = next((c for c in df_final.columns if any(opt.lower() in c.lower() for opt in options)), None)
        return df_final[match].fillna('') if match else ''

    df_lista = pd.DataFrame({
        'Nome Completo': get_demografia(['Nome', 'Paciente', 'Cidadão']),
        'CPF': df_final['CPF_key'],
        'CNS': get_demografia(['CNS', 'Cartão', 'SUS']),
        'Data Nascimento': get_demografia(['Nascimento', 'Data']),
        'Idade': get_demografia(['Idade']),
        'Endereço': get_demografia(['Endereço', 'Logradouro']),
        'Equipe Área': get_demografia(['Equipe Área', 'Equipe']),
        'Microárea': get_demografia(['Microárea', 'Micro']),
        'Equipe Vínculo': get_demografia(['Vínculo', 'Vinculo']),
        'A': get_indicador('A'),
        'B': get_indicador('B'),
        'C': get_indicador('C'),
        'D': get_indicador('D'),
        'Contém no SIAPS': df_final.get('Contém no SIAPS_siaps', df_final.get('Contém no SIAPS', '')).fillna(''),
        'Contém na Complementar': df_final.get('Contém na Complementar_cad', df_final.get('Contém na Complementar', '')).fillna('')
    })

    st.subheader('Monitoramento de Boas Práticas')
    total = len(df_lista)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Total de pacientes', total)
    
    for i, (key, label) in enumerate(MAPA_INDICADORES.items()):
        count = df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)
        perc = (count / total) * 100 if total > 0 else 0
        [c2, c3, c4, c5][i].metric(label, f"{perc:.1f}%", f"{count} pacientes")

    st.subheader('Distribuição das Boas Práticas')
    dados = [{'Boas Práticas': label, 'Total': df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)} 
             for key, label in MAPA_INDICADORES.items()]
    st.plotly_chart(px.bar(pd.DataFrame(dados), x='Boas Práticas', y='Total', text='Total'), use_container_width=True)

    st.subheader('Lista Nominal Unificada')
    st.dataframe(df_lista, use_container_width=True)
    
    csv = df_lista.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Baixar Lista Nominal Consolidada", csv, "lista_consolidada.csv", "text/csv")
else:
    st.info('Por favor, faça o upload de ambas as planilhas.')
