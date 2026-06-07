import os
import json
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import requests

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meningite | Vigilância Epidemiológica",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paleta (mesma identidade visual do SIVEP) ─────────────────────────────────
LARANJA        = "#E8600A"
LARANJA_CLARO  = "#F28C3A"
LARANJA_ESCURO = "#B84A06"
FUNDO_ESCURO   = "#1A1208"
FUNDO_CARD     = "#231A0E"
FUNDO_SIDEBAR  = "#1E1309"
TEXTO_CLARO    = "#F5E6D3"
TEXTO_MUTED    = "#A8876A"
CINZA_LINHA    = "#3D2E1E"
AMARELO_ACC    = "#F5B841"
AZUL_LINHA     = "#4A9EBF"
VERDE_LINHA    = "#5DBF7A"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {FUNDO_ESCURO};
    color: {TEXTO_CLARO};
}}
section[data-testid="stSidebar"] {{
    background-color: {FUNDO_SIDEBAR} !important;
    border-right: 1px solid {CINZA_LINHA};
}}
section[data-testid="stSidebar"] * {{ color: {TEXTO_CLARO} !important; }}
.stApp {{ background-color: {FUNDO_ESCURO}; }}
.main .block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; }}

.metric-card {{
    background: {FUNDO_CARD};
    border: 1px solid {CINZA_LINHA};
    border-top: 3px solid {LARANJA};
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
    position: relative;
}}
.metric-card .label {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {TEXTO_MUTED};
    margin-bottom: 0.3rem;
}}
.metric-card .value {{
    font-family: 'Syne', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    color: {LARANJA};
    line-height: 1;
}}
.metric-card .sub {{
    font-size: 0.72rem;
    color: {TEXTO_MUTED};
    margin-top: 0.2rem;
}}
.metric-card .sub-kpi {{
    position: absolute;
    top: 1rem;
    right: 1rem;
    text-align: right;
}}
.metric-card .sub-kpi .sub-label {{
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {TEXTO_MUTED};
}}
.metric-card .sub-kpi .sub-value {{
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: {AZUL_LINHA};
}}

.section-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: {TEXTO_CLARO};
    margin-bottom: 0.2rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid {LARANJA};
    display: inline-block;
}}
.section-subtitle {{
    font-size: 0.78rem;
    color: {TEXTO_MUTED};
    margin-bottom: 1rem;
}}
.app-header {{
    background: linear-gradient(135deg, {LARANJA_ESCURO} 0%, {LARANJA} 60%, {LARANJA_CLARO} 100%);
    border-radius: 10px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}}
.app-header h1 {{
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: #fff;
    margin: 0;
    line-height: 1.1;
}}
.app-header p {{
    font-size: 0.8rem;
    color: rgba(255,255,255,0.75);
    margin: 0.2rem 0 0 0;
}}
.divider {{
    height: 1px;
    background: {CINZA_LINHA};
    margin: 1.8rem 0 1.4rem 0;
}}
.styled-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
}}
.styled-table th {{
    background: {LARANJA_ESCURO};
    color: #fff;
    font-family: 'Syne', sans-serif;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.6rem 0.9rem;
    text-align: left;
}}
.styled-table td {{
    padding: 0.5rem 0.9rem;
    border-bottom: 1px solid {CINZA_LINHA};
    color: {TEXTO_CLARO};
}}
.styled-table tr:nth-child(even) td {{ background: rgba(255,255,255,0.03); }}
.styled-table tr:hover td {{ background: rgba(232,96,10,0.08); }}
.styled-table td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.styled-table td.pct {{
    text-align: left;
    font-size: 0.72rem;
    color: {TEXTO_MUTED};
    padding-left: 0.3rem;
}}
.styled-table td.uf {{
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    color: {LARANJA_CLARO};
}}
.legend-box {{
    background: {FUNDO_CARD};
    border: 1px solid {CINZA_LINHA};
    border-radius: 8px;
    padding: 1rem;
    margin-top: 0.5rem;
}}
.legend-item {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
    font-size: 0.78rem;
    color: {TEXTO_CLARO};
}}
.legend-dot {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    flex-shrink: 0;
}}
div[data-baseweb="select"] > div {{
    background-color: {FUNDO_CARD} !important;
    border-color: {CINZA_LINHA} !important;
    color: {TEXTO_CLARO} !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def layout_plotly(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=TEXTO_CLARO, size=11),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO_CLARO, size=10)),
        xaxis=dict(gridcolor=CINZA_LINHA, linecolor=CINZA_LINHA, tickfont=dict(color=TEXTO_MUTED)),
        yaxis=dict(gridcolor=CINZA_LINHA, linecolor=CINZA_LINHA, tickfont=dict(color=TEXTO_MUTED)),
    )
    return fig


SIGLA_PARA_NOME = {
    "AC":"Acre","AL":"Alagoas","AP":"Amapá","AM":"Amazonas","BA":"Bahia",
    "CE":"Ceará","DF":"Distrito Federal","ES":"Espírito Santo","GO":"Goiás",
    "MA":"Maranhão","MT":"Mato Grosso","MS":"Mato Grosso do Sul","MG":"Minas Gerais",
    "PA":"Pará","PB":"Paraíba","PR":"Paraná","PE":"Pernambuco","PI":"Piauí",
    "RJ":"Rio de Janeiro","RN":"Rio Grande do Norte","RS":"Rio Grande do Sul",
    "RO":"Rondônia","RR":"Roraima","SC":"Santa Catarina","SP":"São Paulo",
    "SE":"Sergipe","TO":"Tocantins",
}


@st.cache_data
def carregar_dados(base_dir: str) -> dict:
    proc = os.path.join(base_dir, "data", "processed")
    d = {}
    for nome in ["visao_geral", "evolucao_semanal",
                 "tendencia_notif", "tendencia_conf", "tendencia_mening"]:
        p = os.path.join(proc, f"{nome}.parquet")
        if os.path.exists(p):
            d[nome] = pd.read_parquet(p)
    # Perfis por subgrupo
    for sufixo in ["todos", "confirmados", "meningococica", "sorogrupo_b"]:
        for tabela in ["faixa_etaria", "sexo", "sintomas", "evolucao"]:
            p = os.path.join(proc, f"{tabela}_{sufixo}.parquet")
            if os.path.exists(p):
                d[f"{tabela}_{sufixo}"] = pd.read_parquet(p)
    return d


@st.cache_data
def carregar_base_enriquecida(base_dir: str) -> pd.DataFrame:
    p = Path(base_dir) / "data" / "processed" / "base_enriquecida.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.DataFrame()


@st.cache_data
def carregar_metadata(base_dir: str) -> dict:
    p = Path(base_dir) / "data" / "processed" / "metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data
def carregar_geojson():
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    try:
        return requests.get(url, timeout=15).json()
    except Exception:
        return None


def faixa_etaria(idade_anos: pd.Series) -> pd.Series:
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, np.inf]
    labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
    return pd.cut(idade_anos, bins=bins, labels=labels, right=False)


def top5_com_outros(serie_contagem: pd.Series, col_nome: str) -> pd.DataFrame:
    serie_contagem = serie_contagem.dropna()
    if serie_contagem.empty:
        return pd.DataFrame(columns=[col_nome, "total"])

    top5 = serie_contagem.nlargest(5).rename_axis(col_nome).reset_index(name="total")
    resto = int(serie_contagem.drop(top5[col_nome]).sum())
    if resto > 0:
        if (top5[col_nome] == "Outros").any():
            top5.loc[top5[col_nome] == "Outros", "total"] += resto
        else:
            top5 = pd.concat(
                [top5, pd.DataFrame([{col_nome: "Outros", "total": resto}])],
                ignore_index=True,
            )
    return top5


def calcular_tendencia_uf(evolucao: pd.DataFrame, coluna: str = "total") -> pd.DataFrame:
    if evolucao.empty:
        return pd.DataFrame(columns=["uf_notificacao", "slope"])

    semanas = sorted(evolucao["sem_label"].dropna().unique())
    ultimas6 = semanas[-6:] if len(semanas) >= 6 else semanas
    df6 = evolucao[evolucao["sem_label"].isin(ultimas6)].copy()
    sem_idx = {s: i for i, s in enumerate(ultimas6)}
    df6["sem_idx"] = df6["sem_label"].map(sem_idx)

    resultados = []
    for uf, grupo in df6.groupby("uf_notificacao"):
        grupo = grupo.sort_values("sem_idx")
        if len(grupo) >= 3:
            x = grupo["sem_idx"].to_numpy(dtype=float)
            y = grupo[coluna].fillna(0).to_numpy(dtype=float)
            if np.unique(x).size >= 2:
                slope = float(np.polyfit(x, y, 1)[0])
            else:
                slope = 0.0
        else:
            slope = 0.0
        resultados.append({"uf_notificacao": uf, "slope": round(float(slope), 2)})
    return pd.DataFrame(resultados)


def contar_sintomas(df_sub: pd.DataFrame) -> pd.DataFrame:
    mapa_sintomas = {
        "CLI_CEFALE": "Cefaleia",
        "CLI_FEBRE": "Febre",
        "CLI_VOMITO": "Vomito",
        "CLI_CONVUL": "Convulsoes",
        "CLI_RIGIDE": "Rigidez de Nuca",
        "CLI_KERNIG": "Kernig/Brudzinski",
        "CLI_ABAULA": "Abaulamento de Fontanela",
        "CLI_COMA": "Coma",
        "CLI_PETEQU": "Petequias/Sufusoes",
        "CLI_OUTRAS": "Outros Sintomas",
    }
    sint_counts = {}
    for col, label in mapa_sintomas.items():
        if col in df_sub.columns:
            sint_counts[label] = int((pd.to_numeric(df_sub[col], errors="coerce") == 1).sum())
    return top5_com_outros(pd.Series(sint_counts).sort_values(ascending=False), "sintoma")


def gerar_tabelas_dashboard(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "visao_geral": pd.DataFrame(),
            "evolucao_semanal": pd.DataFrame(),
            "faixa_etaria": pd.DataFrame(),
            "sexo": pd.DataFrame(),
            "sintomas": pd.DataFrame(),
            "evolucao": pd.DataFrame(),
            "tendencia_notif": pd.DataFrame(),
            "tendencia_conf": pd.DataFrame(),
            "tendencia_mening": pd.DataFrame(),
        }

    visao_geral = (
        df.groupby("uf_notificacao", dropna=False)
        .agg(
            total_notificacoes=("TP_NOT", "count"),
            total_confirmados=("is_confirmado", "sum"),
            total_meningococica=("is_meningococica", "sum"),
            total_sorogrupo_b=("is_sorogrupo_b", "sum"),
            total_outro_tipo=("is_outro_tipo", "sum"),
        )
        .reset_index()
        .sort_values("total_notificacoes", ascending=False)
    )

    evolucao_semanal = (
        df.groupby(["uf_notificacao", "sem_label"], dropna=False)
        .agg(
            total_notificacoes=("TP_NOT", "count"),
            total_confirmados=("is_confirmado", "sum"),
            total_meningococica=("is_meningococica", "sum"),
            total_sorogrupo_b=("is_sorogrupo_b", "sum"),
        )
        .reset_index()
        .sort_values(["uf_notificacao", "sem_label"])
    )

    df_conf = df[df["is_confirmado"] == 1]
    faixa_df = (
        df_conf["faixa_etaria"]
        .value_counts()
        .reindex(["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"])
        .fillna(0)
        .astype(int)
        .reset_index()
        .rename(columns={"index": "faixa_etaria", "faixa_etaria": "total"})
    )

    sexo_df = (
        df_conf["sexo_label"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "sexo", "sexo_label": "total"})
    )

    sintomas_df = contar_sintomas(df_conf)

    evolucao_df = (
        df_conf["evolucao_label"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "evolucao", "evolucao_label": "total"})
    )

    tend_notif = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao", "sem_label", "total_notificacoes"]].rename(
            columns={"total_notificacoes": "total"}
        ),
        "total",
    )
    tend_conf = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao", "sem_label", "total_confirmados"]].rename(
            columns={"total_confirmados": "total"}
        ),
        "total",
    )
    tend_mening = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao", "sem_label", "total_meningococica"]].rename(
            columns={"total_meningococica": "total"}
        ),
        "total",
    )

    def salvar_perfis(df_sub: pd.DataFrame, sufixo: str) -> dict[str, pd.DataFrame]:
        fe = (
            df_sub["faixa_etaria"]
            .value_counts()
            .reindex(["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"])
            .fillna(0)
            .astype(int)
            .reset_index()
            .rename(columns={"index": "faixa_etaria", "faixa_etaria": "total"})
        )
        sx = (
            df_sub["sexo_label"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "sexo", "sexo_label": "total"})
        )
        sint = contar_sintomas(df_sub)
        evo_ = (
            df_sub["evolucao_label"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "evolucao", "evolucao_label": "total"})
        )
        return {
            f"faixa_etaria_{sufixo}": fe,
            f"sexo_{sufixo}": sx,
            f"sintomas_{sufixo}": sint,
            f"evolucao_{sufixo}": evo_,
        }

    dados_gerados = {
        "visao_geral": visao_geral,
        "evolucao_semanal": evolucao_semanal,
        "faixa_etaria": faixa_df,
        "sexo": sexo_df,
        "sintomas": sintomas_df,
        "evolucao": evolucao_df,
        "tendencia_notif": tend_notif,
        "tendencia_conf": tend_conf,
        "tendencia_mening": tend_mening,
    }
    dados_gerados.update(salvar_perfis(df, "todos"))
    dados_gerados.update(salvar_perfis(df_conf, "confirmados"))
    dados_gerados.update(salvar_perfis(df[df["is_meningococica"] == True], "meningococica"))
    dados_gerados.update(salvar_perfis(df[df["is_sorogrupo_b"] == True], "sorogrupo_b"))
    return dados_gerados


# ── Carrega dados ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
geojson = carregar_geojson()
metadata = carregar_metadata(BASE_DIR)
base = carregar_base_enriquecida(BASE_DIR)

if base.empty:
    st.error("Nao foi possivel localizar a base enriquecida. Execute o ETL antes de abrir o dashboard.")
    st.stop()

base["DT_NOTIFIC"] = pd.to_datetime(base["DT_NOTIFIC"], errors="coerce")
anos_disponiveis = sorted(base["DT_NOTIFIC"].dt.year.dropna().astype(int).unique().tolist())

if not anos_disponiveis:
    st.error("A base nao possui valores validos em DT_NOTIFIC para montar o filtro de ano.")
    st.stop()

ultima_atualizacao = metadata.get("generated_at", "N/D")
fonte_dados = metadata.get("source", "desconhecida")
ultima_sem = base["sem_label"].dropna().max() if "sem_label" in base.columns else "N/D"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='margin-bottom:1.5rem'>
        <div style='font-family:Syne,sans-serif;font-size:1.1rem;font-weight:800;color:{LARANJA}'>
            🧠 SINAN · Meningite
        </div>
        <div style='font-size:0.72rem;color:{TEXTO_MUTED};margin-top:0.2rem'>
            Vigilância Epidemiológica 2026
        </div>
    </div>
    <div style='margin-top:2rem;padding-top:1rem;border-top:1px solid {CINZA_LINHA};
                font-size:0.68rem;color:{TEXTO_MUTED};line-height:1.6'>
        Fonte: SINAN / Ministério da Saúde<br>
        Origem da base: <b style='color:{LARANJA_CLARO}'>{fonte_dados}</b><br>
        Atualizado em: <b style='color:{LARANJA_CLARO}'>{ultima_atualizacao}</b><br>
        Última Semana Epidemiológica disponível: <b style='color:{LARANJA_CLARO}'>{ultima_sem}</b><br>
    </div>
    <div style='margin-top:1rem;padding-top:1rem;border-top:1px solid {CINZA_LINHA};
                font-size:0.70rem;color:{TEXTO_MUTED};line-height:1.8'>
        <b style='color:{TEXTO_CLARO}'>Projeto de Exploração de Dados Públicos</b><br>
        Objetivo: Prova de Conceito<br>
        Autor: Matheus Rodrigues
    </div>
    <div style='margin-top:1rem;padding:0.8rem;background:{FUNDO_CARD};
                border-left:3px solid {LARANJA};border-radius:4px;
                font-size:0.65rem;color:{TEXTO_MUTED};line-height:1.6'>
        ⚠ Os dados contidos nesse dash estão sujeitos à revisão, considere esse ponto ao fazer análises a partir dos mesmos.
    </div>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
    <div>🧠</div>
    <div>
        <h1>Vigilância de Meningite — Brasil 2025/2026</h1>
        <p>Sistema de Informação de Agravos de Notificação · SINAN · Ministério da Saúde</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
filtro_col, _ = st.columns([1, 3])
with filtro_col:
    st.markdown(
        f"<div style='font-size:0.72rem;color:{TEXTO_MUTED};text-transform:uppercase;"
        f"letter-spacing:0.08em;margin-bottom:0.3rem'>Ano da Notificacao</div>",
        unsafe_allow_html=True,
    )
    opcao_ano = st.selectbox(
        "Ano",
        options=["Todos"] + [str(ano) for ano in anos_disponiveis],
        index=1 if "2026" in [str(ano) for ano in anos_disponiveis] else 0,
        label_visibility="collapsed",
        key="filtro_ano_notificacao",
    )

ano_selecionado = None if opcao_ano == "Todos" else int(opcao_ano)
base_filtrada = base if ano_selecionado is None else base[base["DT_NOTIFIC"].dt.year == ano_selecionado].copy()

if base_filtrada.empty:
    st.warning("Nao ha registros para o ano selecionado.")
    st.stop()

dados = gerar_tabelas_dashboard(base_filtrada)
vg  = dados.get("visao_geral", pd.DataFrame())
es  = dados.get("evolucao_semanal", pd.DataFrame())
fe  = dados.get("faixa_etaria",  pd.DataFrame())
sx  = dados.get("sexo",          pd.DataFrame())
sin = dados.get("sintomas",      pd.DataFrame())
evo = dados.get("evolucao",      pd.DataFrame())

ultima_sem = es["sem_label"].dropna().max() if not es.empty else "N/D"
ultima_atualizacao = metadata.get("generated_at", "N/D")
fonte_dados = metadata.get("source", "desconhecida")

total_notif    = int(vg["total_notificacoes"].sum())
total_conf     = int(vg["total_confirmados"].sum())
total_mening   = int(vg["total_meningococica"].sum())
total_sorob    = int(vg["total_sorogrupo_b"].sum())
total_outro    = int(vg["total_outro_tipo"].sum())
pct_conf       = total_conf   / total_notif  * 100 if total_notif  else 0
pct_mening     = total_mening / total_conf   * 100 if total_conf   else 0
pct_outro      = total_outro  / total_conf   * 100 if total_conf   else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Total de Notificações</div>
        <div class="value">{total_notif:,}</div>
        <div class="sub">Casos notificados no período</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Casos Confirmados</div>
        <div class="value" style="color:{LARANJA_CLARO}">{total_conf:,}</div>
        <div class="sub">{pct_conf:.1f}% do total notificado</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Meningite Meningocócica</div>
        <div class="value" style="color:{AMARELO_ACC}">{total_mening:,}</div>
        <div class="sub">{pct_mening:.1f}% dos confirmados</div>
        <div class="sub-kpi">
            <div class="sub-label">Sorogrupo B</div>
            <div class="sub-value">{total_sorob:,}</div>
        </div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Outros Tipos Confirmados</div>
        <div class="value" style="color:{TEXTO_MUTED}">{total_outro:,}</div>
        <div class="sub">{pct_outro:.1f}% dos confirmados</div>
    </div>""", unsafe_allow_html=True)


# ── Seção 1: Tabela por UF ────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Visão Geral por UF</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Distribuição de casos por Unidade Federativa de notificação</div>', unsafe_allow_html=True)

totais = pd.DataFrame([{
    "uf_notificacao":    "BRASIL",
    "total_notificacoes":  total_notif,
    "total_confirmados":   total_conf,
    "total_meningococica": total_mening,
    "total_sorogrupo_b":   total_sorob,
    "total_outro_tipo":    total_outro,
}])
tabela = pd.concat([vg, totais], ignore_index=True)

linhas = ""
for _, row in tabela.iterrows():
    uf   = str(row["uf_notificacao"])
    tn   = int(row["total_notificacoes"])
    tc   = int(row["total_confirmados"])
    tm   = int(row["total_meningococica"])
    tb   = int(row["total_sorogrupo_b"])
    to_  = int(row["total_outro_tipo"])
    pc   = tc / tn * 100 if tn else 0
    pm   = tm / tc * 100 if tc else 0
    po   = to_ / tc * 100 if tc else 0
    br   = uf == "BRASIL"
    etr  = 'style="background:rgba(232,96,10,0.12)"' if br else ""
    euf  = f'style="font-weight:800;color:{"#fff" if br else LARANJA_CLARO}"'
    linhas += f"""
    <tr {etr}>
        <td class="uf" {euf}>{uf}</td>
        <td class="num">{tn:,}</td>
        <td class="num">{tc:,}</td><td class="pct">({pc:.1f}%)</td>
        <td class="num">{tm:,}</td><td class="pct">({pm:.1f}%)</td>
        <td class="num">{tb:,}</td>
        <td class="num">{to_:,}</td><td class="pct">({po:.1f}%)</td>
    </tr>"""

st.markdown(f"""
<div style="max-height:400px;overflow-y:auto;border:1px solid {CINZA_LINHA};border-radius:8px">
<table class="styled-table">
    <thead><tr>
        <th>UF</th>
        <th style="text-align:right">Notificações</th>
        <th style="text-align:right">Confirmados</th><th>%</th>
        <th style="text-align:right">Meningocócica</th><th>%</th>
        <th style="text-align:right">Sorogrupo B</th>
        <th style="text-align:right">Outro Tipo</th><th>%</th>
    </tr></thead>
    <tbody>{linhas}</tbody>
</table>
</div>
""", unsafe_allow_html=True)


# ── Seção 2: Evolução — Notificações vs Confirmados ───────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Evolução de Casos por Semana Epidemiológica</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Notificações e confirmações ao longo do tempo</div>', unsafe_allow_html=True)

col_f1, _ = st.columns([2, 3])
with col_f1:
    st.markdown(f"<div style='font-size:0.72rem;color:{TEXTO_MUTED};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.3rem'>Estado de Notificação</div>", unsafe_allow_html=True)
    ufs = ["Todos"] + sorted(es["uf_notificacao"].dropna().unique().tolist())
    uf1 = st.selectbox("UF G1", ufs, index=0, label_visibility="collapsed", key="uf_g1")

df_g1 = (
    es.groupby("sem_label", as_index=False)
    .agg(total_notificacoes=("total_notificacoes","sum"), total_confirmados=("total_confirmados","sum"))
    if uf1 == "Todos"
    else es[es["uf_notificacao"] == uf1].copy()
)
df_g1 = df_g1.sort_values("sem_label")

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=df_g1["sem_label"], y=df_g1["total_notificacoes"],
    name="Total Notificado", mode="lines+markers",
    line=dict(color=LARANJA, width=2.5),
    marker=dict(size=5), fill="tozeroy", fillcolor="rgba(232,96,10,0.07)",
))
fig1.add_trace(go.Scatter(
    x=df_g1["sem_label"], y=df_g1["total_confirmados"],
    name="Total Confirmado", mode="lines+markers",
    line=dict(color=AZUL_LINHA, width=2.5, dash="dot"),
    marker=dict(size=5, color=AZUL_LINHA),
))
fig1 = layout_plotly(fig1, height=360)
fig1.update_xaxes(tickangle=-45)
st.plotly_chart(fig1, width="stretch")


# ── Seção 3: Evolução — Meningocócica vs Sorogrupo B ─────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Meningite Meningocócica e Sorogrupo B por Semana</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Casos confirmados de Meningite Meningocócica e Sorogrupo B</div>', unsafe_allow_html=True)

col_f2, _ = st.columns([2, 3])
with col_f2:
    st.markdown(f"<div style='font-size:0.72rem;color:{TEXTO_MUTED};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.3rem'>Estado de Notificação</div>", unsafe_allow_html=True)
    uf2 = st.selectbox("UF G2", ufs, index=0, label_visibility="collapsed", key="uf_g2")

df_g2 = (
    es.groupby("sem_label", as_index=False)
    .agg(total_meningococica=("total_meningococica","sum"), total_sorogrupo_b=("total_sorogrupo_b","sum"))
    if uf2 == "Todos"
    else es[es["uf_notificacao"] == uf2].copy()
)
df_g2 = df_g2.sort_values("sem_label")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df_g2["sem_label"], y=df_g2["total_meningococica"],
    name="Meningite Meningocócica", mode="lines+markers",
    line=dict(color=AMARELO_ACC, width=2.5),
    marker=dict(size=5, color=AMARELO_ACC),
    fill="tozeroy", fillcolor="rgba(245,184,65,0.07)",
))
fig2.add_trace(go.Scatter(
    x=df_g2["sem_label"], y=df_g2["total_sorogrupo_b"],
    name="Sorogrupo B", mode="lines+markers",
    line=dict(color=VERDE_LINHA, width=2.5, dash="dot"),
    marker=dict(size=5, color=VERDE_LINHA),
))
fig2 = layout_plotly(fig2, height=360)
fig2.update_xaxes(tickangle=-45)
st.plotly_chart(fig2, width="stretch")


# ── Seção 4: Mapa de Casos ────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Mapa de Casos</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Volume absoluto de casos confirmados por UF</div>', unsafe_allow_html=True)

col_fm, _ = st.columns([2, 3])
with col_fm:
    st.markdown(f"<div style='font-size:0.72rem;color:{TEXTO_MUTED};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.3rem'>Tipo de Caso</div>", unsafe_allow_html=True)
    tipo_mapa = st.selectbox(
        "Tipo Mapa",
        options=["Total de Casos Notificados", "Casos Confirmados de Meningite Meningocócica", "Casos Confirmados de Meningite Sorogrupo B"],
        index=0,
        label_visibility="collapsed",
        key="tipo_mapa",
    )

col_mapa_map = {
    "Total de Casos Notificados":                       "total_notificacoes",
    "Casos Confirmados de Meningite Meningocócica":     "total_meningococica",
    "Casos Confirmados de Meningite Sorogrupo B":       "total_sorogrupo_b",
}
coluna_mapa = col_mapa_map[tipo_mapa]

mapa_df = vg.copy()
mapa_df["nome_uf"] = mapa_df["uf_notificacao"].map(SIGLA_PARA_NOME)
mapa_df = mapa_df.dropna(subset=["nome_uf"])

col_map, col_leg = st.columns([4, 1])
with col_map:
    if geojson:
        fig_mapa = px.choropleth(
            mapa_df,
            geojson=geojson,
            locations="nome_uf",
            featureidkey="properties.name",
            color=coluna_mapa,
            color_continuous_scale=[
                [0.0,  "#1F0F08"],
                [0.25, "#6B3A1F"],
                [0.5,  "#C45A1A"],
                [0.75, "#E8600A"],
                [1.0,  "#FF4500"],
            ],
            hover_name="nome_uf",
            hover_data={coluna_mapa: True, "nome_uf": False},
            labels={coluna_mapa: "Casos"},
        )
        fig_mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
        fig_mapa.update_layout(
            height=480,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color=TEXTO_CLARO),
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_colorbar=dict(
                title="Casos",
                tickfont=dict(color=TEXTO_CLARO),
                title_font=dict(color=TEXTO_CLARO),
                bgcolor="rgba(0,0,0,0)",
                bordercolor=CINZA_LINHA,
            ),
        )
        st.plotly_chart(fig_mapa, width="stretch")
    else:
        st.warning("Não foi possível carregar o GeoJSON. Verifique a conexão.")

with col_leg:
    st.markdown(f"""
    <div class="legend-box" style="margin-top:3rem">
        <div style="font-family:Syne,sans-serif;font-size:0.8rem;font-weight:700;
                    color:{TEXTO_CLARO};margin-bottom:0.8rem">
            Volume<br><span style="font-size:0.68rem;color:{TEXTO_MUTED}">Casos absolutos</span>
        </div>
        <div class="legend-item"><div class="legend-dot" style="background:#FF4500"></div>Muito alto</div>
        <div class="legend-item"><div class="legend-dot" style="background:#E8600A"></div>Alto</div>
        <div class="legend-item"><div class="legend-dot" style="background:#C45A1A"></div>Médio</div>
        <div class="legend-item"><div class="legend-dot" style="background:#6B3A1F"></div>Baixo</div>
        <div class="legend-item"><div class="legend-dot" style="background:#1F0F08"></div>Muito baixo</div>
    </div>
    """, unsafe_allow_html=True)


# ── Seção 5: Perfil do Paciente ───────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Perfil do Paciente</div>', unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Distribuição demográfica e clínica dos casos</div>', unsafe_allow_html=True)

col_fp, _ = st.columns([2, 3])
with col_fp:
    st.markdown(f"<div style='font-size:0.72rem;color:{TEXTO_MUTED};text-transform:uppercase;"
                f"letter-spacing:0.08em;margin-bottom:0.3rem'>Tipo de Caso</div>",
                unsafe_allow_html=True)
    tipo_perfil = st.selectbox(
        "Tipo Perfil",
        options=["Todos os Notificados", "Casos Confirmados",
                 "Confirmados Meningite Meningocócica", "Confirmados Sorogrupo B"],
        index=1,
        label_visibility="collapsed",
        key="tipo_perfil",
    )

sufixo_perfil = {
    "Todos os Notificados":                "todos",
    "Casos Confirmados":                   "confirmados",
    "Confirmados Meningite Meningocócica": "meningococica",
    "Confirmados Sorogrupo B":             "sorogrupo_b",
}[tipo_perfil]

fe  = dados.get(f"faixa_etaria_{sufixo_perfil}", pd.DataFrame())
sx  = dados.get(f"sexo_{sufixo_perfil}",         pd.DataFrame())
sin = dados.get(f"sintomas_{sufixo_perfil}",     pd.DataFrame())
evo = dados.get(f"evolucao_{sufixo_perfil}",     pd.DataFrame())

# Linha 1: Faixa etária + Sexo
col_fe, col_sx = st.columns([3, 2])

with col_fe:
    st.markdown(f"<div style='font-size:0.8rem;color:{TEXTO_MUTED};margin-bottom:0.5rem'>"
                "Casos por Faixa Etária</div>", unsafe_allow_html=True)
    if not fe.empty:
        fe_plot = fe.copy()
        if "faixa_etaria" not in fe_plot.columns:
            fe_plot = fe_plot.rename(columns={fe_plot.columns[0]: "faixa_etaria",
                                              fe_plot.columns[1]: "total"})
        fig_fe = px.bar(
            fe_plot, x="faixa_etaria", y="total",
            color_discrete_sequence=[LARANJA],
            labels={"faixa_etaria": "Faixa Etária", "total": "Casos"},
        )
        fig_fe.update_traces(marker_line_width=0)
        fig_fe = layout_plotly(fig_fe, height=300)
        st.plotly_chart(fig_fe, width="stretch")

with col_sx:
    st.markdown(f"<div style='font-size:0.8rem;color:{TEXTO_MUTED};margin-bottom:0.5rem'>"
                "Casos por Sexo</div>", unsafe_allow_html=True)
    if not sx.empty:
        sx_plot = sx.copy()
        if "sexo" not in sx_plot.columns:
            sx_plot = sx_plot.rename(columns={sx_plot.columns[0]: "sexo",
                                              sx_plot.columns[1]: "total"})
        sx_plot   = sx_plot[sx_plot["sexo"] != "Ignorado"]
        total_gen = int(sx_plot["total"].sum())
        fig_sx = go.Figure(go.Pie(
            labels=sx_plot["sexo"], values=sx_plot["total"],
            hole=0.62,
            marker=dict(colors=[LARANJA, LARANJA_CLARO],
                        line=dict(color=FUNDO_ESCURO, width=2)),
            textfont=dict(color="#fff", size=11),
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        ))
        fig_sx.update_layout(
            height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color=TEXTO_CLARO),
            margin=dict(l=0, r=0, t=10, b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXTO_CLARO, size=11)),
            annotations=[dict(
                text=f"<b>{total_gen:,}</b>", x=0.5, y=0.5,
                font=dict(size=16, color=TEXTO_CLARO, family="Syne"), showarrow=False,
            )],
        )
        st.plotly_chart(fig_sx, width="stretch")

# Linha 2: Sintomas + Evolução
col_sin, col_evo = st.columns(2)

with col_sin:
    st.markdown(f"<div style='font-size:0.8rem;color:{TEXTO_MUTED};margin-bottom:0.5rem'>"
                "Top 5 Sinais e Sintomas</div>", unsafe_allow_html=True)
    if not sin.empty:
        sin_plot = sin.copy()
        if "sintoma" not in sin_plot.columns:
            sin_plot = sin_plot.rename(columns={sin_plot.columns[0]: "sintoma",
                                                sin_plot.columns[1]: "total"})
        sin_plot = sin_plot.sort_values("total", ascending=True)
        fig_sin = px.bar(
            sin_plot, x="total", y="sintoma", orientation="h",
            color_discrete_sequence=[LARANJA],
            labels={"sintoma": "", "total": "Casos"},
        )
        fig_sin.update_traces(marker_line_width=0)
        fig_sin = layout_plotly(fig_sin, height=300)
        st.plotly_chart(fig_sin, width="stretch")

with col_evo:
    st.markdown(f"<div style='font-size:0.8rem;color:{TEXTO_MUTED};margin-bottom:0.5rem'>"
                "Evolução dos Casos</div>", unsafe_allow_html=True)
    if not evo.empty:
        evo_plot = evo.copy()
        if "evolucao" not in evo_plot.columns:
            evo_plot = evo_plot.rename(columns={evo_plot.columns[0]: "evolucao",
                                                evo_plot.columns[1]: "total"})
        evo_plot = evo_plot.sort_values("total", ascending=True)
        cores_evo = {
            "Alta":                  VERDE_LINHA,
            "Óbito por Meningite":   LARANJA,
            "Óbito por Outra Causa": AMARELO_ACC,
            "Ignorado":              TEXTO_MUTED,
        }
        fig_evo = px.bar(
            evo_plot, x="total", y="evolucao", orientation="h",
            color="evolucao", color_discrete_map=cores_evo,
            labels={"evolucao": "", "total": "Casos"},
        )
        fig_evo.update_traces(marker_line_width=0)
        fig_evo = layout_plotly(fig_evo, height=300)
        fig_evo.update_layout(showlegend=False)
        st.plotly_chart(fig_evo, width="stretch")


# ── Rodapé ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:2rem;padding-top:1rem;border-top:1px solid {CINZA_LINHA};
            text-align:center;font-size:0.7rem;color:{TEXTO_MUTED}">
    Dados: SINAN / Ministério da Saúde ·
    Base atualizada em: <b style="color:{LARANJA_CLARO}">{ultima_atualizacao}</b> ·
    Última SE disponível: <b style="color:{LARANJA_CLARO}">{ultima_sem}</b> ·
    Dados sujeitos a revisão
</div>
""", unsafe_allow_html=True)
