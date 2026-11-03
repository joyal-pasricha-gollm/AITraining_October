from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

class Settings(BaseSettings):
    app_name: str = "ReclaimAI API"
    app_version: str = "1.0.0"
    app_environment: str = "development"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: str
    frontend_url: str = "http://localhost:5173"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    admin_name: str = "ReclaimAI Administrator"
    admin_email: str = "admin@reclaimai.local"
    admin_password: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @property
    def database_url(self) -> URL:
        return URL.create("postgresql+psycopg", username=self.database_user, password=self.database_password,
                          host=self.database_host, port=self.database_port, database=self.database_name)

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
