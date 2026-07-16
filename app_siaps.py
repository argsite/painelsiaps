import streamlit as st
import pandas as pd
import io
from io import BytesIO
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Dashboard APS - Hipertensão e Diabetes")

st.markdown("""
<style>
.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:0.5rem 0 1rem 0}
.metric-card{border-radius:16px;padding:14px 16px;border:1px solid rgba(15,23,42,.08);box-shadow:0 1px 3px rgba(15,23,42,.05);background:#fff}
.metric-card-label{font-size:.92rem;line-height:1.25;color:#334155;margin-bottom:10px;min-height:2.5em;display:flex;align-items:flex-start;gap:8px}
.metric-card-value{font-size:clamp(1.65rem,2.6vw,2.2rem);font-weight:700;line-height:1.05;color:#0f172a;letter-spacing:-0.02em;word-break:break-word}
@media (max-width:640px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.metric-card{padding:12px 12px;border-radius:14px}.metric-card-label{font-size:.84rem;min-height:2.8em}.metric-card-value{font-size:1.7rem}}
</style>
""", unsafe_allow_html=True)

st.title("Dashboard APS - Hipertensão e Diabetes")
st.caption("Painel para acompanhamento territorial, busca ativa e monitoramento por equipe e microárea.")

def carregar_planilha(arquivo):
    nome = arquivo.name.lower()
    if nome.endswith('.xlsx'):
        return pd.read_excel(arquivo)
    if nome.endswith('.xls'):
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
        if any(chave in c for 
