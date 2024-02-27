from functools import lru_cache
from dotenv import find_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "My Finance API"
    database_url: str

    model_config = SettingsConfigDict(env_file=find_dotenv(".env"))


@lru_cache
def get_settings():
    return Settings()