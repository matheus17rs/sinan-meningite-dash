from __future__ import annotations

import logging

from .extract import obter_base_bruta
from .transform import construir_base_enriquecida, construir_tabelas
from .load import salvar_tabelas
from .config import DEFAULT_END_YEAR, DEFAULT_START_YEAR

LOGGER = logging.getLogger(__name__)


def configurar_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def resolver_anos() -> list[int]:
    start_year = max(2000, DEFAULT_START_YEAR)
    end_year = max(start_year, DEFAULT_END_YEAR)
    return list(range(start_year, end_year + 1))


def executar_etl() -> dict[str, object]:
    anos = resolver_anos()
    LOGGER.info("Anos alvo: %s", anos)

    df_raw, metadata = obter_base_bruta(anos)
    LOGGER.info("Bruto carregado: %s linhas | %s colunas", len(df_raw), len(df_raw.columns))

    df = construir_base_enriquecida(df_raw)
    LOGGER.info("Base enriquecida: %s linhas | %s colunas", len(df), len(df.columns))

    tabelas = construir_tabelas(df)
    tabelas["base_enriquecida"] = df
    metadata["rows_raw"] = int(len(df_raw))
    metadata["rows_processed"] = int(len(df))
    metadata["columns_raw"] = int(len(df_raw.columns))
    metadata["columns_processed"] = int(len(df.columns))
    metadata["temporal_profiles"] = {
        "sintomas": {
            "date_column": "DT_SIN_PRI",
            "week_label_column": "sem_label",
        },
        "notificacao": {
            "date_column": "DT_NOTIFIC",
            "week_label_column": "sem_label_notificacao",
        },
    }
    salvar_tabelas(tabelas, metadata)

    LOGGER.info("ETL concluido com sucesso.")
    return tabelas


def main() -> None:
    configurar_logging()
    tabelas = executar_etl()

    for nome, df_out in tabelas.items():
        if isinstance(df_out, dict):
            continue
        LOGGER.info("%-20s -> %s linhas | %s colunas", nome, df_out.shape[0], df_out.shape[1])
