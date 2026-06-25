"""
banco.py
────────
Engine DuckDB sobre o Parquet local de Recife (recife_tb_geolink.parquet).

Estratégia (validada no dashboard nacional):
  - SELECT só das colunas usadas (não SELECT *) — menos dados lidos.
  - SET threads = nº de CPUs para leitura colunar paralela.
  - Cada chamada abre conexão própria (thread-safe). O cache fica no nível
    do resultado (DataFrame), via @st.cache_data em dados.py.

O SQL do chamador referencia a tabela como 'tb' — injetada como CTE com
apenas COLUNAS_DASHBOARD.
"""

import os

import duckdb
import pandas as pd

from src.constantes import PARQUET, GEOLINK_PARQUET, COLUNAS_DASHBOARD, COLUNAS_GEO


def _threads() -> int:
    return min(os.cpu_count() or 2, 8)


def _parquet_posix() -> str:
    return PARQUET.as_posix()


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    """SQL sobre o SINAN completo de Recife (tabela = 'tb'). Base dos INDICADORES."""
    cols = ", ".join(f'"{c}"' for c in COLUNAS_DASHBOARD)
    wrapped = f"""
        WITH tb AS (
            SELECT {cols} FROM read_parquet('{_parquet_posix()}')
        )
        {sql}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_threads()}")
        return con.execute(wrapped, params or []).df()


def query_geo(sql: str, params: list | None = None) -> pd.DataFrame:
    """SQL sobre a base geocodificada geolink (tabela = 'tb'). Base do MAPA."""
    cols = ", ".join(f'"{c}"' for c in COLUNAS_GEO)
    wrapped = f"""
        WITH tb AS (
            SELECT {cols} FROM read_parquet('{GEOLINK_PARQUET.as_posix()}')
        )
        {sql}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_threads()}")
        return con.execute(wrapped, params or []).df()


def query_all_cols(sql: str, params: list | None = None) -> pd.DataFrame:
    """Igual a query() mas com SELECT * — usado pela Análise Livre (PyGWalker)."""
    wrapped = f"""
        WITH tb AS (
            SELECT * FROM read_parquet('{_parquet_posix()}')
        )
        {sql}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_threads()}")
        return con.execute(wrapped, params or []).df()


def anos_no_banco() -> list[int]:
    """Anos presentes no Parquet, do mais recente ao mais antigo."""
    df = query("SELECT DISTINCT nu_ano FROM tb WHERE nu_ano IS NOT NULL ORDER BY nu_ano DESC")
    return [int(a) for a in df["nu_ano"].tolist()]
