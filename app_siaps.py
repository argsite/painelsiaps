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
    return df

# --- Interface ---
st.title('🏥 Dashboard APS - Hipertensão')

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
    df_siaps = carregar_e_limpar(arq_siaps, eh_siaps=True)
    df_cad = carregar_e_limpar(arq_cad)
    
    df_siaps['Contém no SIAPS'] = 'X'
    df_cad['Contém na Complementar'] = 'X'
    
    # Merge
    df_final = pd.merge(df_siaps, df_cad, on='CPF_key', how='outer', suffixes=('_siaps', '_cad'))
    
    # FILTRO FINAL: Remove qualquer linha que não tenha CPF de 11 dígitos válido (elimina legendas remanescentes)
    df_final = df_final[df_final['CPF_key'].str.match(r'^\d{11}$')]

    # Função de mapeamento inteligente
    def get_col(col_siaps, options_cad):
        if col_siaps in df_final.columns:
            return df_final[col_siaps].fillna('')
        match = next((c for c in df_final.columns if any(opt.lower() in c.lower() for opt in options_cad)), None)
        return df_final[match].fillna('') if match else ''

    df_lista = pd.DataFrame({
        'Nome Completo': get_col('', ['Nome', 'Paciente', 'Cidadão']),
        'CPF': df_final['CPF_key'],
        'CNS': get_col('', ['CNS', 'Cartão', 'SUS']),
        'Data Nascimento': get_col('', ['Nascimento', 'Data']),
        'Idade': get_col('', ['Idade']),
        'Endereço': get_col('', ['Endereço', 'Logradouro', 'Endereço Residencial']),
        'Equipe Área': get_col('', ['Equipe Área', 'Equipe']),
        'Microárea': get_col('', ['Microárea', 'Micro']),
        'Equipe Vínculo': get_col('', ['Equipe Vínculo', 'Vinculo']),
        'A': get_col('A', ['EXACT_INDICADOR_A']), 
        'B': get_col('B', ['EXACT_INDICADOR_B']),
        'C': get_col('C', ['EXACT_INDICADOR_C']),
        'D': get_col('D', ['EXACT_INDICADOR_D']),
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
    
    csv = df_lista.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Baixar Lista Nominal Consolidada", csv, "lista_consolidada.csv", "text/csv")
else:
    st.info('Por favor, faça o upload de ambas as planilhas para iniciar o monitoramento.')
