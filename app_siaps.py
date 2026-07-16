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


def detectar_tipo_siaps(df: pd.DataFrame, nome_arquivo: str = ""):
    cols = {str(c).strip() for c in df.columns}
    nome = (nome_arquivo or "").lower()
    colunas_hipertensao_boas_praticas = {
        "CPF", "CNS", "Nascimento", "Sexo", "Raça cor", "CNES", "INE",
        "A", "B", "C", "D", "NM", "DN"
    }
    if colunas_hipertensao_boas_praticas.issubset(cols):
        if "hipertens" in nome or "hipertensão" in nome or "hipertensao" in nome:
            return "SIAPS_HIPERTENSAO_BOAS_PRATICAS"
        return "SIAPS_HIPERTENSAO_BOAS_PRATICAS"
    return None


def exibir_cabecalho_analise(linha_cuidado: str, origem: str):
    selo = "Detectado automaticamente" if origem == "automática" else "Definido manualmente"
    st.markdown(
        f"<div style='background:#f8fafc;border:1px solid #e5e7eb;border-radius:16px;padding:16px 18px;margin:8px 0 14px 0'><div style='font-size:0.82rem;color:#64748b;font-weight:600;letter-spacing:.02em;text-transform:uppercase;margin-bottom:6px'>Análise do relatório</div><div style='font-size:1.35rem;font-weight:700;color:#0f172a;margin-bottom:4px'>Linha de cuidado: {linha_cuidado}</div><div style='font-size:0.95rem;color:#475569'>{selo}</div></div>",
        unsafe_allow_html=True,
    )


def exibirmetricascards(*cards):
    html = ['<div class="metric-grid">']
    for titulo, valor in cards:
        html.append(
            f'<div class="metric-card"><div class="metric-card-label">{titulo}</div><div class="metric-card-value">{valor}</div></div>'
        )
    html.append('</div>')
    st.markdown(''.join(html), unsafe_allow_html=True)


def graficobarras(df, x, y, titulo, cor=None):
    if df.empty:
        st.info('Sem dados para exibir neste gráfico.')
        return
    fig = px.bar(df, x=x, y=y, title=titulo, color=cor)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)


def dataframeparaexcelbytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    output.seek(0)
    return output.getvalue()


def marcar_x(serie):
    return serie.fillna('').astype(str).str.strip().str.upper().eq('X')


def traduzir_raca_cor(valor):
    mapa = {
        '1': 'Branca',
        '2': 'Preta',
        '3': 'Amarela',
        '4': 'Parda',
        '5': 'Indígena',
        '6': 'Sem informação',
    }
    if pd.isna(valor):
        return 'Sem informação'
    chave = str(valor).strip()
    return mapa.get(chave, chave)


def montar_motivo_pendencia_siaps_hipertensao(row):
    motivos = []
    if row.get('pendencia_A', False):
        motivos.append('Sem consulta em 6 meses')
    if row.get('pendencia_B', False):
        motivos.append('Sem aferição de PA em 6 meses')
    if row.get('pendencia_C', False):
        motivos.append('Sem peso e altura em 12 meses')
    if row.get('pendencia_D', False):
        motivos.append('Sem 2 visitas ACS/TACS em 12 meses')
    return ' | '.join(motivos) if motivos else 'Sem pendências'


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
    m = calcular_metricas_siaps_hipertensao(df)

    exibirmetricascards(
        ('Total de pacientes', m['total_pacientes']),
        ('Denominador', m['denominador']),
        ('Numerador', m['numerador']),
        ('Desempenho', f"{m['desempenho']:.1f}%"),
        ('Boas práticas', f"{m['boas_praticas_cumpridas']}/{m['boas_praticas_possiveis']}"),
    )
    exibirmetricascards(
        ('Pendência A', m['pend_a']),
        ('Pendência B', m['pend_b']),
        ('Pendência C', m['pend_c']),
        ('Pendência D', m['pend_d']),
    )

    cobertura = pd.DataFrame({
        'Boa prática': ['A - Consulta', 'B - PA', 'C - Peso/altura', 'D - Visitas ACS'],
        'Cumpridos': [m['cumpriu_a'], m['cumpriu_b'], m['cumpriu_c'], m['cumpriu_d']],
        'Pendentes': [m['pend_a'], m['pend_b'], m['pend_c'], m['pend_d']],
    })

    st.subheader('Cobertura das boas práticas')
    graficobarras(cobertura, 'Boa prática', 'Cumpridos', 'Boas práticas cumpridas - Hipertensão SIAPS')

    st.subheader('Lista nominal de pendências')
    somente_pendentes = st.checkbox(
        'Mostrar apenas pacientes com alguma pendência',
        value=True,
        key='siaps_hipertensao_somente_pendentes',
    )

    lista = df.copy()
    if somente_pendentes:
        lista = lista[lista['total_pendencias'] > 0]

    lista = lista.sort_values(by=['total_pendencias', 'total_boas_praticas'], ascending=[False, True])

    colunas_saida = [
        'CPF', 'CNS', 'Nascimento', 'Sexo', 'Raça cor', 'Raça/Cor descrita',
        'CNES', 'INE', 'A', 'B', 'C', 'D', 'NM', 'DN',
        'total_boas_praticas', 'total_pendencias', 'Motivo da pendência'
    ]
    colunas_saida = [c for c in colunas_saida if c in lista.columns]

    st.download_button(
        'Exportar lista nominal SIAPS - Hipertensão',
        data=dataframeparaexcelbytes(lista[colunas_saida]),
        file_name='siaps_hipertensao_boas_praticas.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key='download_siaps_hipertensao',
    )
    st.dataframe(lista[colunas_saida], use_container_width=True)


arquivo = file_uploader_compat('Envie a planilha correspondente', type=['xlsx', 'xls', 'csv'])

with st.expander('Como usar'):
    st.markdown(
        """
- Envie a planilha correspondente.
- O sistema tenta identificar automaticamente o tipo de relatório.
- Para planilhas SIAPS de boas práticas, o cabeçalho da linha 18 é lido automaticamente.
- Para os relatórios antigos, a lógica atual continua disponível.
        """
    )

if arquivo is None:
    st.info('Aguardando upload da planilha.')
else:
    try:
        tipo_siaps = None
        df_siaps = None

        if arquivo.name.lower().endswith(('.xlsx', '.xls')):
            arquivo.seek(0)
            try:
                df_siaps = pd.read_excel(arquivo, header=17)
                tipo_siaps = detectar_tipo_siaps(df_siaps, arquivo.name)
            except Exception as e:
                st.warning(f'Falha ao tentar ler como SIAPS: {e}')
                tipo_siaps = None

        if tipo_siaps == 'SIAPS_HIPERTENSAO_BOAS_PRATICAS':
            exibir_cabecalho_analise('Hipertensão - Boas Práticas SIAPS', 'automática')
            render_siaps_hipertensao_boas_praticas(df_siaps)
        else:
            arquivo.seek(0)
            df = carregar_planilha_generica(arquivo)
            linhadetectada, origem = detectar_linha_cuidado(df, arquivo.name)
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
