from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str = Field(min_length=64)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        le=60,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()