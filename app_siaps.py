import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

# --- Funções de Processamento ---
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
        
        col_nome = next((c for c in df.columns if 'NOME' in c.upper()), None)
        if col_nome:
            legendas = ['BRANCA', 'PRETA', 'PARDA', 'AMARELA', 'INDIGENA', 'SEM INFORMACAO', 'TOTAL', 'SIGLA']
            df = df[~df[col_nome].astype(str).str.upper().isin(legendas)]
    return df

# --- Interface Principal ---
st.title('🏥 Dashboard APS - Hipertensão')

MAPA_INDICADORES = {'A': 'A - Consultas', 'B': 'B - P.A.', 'C': 'C - Peso/Altura', 'D': 'D - Visitas'}

with st.sidebar:
    st.header("Uploads de Arquivos")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Resultado)', type=['xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xlsx'])

if arq_siaps and arq_cad:
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    df_cad = carregar_e_limpar(arq_cad)
    
    df_siaps['Contém no SIAPS'] = 'X'
    df_cad['Contém na Complementar'] = 'X'
    
    df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))

    # Função de mapeamento flexível e robusta
    def get_col(col_siaps, options_cad):
        # Para indicadores, usamos o nome exato da coluna no merge
        if col_siaps and col_siaps in df_final.columns:
            return df_final[col_siaps].fillna('')
        # Para demografia, busca pela string contida no nome (ex: "Nome" em "Nome Completo")
        match = next((c for c in df_final.columns if any(opt.lower() == c.lower() for opt in options_cad)), None)
        return df_final[match].fillna('') if match else ''

    df_lista = pd.DataFrame({
        'Nome Completo': get_col('', ['Nome', 'Nome Completo', 'Paciente', 'Cidadão']),
        'CPF': df_final['CPF_key'],
        'CNS': get_col('', ['CNS', 'Cartão', 'Cartão SUS', 'SUS']),
        'Data Nascimento': get_col('', ['Data Nascimento', 'Data de Nascimento', 'Nascimento']),
        'Idade': get_col('', ['Idade']),
        'Endereço': get_col('', ['Endereço', 'Logradouro', 'Endereco']),
        'Equipe Área': get_col('', ['Equipe Área', 'Equipe', 'Equipe Área de Saúde']),
        'Microárea': get_col('', ['Microárea', 'Micro']),
        'Equipe Vínculo': get_col('', ['Equipe Vínculo', 'Vinculo']),
        'A': get_col('A_siaps', ['A']),
        'B': get_col('B_siaps', ['B']),
        'C': get_col('C_siaps', ['C']),
        'D': get_col('D_siaps', ['D']),
        'Contém no SIAPS': df_final.get('Contém no SIAPS', '').fillna(''),
        'Contém na Complementar': df_final.get('Contém na Complementar', '').fillna('')
    })

    # --- Painel e Gráficos ---
    st.subheader('Monitoramento de Boas Práticas')
    total = len(df_lista)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Total de pacientes', total)
    
    for i, (key, label) in enumerate(MAPA_INDICADORES.items()):
        if key in df_lista.columns:
            count = df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)
            perc = (count / total) * 100 if total > 0 else 0
            [c2, c3, c4, c5][i].metric(label, f"{perc:.1f}%", f"{count} pacientes")

    st.subheader('Distribuição das Boas Práticas')
    dados_graf = [{'Boas Práticas': label, 'Total': df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)} 
                  for key, label in MAPA_INDICADORES.items() if key in df_lista.columns]
    if dados_graf:
        st.plotly_chart(px.bar(pd.DataFrame(dados_graf), x='Boas Práticas', y='Total', text='Total'), use_container_width=True)

    st.subheader('Lista Nominal Unificada')
    st.dataframe(df_lista, use_container_width=True)
    
    csv = df_lista.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Baixar Lista Nominal Consolidada", csv, "lista_consolidada.csv", "text/csv")
else:
    st.info('Por favor, faça o upload de ambas as planilhas para iniciar o monitoramento.')
