import streamlit as st
import pandas as pd
from io import BytesIO
import plotly.express as px



def remover_colunas_duplicadas(df):
    return df.loc[:, ~pd.Index(df.columns).duplicated(keep='first')].copy()

def deduplicar_por_cpf(df):
    if df is None or df.empty or 'CPF' not in df.columns:
        return df.copy() if df is not None else df
    base = df.copy()
    base['CPF_norm'] = base['CPF'].astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)
    base = base[base['CPF_norm'] != '00000000000']
    return base.drop_duplicates(subset=['CPF_norm']).copy()

st.set_page_config(layout='wide', page_title='Dashboard APS - Hipertensão')

st.title('Dashboard APS - Hipertensão')
st.caption('Lista nominal SIAPS unificada com a base complementar e filtros de busca ativa.')


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


def detectar_tipo_siaps(df, nome_arquivo=''):
    cols = {str(c).strip().lower() for c in df.columns}
    if {'cpf', 'cns', 'nascimento', 'sexo', 'raça cor', 'cnes', 'ine', 'a', 'b', 'c', 'd', 'nm', 'dn'}.issubset(cols):
        return 'SIAPS_HIPERTENSAO_BOAS_PRATICAS'
    if 'hipertens' in (nome_arquivo or '').lower() and {'cpf', 'cns', 'a', 'b', 'c', 'd'}.issubset(cols):
        return 'SIAPS_HIPERTENSAO_BOAS_PRATICAS'
    return None


def limpar_siaps_hipertensao(df):
    df = df.copy()
    if 'CPF' in df.columns:
        cpf = df['CPF'].astype(str).str.replace(r'\D+', '', regex=True)
        df = df[df['CPF'].isna() | cpf.str.len().eq(11)]
    df['CPF'] = cpf
    return df


def normalizar_cpf(s):
    return s.fillna('').astype(str).str.replace(r'\D+', '', regex=True).str.zfill(11)


def preparar_siaps_hipertensao_boas_praticas(df):
    df = df.copy()
    rename = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl == 'nascimento':
            rename[c] = 'Data de Nascimento'
        elif cl in ['raça cor', 'raca cor']:
            rename[c] = 'Raça'
    df = df.rename(columns=rename)
    for col in ['A', 'B', 'C', 'D']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper().eq('X')
    for col in ['NM', 'DN']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper().eq('X')
    for col in ['A', 'B', 'C', 'D', 'NM', 'DN']:
        if col in df.columns:
            df[f'pendencia_{col}'] = ~df[col].fillna(False).astype(bool)
    return df


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


def normalizar_colunas_cadastro(cad):
    cad = cad.copy()
    ren = {}
    for c in cad.columns:
        cl = str(c).strip().lower()
        if cl in ['nome completo', 'nome', 'paciente']:
            ren[c] = 'Nome Completo'
        elif cl in ['cns']:
            ren[c] = 'CNS'
        elif cl in ['data nascimento', 'data de nascimento', 'nascimento']:
            ren[c] = 'Data de Nascimento'
        elif cl in ['endereço', 'endereco']:
            ren[c] = 'Endereço'
        elif cl in ['equipe área', 'equipe area']:
            ren[c] = 'Equipe Área'
        elif cl in ['microárea', 'microarea']:
            ren[c] = 'Microárea'
        elif cl in ['equipe vínculo', 'equipe vinculo']:
            ren[c] = 'Equipe Vínculo'
    cad = cad.rename(columns=ren)
    cad = remover_colunas_duplicadas(cad)
    return cad


def cruzar_siaps_com_cadastro(df_siaps, df_cadastro):
    siaps = deduplicar_por_cpf(df_siaps.copy())
    cad = normalizar_colunas_cadastro(df_cadastro.copy())
    cad = deduplicar_por_cpf(cad)

    siaps['CPF_norm'] = normalizar_cpf(siaps['CPF']) if 'CPF' in siaps.columns else ''
    cad['CPF_norm'] = normalizar_cpf(cad['CPF']) if 'CPF' in cad.columns else ''

    cad_cols = ['Nome Completo', 'CNS', 'Data de Nascimento', 'Idade', 'Endereço', 'Equipe Área', 'Microárea', 'Equipe Vínculo']
    cad = cad[['CPF_norm'] + [c for c in cad_cols if c in cad.columns]].drop_duplicates('CPF_norm') if 'CPF_norm' in cad.columns else cad

    merged = siaps.merge(cad, on='CPF_norm', how='left', suffixes=('_siaps', '_cad'))
    merged['_match_complementar'] = merged['CPF_norm'].isin(cad['CPF_norm']) if 'CPF_norm' in cad.columns else False

    priority = {
        'Nome Completo': ['Nome Completo_cad', 'Nome Completo_siaps'],
        'CNS': ['CNS_cad', 'CNS_siaps'],
        'Data de Nascimento': ['Data de Nascimento_cad', 'Data de Nascimento_siaps'],
        'Idade': ['Idade_cad', 'Idade_siaps'],
        'Endereço': ['Endereço_cad', 'Endereço_siaps'],
        'Equipe Área': ['Equipe Área_cad', 'Equipe Área_siaps'],
        'Microárea': ['Microárea_cad', 'Microárea_siaps'],
        'Equipe Vínculo': ['Equipe Vínculo_cad', 'Equipe Vínculo_siaps'],
        'Sexo': ['Sexo_siaps'],
        'Raça': ['Raça_siaps']
    }

    for out_col, sources in priority.items():
        merged[out_col] = pd.NA
        for src in sources:
            if src in merged.columns:
                merged[out_col] = merged[out_col].combine_first(merged[src])

    merged['Encontrado na SIAPS'] = True
    merged['Encontrado na Complementar'] = merged['_match_complementar']
    merged['Origem'] = merged['_match_complementar'].map({True: 'SIAPS + Complementar', False: 'Apenas SIAPS'})
    merged = merged.drop(columns=['CPF_norm', '_match_complementar'], errors='ignore')
    merged = remover_colunas_duplicadas(merged)
    return merged

def contar_boas_praticas(df):
    m = {}
    for k in ['A', 'B', 'C', 'D']:
        m[k] = int(df.get(k, pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if k in df.columns else 0
    return m


def barra(df, x, y, title):
    fig = px.bar(df, x=x, y=y, title=title, text=y)
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)


def exibir_card(l1, v1, l2=None, v2=None):
    cols = st.columns(2 if l2 is not None else 1)
    cols[0].metric(l1, v1)
    if l2 is not None:
        cols[1].metric(l2, v2)


def main():
    arq_siaps = file_uploader_compat('Envie a planilha SIAPS', type=['csv','xlsx','xls'])
    arq_cad = file_uploader_compat('Envie a planilha complementar', type=['csv','xlsx','xls'])
    if arq_siaps is None or arq_cad is None:
        st.info('Envie as duas planilhas para iniciar.')
        return

    def carregar_siaps_bruto(arquivo):
        nome = arquivo.name.lower()
        if nome.endswith(('.xlsx', '.xls')):
            arquivo.seek(0)
            bruto = pd.read_excel(arquivo, header=None)
        else:
            bruto = carregar_planilha_generica(arquivo)
            if list(bruto.columns) and 'CPF' in [str(c).strip() for c in bruto.columns]:
                return bruto
            arquivo.seek(0)
            for enc in ['utf-8', 'latin1', 'cp1252']:
                try:
                    bruto = pd.read_csv(arquivo, header=None, encoding=enc)
                    break
                except Exception:
                    arquivo.seek(0)
            else:
                arquivo.seek(0)
                bruto = pd.read_csv(arquivo, header=None, encoding='latin1')
        header_idx = None
        for i in range(min(len(bruto), 40)):
            vals = ' '.join(bruto.iloc[i].fillna('').astype(str).tolist()).lower()
            if 'cpf' in vals and 'cns' in vals and 'nascimento' in vals and 'sexo' in vals and ('raça cor' in vals or 'raca cor' in vals) and 'cnes' in vals and 'ine' in vals and 'a' in vals and 'b' in vals and 'c' in vals and 'd' in vals:
                header_idx = i
                break
        if header_idx is None:
            return pd.DataFrame()
        header = [str(x).strip() for x in bruto.iloc[header_idx].tolist()]
        dados = bruto.iloc[header_idx+1:].copy()
        dados.columns = header
        dados = remover_colunas_duplicadas(dados)
        return dados

    df_siaps = carregar_siaps_bruto(arq_siaps)
    df_siaps.columns = [str(c).strip() for c in df_siaps.columns]
    df_siaps = limpar_siaps_hipertensao(df_siaps)
    tipo = detectar_tipo_siaps(df_siaps, arq_siaps.name)
    if tipo != 'SIAPS_HIPERTENSAO_BOAS_PRATICAS':
        st.error('Não foi possível identificar a planilha SIAPS de hipertensão.')
        return

    df_cad = carregar_base_cadastro(arq_cad)
    merged = cruzar_siaps_com_cadastro(df_siaps, df_cad)
    merged = preparar_siaps_hipertensao_boas_praticas(merged)

    siaps_total = int(merged['Encontrado na SIAPS'].fillna(False).astype(bool).sum()) if 'Encontrado na SIAPS' in merged.columns else 0
    comum = int((merged['Encontrado na SIAPS'].fillna(False).astype(bool) & merged['Encontrado na Complementar'].fillna(False).astype(bool)).sum())
    so_siaps = int((merged['Encontrado na SIAPS'].fillna(False).astype(bool) & ~merged['Encontrado na Complementar'].fillna(False).astype(bool)).sum())
    so_cad = int((~merged['Encontrado na SIAPS'].fillna(False).astype(bool) & merged['Encontrado na Complementar'].fillna(False).astype(bool)).sum())

    st.sidebar.header('Filtros da busca ativa')
    view = st.sidebar.selectbox('Visualização', ['Todos', 'Somente em comum', 'Somente SIAPS', 'Somente complementar'])
    eq = st.sidebar.selectbox('Equipe', ['Todas'] + sorted([x for x in merged.get('Equipe Área', pd.Series(dtype=str)).dropna().astype(str).str.strip().unique() if x])) if 'Equipe Área' in merged.columns else 'Todas'
    mi = st.sidebar.selectbox('Microárea', ['Todas'] + sorted([x for x in merged.get('Microárea', pd.Series(dtype=str)).dropna().astype(str).str.strip().unique() if x])) if 'Microárea' in merged.columns else 'Todas'
    faixa = st.sidebar.selectbox('Faixa etária', ['Todas', '0-17', '18-39', '40-59', '60+'])
    pend = st.sidebar.selectbox('Pendência', ['Todas', 'A', 'B', 'C', 'D'])

    merged = remover_colunas_duplicadas(merged)
    vis = merged.copy()
    if view == 'Somente em comum': vis = vis[vis['Encontrado na SIAPS'] & vis['Encontrado na Complementar']]
    elif view == 'Somente SIAPS': vis = vis[vis['Encontrado na SIAPS'] & ~vis['Encontrado na Complementar']]
    elif view == 'Somente complementar': vis = vis[~vis['Encontrado na SIAPS'] & vis['Encontrado na Complementar']]
    if eq != 'Todas' and 'Equipe Área' in vis.columns: vis = vis[vis['Equipe Área'].astype(str).str.strip() == eq]
    if mi != 'Todas' and 'Microárea' in vis.columns: vis = vis[vis['Microárea'].astype(str).str.strip() == mi]
    if faixa != 'Todas' and 'Idade' in vis.columns:
        a,b = {'0-17':(0,17),'18-39':(18,39),'40-59':(40,59),'60+':(60,200)}[faixa]
        vis = vis[pd.to_numeric(vis['Idade'], errors='coerce').between(a,b,inclusive='both')]
    if pend != 'Todas' and f'pendencia_{pend}' in vis.columns: vis = vis[vis[f'pendencia_{pend}']]

    m = contar_boas_praticas(merged)
    st.metric('SIAPS total', siaps_total)
    st.metric('Em comum', comum)
    st.metric('Só SIAPS', so_siaps)
    st.metric('Só complementar', so_cad)
    st.metric('Exibidos após filtros', len(vis))

    cols = ['Nome Completo','CPF','CNS','Data de Nascimento','Idade','Endereço','Equipe Área','Microárea','Equipe Vínculo','Sexo','Raça','A','B','C','D','Encontrado na SIAPS','Encontrado na Complementar']
    for c in cols:
        if c not in vis.columns: vis[c] = ''

    st.subheader('Lista Nominal SIAPS')
    vis = remover_colunas_duplicadas(vis)
    vis = vis.loc[:, [c for i, c in enumerate(cols) if c in vis.columns and c not in cols[:i]]].copy()
    st.dataframe(remover_colunas_duplicadas(vis), use_container_width=True)
    st.caption(f'Total após filtros: {len(vis)}')


if __name__ == '__main__':
    main()
