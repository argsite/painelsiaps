import streamlit as st
import pandas as pd
import io
from io import BytesIO
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dashboard APS - Hipertensão e Diabetes")

st.markdown(
    """
<style>
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:0.5rem 0 1rem 0}
.metric-card{border-radius:16px;padding:14px 16px;border:1px solid rgba(15,23,42,.08);box-shadow:0 1px 3px rgba(15,23,42,.05);background:#fff}
.metric-card-label{font-size:.92rem;line-height:1.25;color:#334155;margin-bottom:10px;min-height:2.5em;display:flex;align-items:flex-start;gap:8px}
.metric-card-value{font-size:clamp(1.65rem,2.6vw,2.2rem);font-weight:700;line-height:1.05;color:#0f172a;letter-spacing:-0.02em;word-break:break-word}
@media (max-width:640px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.metric-card{padding:12px 12px;border-radius:14px}.metric-card-label{font-size:.84rem;min-height:2.8em}.metric-card-value{font-size:1.7rem}}
</style>
""",
    unsafe_allow_html=True,
)

st.title("Dashboard APS - Hipertensão e Diabetes")
st.caption("Painel para acompanhamento territorial, busca ativa e monitoramento por equipe e microárea.")


def file_uploader_compat(label, type=None):
    kwargs = {}
    if type is not None:
        kwargs['type'] = type
    try:
        return st.file_uploader(label, **kwargs)
    except AttributeError:
        return st.sidebar.file_uploader(label, **kwargs)





def marcar_x(serie):
    return serie.fillna('').astype(str).str.strip().str.upper().eq('X')


def traduzir_raca_cor(valor):
    mapa = {'1': 'Branca', '2': 'Preta', '3': 'Amarela', '4': 'Parda', '5': 'Indígena', '6': 'Sem informação'}
    chave = str(valor).strip()
    return mapa.get(chave, valor)


def montar_motivo_pendencia_siaps_hipertensao(linha):
    motivos = []
    if linha.get('pendencia_A', False):
        motivos.append('Sem consulta')
    if linha.get('pendencia_B', False):
        motivos.append('Sem PA')
    if linha.get('pendencia_C', False):
        motivos.append('Sem peso/altura')
    if linha.get('pendencia_D', False):
        motivos.append('Sem visitas ACS')
    return '; '.join(motivos)


def exibirmetricascards(*cards):
    cols = st.columns(len(cards)) if cards else []
    for col, (rotulo, valor) in zip(cols, cards):
        col.metric(rotulo, valor)


def graficobarras(df, x, y, titulo):
    fig = px.bar(df, x=x, y=y, title=titulo, text=y)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)


def dataframeparaexcelbytes(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return buffer.getvalue()


def exibir_cabecalho_analise(linha_cuidado: str, origem: str):
    selo = 'Detectado automaticamente' if origem == 'automática' else 'Definido manualmente'
    st.subheader(linha_cuidado)
    st.caption(selo)


def detectar_tipo_siaps(df: pd.DataFrame, nome_arquivo: str = ''):
    colunas = {str(c).strip().lower() for c in df.columns}
    esperadas = {'cpf', 'cns', 'nascimento', 'sexo', 'raça cor', 'cnes', 'ine', 'a', 'b', 'c', 'd', 'nm', 'dn'}
    if esperadas.issubset(colunas):
        return 'SIAPS_HIPERTENSAO_BOAS_PRATICAS'
    nome = (nome_arquivo or '').lower()
    if 'hipertens' in nome and {'a', 'b', 'c', 'd', 'nm', 'dn'}.issubset(colunas):
        return 'SIAPS_HIPERTENSAO_BOAS_PRATICAS'
    return None



def limpar_siaps_hipertensao(df):
    df = df.copy()
    if 'CPF' in df.columns:
        cpf = df['CPF'].astype(str).str.replace(r'\D+', '', regex=True)
        df = df[df['CPF'].isna() | cpf.str.len().eq(11)]
    return df

def carregar_planilha_generica(arquivo):
    nome = arquivo.name.lower()
    arquivo.seek(0)
    if nome.endswith('.xlsx') or nome.endswith('.xls'):
        return pd.read_excel(arquivo)
    return pd.read_csv(arquivo)


def detectar_linha_cuidado(df: pd.DataFrame, nome_arquivo: str = ""):
    colunas = {str(c).strip().lower() for c in df.columns}
    nome = (nome_arquivo or "").lower()
    pontos_diabetes = 0
    pontos_hipertensao = 0
    chaves_diabetes = ["hba1c", "hemoglobina glicada", "pés", "pes", "diabetes"]
    chaves_hipertensao = ["hipertens", "pressão arterial", "pressao arterial", "pa aferida"]

    for chave in chaves_diabetes:
        if any(chave in c for c in colunas) or chave in nome:
            pontos_diabetes += 1
    for chave in chaves_hipertensao:
        if any(chave in c for c in colunas) or chave in nome:
            pontos_hipertensao += 1

    if pontos_diabetes > pontos_hipertensao:
        return "Diabetes", "automática"
    if pontos_hipertensao > pontos_diabetes:
        return "Hipertensão", "automática"
    return None, "indefinida"




def carregar_base_cadastro(arquivo):
    arquivo.seek(0)
    nome = arquivo.name.lower()
    if nome.endswith(('.xlsx', '.xls')):
        return pd.read_excel(arquivo)
    for enc in ['utf-8', 'latin1', 'cp1252']:
        try:
            arquivo.seek(0)
            return pd.read_csv(arquivo, encoding=enc)
        except UnicodeDecodeError:
            continue
    arquivo.seek(0)
    return pd.read_csv(arquivo, encoding='latin1', sep=None, engine='python')


def normalizar_cpf(serie):
    return serie.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)


def cruzar_siaps_com_cadastro(df_siaps, df_cadastro):
    siaps = df_siaps.copy()
    cad = df_cadastro.copy()

    if 'CPF' not in siaps.columns and 'CPF' not in cad.columns:
        return siaps

    if 'CPF' in siaps.columns:
        siaps['CPF_norm'] = normalizar_cpf(siaps['CPF'])
    else:
        siaps['CPF_norm'] = ''
    if 'CPF' in cad.columns:
        cad['CPF_norm'] = normalizar_cpf(cad['CPF'])
    else:
        cad['CPF_norm'] = ''

    cols_map = {}
    for col in cad.columns:
        c = str(col).strip().lower()
        if c in ['nome completo', 'nome', 'paciente']:
            cols_map[col] = 'Nome Completo'
        elif c in ['endereço', 'endereco']:
            cols_map[col] = 'Endereço'
        elif c in ['equipe área', 'equipe area', 'equipe']:
            cols_map[col] = 'Equipe Área'
        elif c in ['microárea', 'microarea']:
            cols_map[col] = 'Microárea'
        elif c in ['equipe vínculo', 'equipe vinculo']:
            cols_map[col] = 'Equipe Vínculo'
    cad = cad.rename(columns=cols_map)

    siaps['Fonte SIAPS'] = 'SIM'
    cad['Fonte Complementar'] = 'SIM'

    cols_siaps = [c for c in siaps.columns if c != 'CPF_norm']
    cols_cad = [c for c in cad.columns if c != 'CPF_norm']
    merged = siaps.merge(cad, on='CPF_norm', how='outer', suffixes=('_siaps', '_cad'), indicator=True)

    merged['Encontrado na SIAPS'] = merged['_merge'].isin(['both', 'left_only'])
    merged['Encontrado na complementar'] = merged['_merge'].isin(['both', 'right_only'])

    for base_col in ['CPF', 'Nome Completo', 'Endereço', 'Equipe Área', 'Microárea', 'Equipe Vínculo']:
        si = f'{base_col}_siaps'
        ca = f'{base_col}_cad'
        if si in merged.columns and ca in merged.columns:
            merged[base_col] = merged[si].combine_first(merged[ca])
        elif si in merged.columns:
            merged[base_col] = merged[si]
        elif ca in merged.columns:
            merged[base_col] = merged[ca]

    merged['Origem do registro'] = merged['_merge'].map({'both': 'SIAPS + Complementar', 'left_only': 'Apenas SIAPS', 'right_only': 'Apenas Complementar'})
    if 'Nome Completo_cad' in merged.columns and 'Nome Completo' not in merged.columns:
        merged['Nome Completo'] = merged['Nome Completo_cad']
    merged = merged.drop(columns=['_merge', 'CPF_norm'], errors='ignore')
    return merged


def preparar_siaps_hipertensao_boas_praticas(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how='all')
    if 'CPF' in df.columns:
        df = df[df['CPF'].notna()]

    for col in ['A', 'B', 'C', 'D', 'NM', 'DN']:
        df[f'cumpriu_{col}'] = marcar_x(df[col]) if col in df.columns else False

    df['pendencia_A'] = ~df['cumpriu_A']
    df['pendencia_B'] = ~df['cumpriu_B']
    df['pendencia_C'] = ~df['cumpriu_C']
    df['pendencia_D'] = ~df['cumpriu_D']
    df['no_numerador'] = df['cumpriu_NM']
    df['no_denominador'] = df['cumpriu_DN']
    df['total_boas_praticas'] = (
        df['cumpriu_A'].astype(int)
        + df['cumpriu_B'].astype(int)
        + df['cumpriu_C'].astype(int)
        + df['cumpriu_D'].astype(int)
    )
    df['total_pendencias'] = (
        df['pendencia_A'].astype(int)
        + df['pendencia_B'].astype(int)
        + df['pendencia_C'].astype(int)
        + df['pendencia_D'].astype(int)
    )

    if 'Raça cor' in df.columns:
        df['Raça/Cor descrita'] = df['Raça cor'].apply(traduzir_raca_cor)

    df['Motivo da pendência'] = df.apply(montar_motivo_pendencia_siaps_hipertensao, axis=1)
    return df


def calcular_metricas_siaps_hipertensao(df):
    total_pacientes = len(df)
    denominador = int(df['no_denominador'].sum())
    numerador = int(df['no_numerador'].sum())
    desempenho = (numerador / denominador * 100) if denominador else 0.0
    cumpriu_a = int(df['cumpriu_A'].sum())
    cumpriu_b = int(df['cumpriu_B'].sum())
    cumpriu_c = int(df['cumpriu_C'].sum())
    cumpriu_d = int(df['cumpriu_D'].sum())
    pend_a = int(df['pendencia_A'].sum())
    pend_b = int(df['pendencia_B'].sum())
    pend_c = int(df['pendencia_C'].sum())
    pend_d = int(df['pendencia_D'].sum())
    boas_praticas_cumpridas = cumpriu_a + cumpriu_b + cumpriu_c + cumpriu_d
    boas_praticas_possiveis = total_pacientes * 4
    cobertura_boas_praticas = (boas_praticas_cumpridas / boas_praticas_possiveis * 100) if boas_praticas_possiveis else 0.0
    return {
        'total_pacientes': total_pacientes,
        'denominador': denominador,
        'numerador': numerador,
        'desempenho': desempenho,
        'cumpriu_a': cumpriu_a,
        'cumpriu_b': cumpriu_b,
        'cumpriu_c': cumpriu_c,
        'cumpriu_d': cumpriu_d,
        'pend_a': pend_a,
        'pend_b': pend_b,
        'pend_c': pend_c,
        'pend_d': pend_d,
        'boas_praticas_cumpridas': boas_praticas_cumpridas,
        'boas_praticas_possiveis': boas_praticas_possiveis,
        'cobertura_boas_praticas': cobertura_boas_praticas,
    }


def render_siaps_hipertensao_boas_praticas(df):
    df = preparar_siaps_hipertensao_boas_praticas(df)
    st.sidebar.header('Filtros da busca ativa')
    filtrado = df.copy()

    if 'Equipe Área' in filtrado.columns:
        eq_opts = ['Todas'] + sorted([x for x in filtrado['Equipe Área'].dropna().astype(str).str.strip().unique().tolist() if x])
        eq_sel = st.sidebar.selectbox('Equipe', eq_opts, index=0)
        if eq_sel != 'Todas':
            filtrado = filtrado[filtrado['Equipe Área'].astype(str).str.strip() == eq_sel]

    if 'Microárea' in filtrado.columns:
        mi_opts = ['Todas'] + sorted([x for x in filtrado['Microárea'].dropna().astype(str).str.strip().unique().tolist() if x])
        mi_sel = st.sidebar.selectbox('Microárea', mi_opts, index=0)
        if mi_sel != 'Todas':
            filtrado = filtrado[filtrado['Microárea'].astype(str).str.strip() == mi_sel]

    faixas = {'Todas': None, '0-17': (0, 17), '18-39': (18, 39), '40-59': (40, 59), '60+': (60, 200)}
    faixa_sel = st.sidebar.selectbox('Faixa etária', list(faixas.keys()), index=0)
    if faixa_sel != 'Todas' and 'Idade' in filtrado.columns:
        mn, mx = faixas[faixa_sel]
        filtrado = filtrado[pd.to_numeric(filtrado['Idade'], errors='coerce').between(mn, mx, inclusive='both')]

    pend_sel = st.sidebar.selectbox('Pendência de boas práticas', ['Todas', 'A', 'B', 'C', 'D'], index=0)
    if pend_sel != 'Todas':
        filtrado = filtrado[filtrado[f'pendencia_{pend_sel}']]

    m = calcular_metricas_siaps_hipertensao(filtrado)
    exibirmetricascards(
        ('Total de pacientes', m['total_pacientes']),
        ('Denominador', m['denominador']),
        ('Numerador', m['numerador']),
        ('Desempenho', f"{m['desempenho']:.1f}%"),
    )

    cols = ['Nome Completo','CPF','CNS','Data de Nascimento','Idade','Endereço','Equipe Área','Microárea','Equipe Vínculo','Sexo','Raça','A','B','C','D','Encontrado na SIAPS','Encontrado na Complementar']
    for c in cols:
        if c not in filtrado.columns:
            filtrado[c] = ''

    st.subheader('Lista Nominal SIAPS')
    st.dataframe(filtrado[cols], use_container_width=True)



arquivo_siaps = file_uploader_compat('Envie a planilha SIAPS', type=['xlsx', 'xls', 'csv'])
arquivo_cadastro = file_uploader_compat('Envie a base cadastral para cruzamento', type=['xlsx', 'xls', 'csv'])

with st.expander('Como usar'):
    st.markdown(
        """
- Envie a planilha correspondente.
- O sistema tenta identificar automaticamente o tipo de relatório.
- Para planilhas SIAPS de boas práticas, o cabeçalho da linha 18 é lido automaticamente.
- Para os relatórios antigos, a lógica atual continua disponível.
        """
    )

if arquivo_siaps is None:
    st.info('Aguardando upload da planilha.')
else:
    try:
        tipo_siaps = None
        df_siaps = None

        if arquivo_siaps.name.lower().endswith(('.xlsx', '.xls')):
            arquivo_siaps.seek(0)
            try:
                df_siaps = pd.read_excel(arquivo_siaps, header=17)
                tipo_siaps = detectar_tipo_siaps(df_siaps, arquivo_siaps.name)
            except Exception as e:
                st.warning(f'Falha ao tentar ler como SIAPS: {e}')
                tipo_siaps = None

        if tipo_siaps == 'SIAPS_HIPERTENSAO_BOAS_PRATICAS':
            if arquivo_cadastro is not None:
                try:
                    df_cadastro = carregar_base_cadastro(arquivo_cadastro)
                    df_siaps = cruzar_siaps_com_cadastro(df_siaps, df_cadastro)
                except Exception as e:
                    st.warning(f'Não foi possível cruzar a base cadastral: {e}')
            exibir_cabecalho_analise('Hipertensão - Boas Práticas SIAPS', 'automática')
            render_siaps_hipertensao_boas_praticas(df_siaps)
        else:
            arquivo_siaps.seek(0)
            df = carregar_planilha_generica(arquivo_siaps)
            if hasattr(df, 'shape'):
                df = limpar_siaps_hipertensao(df)
            linhadetectada, origem = detectar_linha_cuidado(df, arquivo_siaps.name)
            if linhadetectada is None:
                st.warning('Não foi possível identificar automaticamente a linha de cuidado. Escolha manualmente abaixo.')
                secao = st.radio('Linha de cuidado', ['Hipertensão', 'Diabetes'], horizontal=True, key='linhamanualprincipal')
                origem = 'manual'
            else:
                secao = linhadetectada
            exibir_cabecalho_analise(secao, origem)
            st.info('Esta versão está pronta para o fluxo SIAPS de hipertensão. O fluxo antigo completo ainda não foi reintegrado aqui.')
    except Exception as e:
        st.error(f'Não foi possível processar a planilha: {e}')
