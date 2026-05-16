"""
Carbono em Pé — Configurações centrais
Todas as variáveis sensíveis vêm do ambiente, nunca hardcoded.
"""
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List
import secrets


class Settings(BaseSettings):
    # Aplicação
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = secrets.token_urlsafe(32)
    APP_ALLOWED_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    @field_validator("APP_ENV")
    @classmethod
    def validar_ambiente(cls, v):
        assert v in ("development", "staging", "production"), \
            "APP_ENV deve ser development, staging ou production"
        return v

    @property
    def origens_permitidas(self) -> List[str]:
        return [o.strip() for o in self.APP_ALLOWED_ORIGINS.split(",")]

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "carbono-em-pe-relatorios"

    # JWT — tokens de curta duração por segurança
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_PIX_ENABLED: bool = False  # Requer ativação explícita da conta no dashboard Stripe

    # Google Earth Engine
    GEE_SERVICE_ACCOUNT: str
    GEE_KEY_FILE: str
    GEE_PROJECT_ID: str

    # NFE.io
    NFEIO_API_KEY: str
    NFEIO_COMPANY_ID: str

    # E-mail
    RESEND_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        return self.APP_ENV == "development"


# Instância única — importar de qualquer módulo
settings = Settings()
