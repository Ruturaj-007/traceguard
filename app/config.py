from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = ""
    redis_url: str = ""
    api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()