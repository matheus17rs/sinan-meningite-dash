import os
import pandas as pd
import numpy as np
from scipy import stats as sp_stats

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR    = r"D:\Users\mathe\Arquivos\GSK\SINAN"
CAMINHO_CSV = os.path.join(BASE_DIR, "data", "raw", "meningite_sinan.csv")
DIR_OUT     = os.path.join(BASE_DIR, "data", "processed")

# ── Mapeamentos ───────────────────────────────────────────────────────────────
# Código IBGE (2 dígitos) → sigla UF
IBGE_PARA_UF = {
    11:"RO",12:"AC",13:"AM",14:"RR",15:"PA",16:"AP",17:"TO",
    21:"MA",22:"PI",23:"CE",24:"RN",25:"PB",26:"PE",27:"AL",
    28:"SE",29:"BA",31:"MG",32:"ES",33:"RJ",35:"SP",41:"PR",
    42:"SC",43:"RS",50:"MS",51:"MT",52:"GO",53:"DF",
}

# CON_DIAGES → label do tipo de meningite
TIPO_MENING = {
    1:  "Meningococcemia",
    2:  "Meningite Meningocócica",
    3:  "Mening. Meningocócica c/ Meningococcemia",
    4:  "Meningite Tuberculosa",
    5:  "Outras Bactérias",
    6:  "Meningite Não Especificada",
    7:  "Meningite Asséptica",
    8:  "Outra Etiologia",
    9:  "Meningite por Hemófilo",
    10: "Meningite por Pneumococo",
}

# CLA_SOROGR → sorogrupo
SOROGRUPO = {
    1:"A", 2:"B", 3:"C", 4:"D", 5:"X",
    6:"Y", 7:"Z", 8:"W135", 9:"29E",
}

# ── Funções auxiliares ────────────────────────────────────────────────────────
def carregar_raw(caminho: str) -> pd.DataFrame:
    try:
        return pd.read_csv(caminho, encoding="utf-8",  low_memory=False, on_bad_lines="skip")
    except Exception:
        return pd.read_csv(caminho, encoding="latin1", low_memory=False, on_bad_lines="skip")


def calcular_idade_anos(serie: pd.Series) -> pd.Series:
    """
    NU_IDADE_N do SINAN é um inteiro composto de 4 dígitos:
      1º dígito = unidade (1=hora, 2=dia, 3=mês, 4=ano)
      2-4º dígito = valor numérico
    Ex: 4001 → 1 ano | 3009 → 9 meses | 2015 → 15 dias
    """
    n = pd.to_numeric(serie, errors="coerce")
    unidade = (n // 1000).astype("Int64")
    valor   = (n  % 1000).astype(float)

    idade_anos = np.where(unidade == 4, valor,
                 np.where(unidade == 3, valor / 12,
                 np.where(unidade == 2, valor / 365,
                 np.where(unidade == 1, valor / 8760,
                          np.nan))))
    return pd.Series(idade_anos, index=serie.index)


def faixa_etaria(idade_anos: pd.Series) -> pd.Series:
    bins   = [0, 10, 20, 30, 40, 50, 60, 70, 80, np.inf]
    labels = ["0-9","10-19","20-29","30-39","40-49","50-59","60-69","70-79","80+"]
    return pd.cut(idade_anos, bins=bins, labels=labels, right=False)


def confirmar_caso(df: pd.DataFrame) -> pd.Series:
    """CLASSI_FIN == 1 → confirmado."""
    return (pd.to_numeric(df["CLASSI_FIN"], errors="coerce") == 1).astype(int)


def is_meningococica(df: pd.DataFrame) -> pd.Series:
    """CON_DIAGES IN (1,2,3) → Meningocócica (inclui Meningococcemia)."""
    diag = pd.to_numeric(df["CON_DIAGES"], errors="coerce")
    return (df["is_confirmado"] == 1) & diag.isin([1, 2, 3])


def is_sorogrupo_b(df: pd.DataFrame) -> pd.Series:
    """CLA_SOROGR == 2 → Sorogrupo B."""
    sg = pd.to_numeric(df["CLA_SOROGR"], errors="coerce")
    return (df["is_confirmado"] == 1) & (sg == 2)


def is_outro_tipo(df: pd.DataFrame) -> pd.Series:
    """Confirmado e NÃO meningocócica."""
    return (df["is_confirmado"] == 1) & (~df["is_meningococica"])


def processar_sem_pri(serie: pd.Series) -> pd.Series:
    """
    SEM_PRI formato AAAASS (ex: 202601).
    Retorna string 'AAAA-SE01'.
    """
    s = pd.to_numeric(serie, errors="coerce").dropna().astype(int).astype(str).str.zfill(6)
    return s.str[:4] + "-SE" + s.str[4:]


def top5_com_outros(serie_contagem: pd.Series, col_nome: str) -> pd.DataFrame:
    top5  = serie_contagem.nlargest(5)
    resto = serie_contagem.drop(top5.index).sum()
    if resto > 0:
        top5["Outros"] = top5.get("Outros", 0) + resto
    return top5.reset_index().rename(columns={"index": col_nome, 0: "total"})


def calcular_tendencia_uf(evolucao: pd.DataFrame, coluna: str = "total") -> pd.DataFrame:
    semanas  = sorted(evolucao["sem_label"].dropna().unique())
    ultimas6 = semanas[-6:] if len(semanas) >= 6 else semanas
    df6      = evolucao[evolucao["sem_label"].isin(ultimas6)].copy()
    sem_idx  = {s: i for i, s in enumerate(ultimas6)}
    df6["sem_idx"] = df6["sem_label"].map(sem_idx)

    resultados = []
    for uf, grupo in df6.groupby("uf_notificacao"):
        grupo = grupo.sort_values("sem_idx")
        if len(grupo) >= 3:
            slope, _, _, _, _ = sp_stats.linregress(
                grupo["sem_idx"], grupo[coluna].fillna(0)
            )
        else:
            slope = 0.0
        resultados.append({"uf_notificacao": uf, "slope": round(slope, 2)})
    return pd.DataFrame(resultados)


# ── ETL principal ─────────────────────────────────────────────────────────────
def executar_etl(caminho_csv: str):
    print("1/8 Carregando dados brutos...")
    df_raw = carregar_raw(caminho_csv)
    print(f"   {df_raw.shape[0]:,} linhas | {df_raw.shape[1]} colunas")
    df_raw["DT_SIN_PRI"] = pd.to_datetime(df_raw["DT_SIN_PRI"], errors="coerce")
    linhas_antes = len(df_raw)
    df_raw = df_raw[df_raw["DT_SIN_PRI"].dt.year >= 2025].copy()
    print(f"   {linhas_antes - len(df_raw)} linhas removidas (data < 2025) → {len(df_raw):,} linhas restantes")

    print("2/8 Calculando campos derivados...")
    novos = pd.DataFrame(index=df_raw.index)

    # UF — SG_UF_NOT vem como código IBGE inteiro (ex: 35 = SP)
    novos["uf_notificacao"] = (
        pd.to_numeric(df_raw["SG_UF_NOT"], errors="coerce")
        .astype("Int64")
        .map(IBGE_PARA_UF)
        .fillna(df_raw["SG_UF_NOT"].astype(str))  # fallback: usa o valor bruto
    )

    # Classificação e tipos
    novos["is_confirmado"]    = confirmar_caso(df_raw)

    diag = pd.to_numeric(df_raw["CON_DIAGES"], errors="coerce")
    sg   = pd.to_numeric(df_raw["CLA_SOROGR"], errors="coerce")

    novos["is_meningococica"] = (novos["is_confirmado"] == 1) & diag.isin([1, 2, 3])
    novos["is_sorogrupo_b"]   = (novos["is_confirmado"] == 1) & (sg == 2)
    novos["is_outro_tipo"]    = (novos["is_confirmado"] == 1) & ~novos["is_meningococica"]

    # Label do tipo
    novos["tipo_mening_label"] = diag.map(TIPO_MENING).fillna("Não especificado")

    # Sexo
    novos["sexo_label"] = (
        df_raw["CS_SEXO"].astype(str).str.strip()
        .map({"M": "Masculino", "F": "Feminino", "I": "Ignorado"})
        .fillna("Ignorado")
    )

    # Idade
    novos["idade_anos"]   = calcular_idade_anos(df_raw["NU_IDADE_N"])
    novos["faixa_etaria"] = faixa_etaria(novos["idade_anos"])

    # Semana epidemiológica dos primeiros sintomas
    sem_raw = df_raw["SEM_PRI"].astype(str).str.strip().str.zfill(6)
    novos["sem_label"] = sem_raw.str[:4] + "-SE" + sem_raw.str[4:]
    novos["sem_label"] = novos["sem_label"].where(
        novos["sem_label"].str.match(r"^\d{4}-SE\d{2}$"), other=None
    )

    # Evolução
    evo = pd.to_numeric(df_raw["EVOLUCAO"], errors="coerce")
    novos["evolucao_label"] = np.where(
        evo == 1, "Alta",
        np.where(evo == 2, "Óbito por Meningite",
        np.where(evo == 3, "Óbito por Outra Causa",
                 "Ignorado"  # 9, NaN e outros
        ))
    )

    df = pd.concat([df_raw, novos], axis=1).copy()

    # ── Tabela 1: KPIs e Visão Geral por UF ──────────────────────────────────
    print("3/8 Gerando visão geral por UF...")
    visao_geral = (
        df.groupby("uf_notificacao", dropna=False)
        .agg(
            total_notificacoes  =("TP_NOT",          "count"),
            total_confirmados   =("is_confirmado",    "sum"),
            total_meningococica =("is_meningococica", "sum"),
            total_sorogrupo_b   =("is_sorogrupo_b",  "sum"),
            total_outro_tipo    =("is_outro_tipo",    "sum"),
        )
        .reset_index()
        .sort_values("total_notificacoes", ascending=False)
    )

    # ── Tabela 2: Evolução semanal ────────────────────────────────────────────
    print("4/8 Gerando série temporal semanal...")
    evolucao_semanal = (
        df.groupby(["uf_notificacao", "sem_label"], dropna=False)
        .agg(
            total_notificacoes  =("TP_NOT",          "count"),
            total_confirmados   =("is_confirmado",    "sum"),
            total_meningococica =("is_meningococica", "sum"),
            total_sorogrupo_b   =("is_sorogrupo_b",  "sum"),
        )
        .reset_index()
        .sort_values(["uf_notificacao", "sem_label"])
    )

    # ── Tabela 3: Faixa etária (apenas confirmados) ───────────────────────────
    print("5/8 Gerando perfil etário...")
    df_conf = df[df["is_confirmado"] == 1]

    faixa_df = (
        df_conf["faixa_etaria"]
        .value_counts()
        .reindex(["0-9","10-19","20-29","30-39","40-49","50-59","60-69","70-79","80+"])
        .fillna(0).astype(int)
        .reset_index()
        .rename(columns={"index": "faixa_etaria", "faixa_etaria": "total"})
    )

    # ── Tabela 4: Sexo (apenas confirmados) ───────────────────────────────────
    sexo_df = (
        df_conf["sexo_label"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "sexo", "sexo_label": "total"})
    )

    # ── Tabela 5: Sintomas top 5 (apenas confirmados) ─────────────────────────
    print("6/8 Gerando sintomas e evolução...")
    mapa_sintomas = {
        "CLI_CEFALE": "Cefaleia",
        "CLI_FEBRE":  "Febre",
        "CLI_VOMITO": "Vômito",
        "CLI_CONVUL": "Convulsões",
        "CLI_RIGIDE": "Rigidez de Nuca",
        "CLI_KERNIG": "Kernig/Brudzinski",
        "CLI_ABAULA": "Abaulamento de Fontanela",
        "CLI_COMA":   "Coma",
        "CLI_PETEQU": "Petéquias/Sufusões",
        "CLI_OUTRAS": "Outros Sintomas",
    }
    sint_counts = {}
    for col, label in mapa_sintomas.items():
        if col in df_conf.columns:
            sint_counts[label] = int(
                (pd.to_numeric(df_conf[col], errors="coerce") == 1).sum()
            )
    sint_series = pd.Series(sint_counts).sort_values(ascending=False)
    sintomas_df = top5_com_outros(sint_series, "sintoma")

    # ── Tabela 6: Evolução (apenas confirmados) ───────────────────────────────
    evolucao_df = (
        df_conf["evolucao_label"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "evolucao", "evolucao_label": "total"})
    )

    # ── Tabela 7: Tendências por UF ───────────────────────────────────────────
    print("7/8 Calculando tendências...")
    tend_notif = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao","sem_label","total_notificacoes"]]
        .rename(columns={"total_notificacoes": "total"}), "total"
    )
    tend_conf = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao","sem_label","total_confirmados"]]
        .rename(columns={"total_confirmados": "total"}), "total"
    )
    tend_mening = calcular_tendencia_uf(
        evolucao_semanal[["uf_notificacao","sem_label","total_meningococica"]]
        .rename(columns={"total_meningococica": "total"}), "total"
    )

    # ── Salva Parquets ────────────────────────────────────────────────────────
    print("8/8 Salvando Parquets...")
    os.makedirs(DIR_OUT, exist_ok=True)

    visao_geral.to_parquet(    os.path.join(DIR_OUT, "visao_geral.parquet"),      index=False)
    evolucao_semanal.to_parquet(os.path.join(DIR_OUT, "evolucao_semanal.parquet"),index=False)
    tend_notif.to_parquet(     os.path.join(DIR_OUT, "tendencia_notif.parquet"),  index=False)
    tend_conf.to_parquet(      os.path.join(DIR_OUT, "tendencia_conf.parquet"),   index=False)
    tend_mening.to_parquet(    os.path.join(DIR_OUT, "tendencia_mening.parquet"), index=False)
    def salvar_perfis(df_sub: pd.DataFrame, sufixo: str):
        # Faixa etária
        fe = (
            df_sub["faixa_etaria"]
            .value_counts()
            .reindex(["0-9","10-19","20-29","30-39","40-49","50-59","60-69","70-79","80+"])
            .fillna(0).astype(int)
            .reset_index()
            .rename(columns={"index": "faixa_etaria", "faixa_etaria": "total"})
        )
        # Sexo
        sx = (
            df_sub["sexo_label"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "sexo", "sexo_label": "total"})
        )
        # Sintomas
        mapa_sintomas = {
            "CLI_CEFALE":"Cefaleia","CLI_FEBRE":"Febre","CLI_VOMITO":"Vômito",
            "CLI_CONVUL":"Convulsões","CLI_RIGIDE":"Rigidez de Nuca",
            "CLI_KERNIG":"Kernig/Brudzinski","CLI_ABAULA":"Abaulamento de Fontanela",
            "CLI_COMA":"Coma","CLI_PETEQU":"Petéquias/Sufusões","CLI_OUTRAS":"Outros Sintomas",
        }
        sint_counts = {}
        for col, label in mapa_sintomas.items():
            if col in df_sub.columns:
                sint_counts[label] = int(
                    (pd.to_numeric(df_sub[col], errors="coerce") == 1).sum()
                )
        sint_series = pd.Series(sint_counts).sort_values(ascending=False)
        sint = top5_com_outros(sint_series, "sintoma")
        # Evolução
        evo_ = (
            df_sub["evolucao_label"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "evolucao", "evolucao_label": "total"})
        )
        fe.to_parquet(  os.path.join(DIR_OUT, f"faixa_etaria_{sufixo}.parquet"), index=False)
        sx.to_parquet(  os.path.join(DIR_OUT, f"sexo_{sufixo}.parquet"),         index=False)
        sint.to_parquet(os.path.join(DIR_OUT, f"sintomas_{sufixo}.parquet"),     index=False)
        evo_.to_parquet(os.path.join(DIR_OUT, f"evolucao_{sufixo}.parquet"),     index=False)

    salvar_perfis(df,                              "todos")
    salvar_perfis(df[df["is_confirmado"] == 1],    "confirmados")
    salvar_perfis(df[df["is_meningococica"] == True], "meningococica")
    salvar_perfis(df[df["is_sorogrupo_b"]  == True],  "sorogrupo_b")

    print("✓ ETL concluído!")

    return {
        "visao_geral":      visao_geral,
        "evolucao_semanal": evolucao_semanal,
        "faixa_etaria":     faixa_df,
        "sexo":             sexo_df,
        "sintomas":         sintomas_df,
        "evolucao":         evolucao_df,
    }


# ── Execução ──────────────────────────────────────────────────────────────────
tabelas = executar_etl(CAMINHO_CSV)

for nome, df_out in tabelas.items():
    print(f"{nome:20s} → {df_out.shape[0]} linhas | {df_out.shape[1]} colunas")
    print(df_out.head(3).to_string(), "\n")
