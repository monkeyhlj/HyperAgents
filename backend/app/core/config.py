import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "HyperAgents API"
    app_version: str = "0.1.0"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents",
    )


settings = Settings()
