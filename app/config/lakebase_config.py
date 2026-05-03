from __future__ import annotations

import os
from dataclasses import dataclass


LAKEBASE_HOST_ENV = "DATABRICKS_LAKEBASE_HOST"
LAKEBASE_PORT_ENV = "DATABRICKS_LAKEBASE_PORT"
LAKEBASE_DATABASE_ENV = "DATABRICKS_LAKEBASE_DATABASE"
LAKEBASE_USER_ENV = "DATABRICKS_LAKEBASE_USER"
LAKEBASE_PASSWORD_ENV = "DATABRICKS_LAKEBASE_PASSWORD"
LAKEBASE_SSLMODE_ENV = "DATABRICKS_LAKEBASE_SSLMODE"


@dataclass(frozen=True)
class LakebaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    sslmode: str = "require"

    @property
    def safe_dsn(self) -> str:
        return (
            f"postgresql://{self.user}:***@{self.host}:{self.port}/"
            f"{self.database}?sslmode={self.sslmode}"
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required Lakebase environment variable: {name}")
    return value


def get_lakebase_config() -> LakebaseConfig:
    return LakebaseConfig(
        host=_required_env(LAKEBASE_HOST_ENV),
        port=int(os.getenv(LAKEBASE_PORT_ENV, "5432")),
        database=_required_env(LAKEBASE_DATABASE_ENV),
        user=_required_env(LAKEBASE_USER_ENV),
        password=_required_env(LAKEBASE_PASSWORD_ENV),
        sslmode=os.getenv(LAKEBASE_SSLMODE_ENV, "require"),
    )
