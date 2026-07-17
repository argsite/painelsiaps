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
    
    # Define linha de cabeçalho: 18 para SIAPS (índice 17), 1 para Complementar (índice 0)
    idx = 17 if eh_siaps else 0
    df.columns = [str(c).strip() for c in df.iloc[idx]]
    df = df.iloc[idx + 1:].reset_index(drop=True)
    
    # Limpeza e normalização do CPF para cruzamento
    col_cpf = next((c for c in df.columns if 'CPF' in c.upper()), None)
    if col_cpf:
        df['CPF_key'] = normalizar_cpf(df[col_cpf])
        # Filtra linhas sem CPF ou CPFs inválidos/zerados (remove rodapé das planilhas)
        df = df[df['CPF_key'].str.len() == 11]
        df = df[~df['CPF_key'].isin(['00000000000', ''])]
    return df

# --- Interface Principal ---
st.title('🏥 Dashboard APS - Hipertensão')

# Mapeamento para os indicadores de Boas Práticas
MAPA_INDICADORES = {
    'A': 'A - Consultas',
    'B': 'B - P.A.',
    'C': 'C - Peso/Altura',
    'D': 'D - Visitas'
}

with st.sidebar:
    st.header("Uploads de Arquivos")
    arq_siaps = st.file_uploader('1. Planilha SIAPS (Resultado)', type=['xlsx'])
    arq_cad = st.file_uploader('2. Planilha Complementar', type=['xlsx'])

if arq_siaps and arq_cad:
    # Processamento
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    df_cad = carregar_e_limpar(arq_cad)
    
    df_siaps['Contém no SIAPS'] = 'X'
    df_cad['Contém na Complementar'] = 'X'
    
    # Merge das bases
    df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))

    # Mapeamento de colunas com busca flexível
    def get_col(options):
        match = next((c for c in df_final.columns if any(opt.lower() in c.lower() for opt in options)), None)
        return df_final[match] if match else ''

    df_lista = pd.DataFrame({
        'Nome Completo': get_col(['Nome', 'Paciente', 'Cidadão']),
        'CPF': df_final['CPF_key'],
        'CNS': get_col(['CNS', 'Cartão', 'SUS']),
        'Data Nascimento': get_col(['Nascimento', 'Data']),
        'Idade': get_col(['Idade']),
        'Endereço': get_col(['Endereço', 'Logradouro']),
        'Equipe Área': get_col(['Equipe Área', 'Equipe']),
        'Microárea': get_col(['Microárea', 'Micro']),
        'Equipe Vínculo': get_col(['Vínculo', 'Vinculo']),
        'A': df_final.get('A', ''),
        'B': df_final.get('B', ''),
        'C': df_final.get('C', ''),
        'D': df_final.get('D', ''),
        'Contém no SIAPS': df_final.get('Contém no SIAPS', '').fillna(''),
        'Contém na Complementar': df_final.get('Contém na Complementar', '').fillna('')
    })

    # --- Monitoramento de Boas Práticas ---
    st.subheader('Monitoramento de Boas Práticas')
    total = len(df_lista)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Total de pacientes', total)
    
    for i, (key, label) in enumerate(MAPA_INDICADORES.items()):
        if key in df_lista.columns:
            count = df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)
            perc = (count / total) * 100 if total > 0 else 0
            [c2, c3, c4, c5][i].metric(label, f"{perc:.1f}%", f"{count} pacientes")

    # --- Gráfico ---
    st.subheader('Distribuição das Boas Práticas')
    dados_grafico = [
        {'Boas Práticas': label, 'Total': df_lista[key].astype(str).str.strip().str.upper().value_counts().get('X', 0)} 
        for key, label in MAPA_INDICADORES.items() if key in df_lista.columns
    ]
    st.plotly_chart(px.bar(pd.DataFrame(dados_grafico), x='Boas Práticas', y='Total', text='Total'), use_container_width=True)

    # --- Tabela Final ---
    st.subheader('Lista Nominal Unificada')
    st.dataframe(df_lista, use_container_width=True)
    
    # Download
    csv = df_lista.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Baixar Lista Nominal Consolidada", csv, "lista_consolidada.csv", "text/csv")

else:
    st.info('Por favor, faça o upload de ambas as planilhas para iniciar o monitoramento.')
```eof
