from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dataset_s3_bucket: str = "test-bucket"
    db_host: str = "localhost"
    db_port: int = 3306
    db_username: str = "root"
    db_password: str = ""
    db_name: str = "tubesml"
    secret_key: str = "secret"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
