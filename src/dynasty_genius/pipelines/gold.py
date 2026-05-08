"""Apply Gold-layer SQL resources for Databricks Asset Bundle jobs."""

from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession


def _split_sql(sql_text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []

    trailing = "\n".join(current).strip()
    if trailing:
        statements.append(trailing)

    return statements


def apply_sql_files(spark: SparkSession, sql_files: list[str]) -> None:
    for sql_file in sql_files:
        sql_path = Path(sql_file)
        sql_text = sql_path.read_text()
        for statement in _split_sql(sql_text):
            spark.sql(statement)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-file", action="append", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    apply_sql_files(SparkSession.builder.getOrCreate(), args.sql_file)
