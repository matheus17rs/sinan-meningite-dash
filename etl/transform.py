from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import DEFAULT_START_YEAR, IBGE_PARA_UF, PROCESSED_DIR, TIPO_MENING

LOGGER = logging.getLogger(__name__)


def normalizar_bruto(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    for col in df.columns:
        if col.startswith("DT_"):
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "DT_SIN_PRI" in df.columns:
        df = df[df["DT_SIN_PRI"].dt.year >= DEFAULT_START_YEAR].copy()

    return df


def calcular_idade_anos(serie: pd.Series) -> pd.Series:
    n = pd.to_numeric(serie, errors="coerce")
    unidade = (n // 1000).astype("Int64")
    valor = (n % 1000).astype(float)

    idade_anos = np.where(
        unidade == 4,
        valor,
        np.where(
            unidade == 3,
            valor / 12,
            np.where(
                unidade == 2,
                valor / 365,
                np.where(unidade == 1, valor / 8760, np.nan),
            ),
        ),
    )
    return pd.Series(idade_anos, index=serie.index)


def faixa_etaria(idade_anos: pd.Series) -> pd.Series:
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, np.inf]
    labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
    return pd.cut(idade_anos, bins=bins, labels=labels, right=False)


def _label_semana_por_data(datas: pd.Series) -> pd.Series:
    iso = datas.dt.isocalendar()
    semanas = pd.Series(index=datas.index, dtype="object")
    mascara_valida = iso.year.notna() & iso.week.notna()
    if mascara_valida.any():
        ano = iso.loc[mascara_valida, "year"].astype(int).astype(str).str.zfill(4)
        semana = iso.loc[mascara_valida, "week"].astype(int).astype(str).str.zfill(2)
        semanas.loc[mascara_valida] = ano + "-SE" + semana
    return semanas


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


def construir_base_enriquecida(df_raw: pd.DataFrame) -> pd.DataFrame:
    df_raw = normalizar_bruto(df_raw)
    LOGGER.info("Base bruta apos filtro temporal: %s linhas", len(df_raw))

    novos = pd.DataFrame(index=df_raw.index)

    def coluna_obrigatoria(nome: str) -> pd.Series:
        if nome not in df_raw.columns:
            raise KeyError(f"Coluna obrigatoria ausente na base bruta: {nome}")
        return df_raw[nome]

    novos["uf_notificacao"] = (
        pd.to_numeric(coluna_obrigatoria("SG_UF_NOT"), errors="coerce")
        .astype("Int64")
        .map(IBGE_PARA_UF)
        .fillna(coluna_obrigatoria("SG_UF_NOT").astype(str))
    )

    novos["is_confirmado"] = (
        pd.to_numeric(coluna_obrigatoria("CLASSI_FIN"), errors="coerce")
        .fillna(0)
        .astype("Int64")
        .eq(1)
        .astype(int)
    )

    diag = pd.to_numeric(coluna_obrigatoria("CON_DIAGES"), errors="coerce")
    sg = pd.to_numeric(coluna_obrigatoria("CLA_SOROGR"), errors="coerce")

    novos["is_meningococica"] = (novos["is_confirmado"] == 1) & diag.isin([1, 2, 3])
    novos["is_sorogrupo_b"] = (novos["is_confirmado"] == 1) & (sg == 2)
    novos["is_outro_tipo"] = (novos["is_confirmado"] == 1) & ~novos["is_meningococica"]
    novos["tipo_mening_label"] = diag.map(TIPO_MENING).fillna("Nao especificado")

    novos["sexo_label"] = (
        coluna_obrigatoria("CS_SEXO")
        .astype(str)
        .str.strip()
        .map({"M": "Masculino", "F": "Feminino", "I": "Ignorado"})
        .fillna("Ignorado")
    )

    novos["idade_anos"] = calcular_idade_anos(coluna_obrigatoria("NU_IDADE_N"))
    novos["faixa_etaria"] = faixa_etaria(novos["idade_anos"])

    sem_raw = coluna_obrigatoria("SEM_PRI").astype(str).str.strip().str.zfill(6)
    novos["sem_label"] = sem_raw.str[:4] + "-SE" + sem_raw.str[4:]
    novos["sem_label"] = novos["sem_label"].where(novos["sem_label"].str.match(r"^\d{4}-SE\d{2}$"), other=None)
    novos["ano_sintomas"] = pd.to_numeric(novos["sem_label"].astype(str).str.extract(r"^(\d{4})-SE\d{2}$")[0], errors="coerce").astype("Int64")
    novos["semana_sintomas"] = pd.to_numeric(novos["sem_label"].astype(str).str.extract(r"SE(\d{2})$")[0], errors="coerce").astype("Int64")
    novos["sem_label_sintomas"] = novos["sem_label"]

    dt_notific = coluna_obrigatoria("DT_NOTIFIC")
    novos["dt_notific_date"] = dt_notific.dt.date
    novos["ano_notificacao"] = dt_notific.dt.year.astype("Int64")
    novos["semana_notificacao"] = dt_notific.dt.isocalendar().week.astype("Int64")
    novos["sem_label_notificacao"] = _label_semana_por_data(dt_notific)

    evo = pd.to_numeric(coluna_obrigatoria("EVOLUCAO"), errors="coerce").fillna(-1)
    novos["evolucao_label"] = np.where(
        evo == 1,
        "Alta",
        np.where(
            evo == 2,
            "Obito por Meningite",
            np.where(evo == 3, "Obito por Outra Causa", "Ignorado"),
        ),
    )

    return pd.concat([df_raw, novos], axis=1).copy()


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


def salvar_perfis(df_sub: pd.DataFrame, sufixo: str) -> dict[str, pd.DataFrame]:
    faixa_ordem = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]

    fe = (
        df_sub["faixa_etaria"]
        .value_counts()
        .reindex(faixa_ordem)
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

    evo = (
        df_sub["evolucao_label"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "evolucao", "evolucao_label": "total"})
    )

    fe.to_parquet(PROCESSED_DIR / f"faixa_etaria_{sufixo}.parquet", index=False)
    sx.to_parquet(PROCESSED_DIR / f"sexo_{sufixo}.parquet", index=False)
    sint.to_parquet(PROCESSED_DIR / f"sintomas_{sufixo}.parquet", index=False)
    evo.to_parquet(PROCESSED_DIR / f"evolucao_{sufixo}.parquet", index=False)

    return {
        "faixa_etaria": fe,
        "sexo": sx,
        "sintomas": sint,
        "evolucao": evo,
    }


def construir_tabelas(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
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

    tabelas = {
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

    tabelas["perfis_todos"] = salvar_perfis(df, "todos")
    tabelas["perfis_confirmados"] = salvar_perfis(df_conf, "confirmados")
    tabelas["perfis_meningococica"] = salvar_perfis(df[df["is_meningococica"] == True], "meningococica")
    tabelas["perfis_sorogrupo_b"] = salvar_perfis(df[df["is_sorogrupo_b"] == True], "sorogrupo_b")

    return tabelas
