from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "spider-radar"
    environment: str = "test"
    api_prefix: str = "/api"

    database_host: str = Field(
        default="pgm-t4ncw5oi9x3919koro.pg.rds.aliyuncs.com", validation_alias="DATABASE_HOST"
    )
    database_port: int = Field(default=5432, validation_alias="DATABASE_PORT")
    database_user: str = Field(default="tactile_app", validation_alias="DATABASE_USER")
    database_password: str = Field(default="", validation_alias="DATABASE_PASSWORD")
    database_name: str = Field(default="tactile", validation_alias="DATABASE_NAME")
    database_schema: str = "spider_radar"

    jwt_secret: str = "spider-radar-test-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    admin_email: str = "admin@spreadx.ai"
    admin_password: str = "SpiderRadar@Admin2026"

    qa_email: str = "qa-test@spreadx.ai"
    qa_password: str = "SpiderRadar@Test2026"

    cors_origins: str = "*"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
