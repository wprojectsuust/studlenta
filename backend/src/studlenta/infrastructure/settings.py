from datetime import timedelta
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация из переменных окружения (префикс ``STUDLENTA_``) или ``.env``."""

    model_config = SettingsConfigDict(env_prefix="STUDLENTA_", env_file=".env", extra="ignore")

    database_url: str = "postgresql://studlenta:studlenta@localhost:5432/studlenta"
    jwt_secret: SecretStr = Field(min_length=32)
    access_ttl_minutes: int = 15
    timezone: str = "Asia/Yekaterinburg"
    # Префикс, под которым сервис опубликован за reverse proxy (прод: "/studlenta").
    # nginx его срезает, но ссылки, cookie и Swagger должны его учитывать.
    root_path: str = ""
    media_root: Path = Path("media")
    media_url: str = "/media"
    # Через запятую: STUDLENTA_CORS_ORIGINS=http://localhost:5173,https://studlenta.example
    # Публичный адрес фронтенда: из него строится ссылка подтверждения почты.
    public_url: str = "http://localhost:3000/studlenta"
    # Почта (ADR-0012). Без smtp_host письма пишутся в лог; mail_outbox_dir — для e2e.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = True
    mail_from: str = "studlenta@karrad.tech"
    mail_from_name: str = "Студлента УУНиТ"
    mail_outbox_dir: Path | None = None
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    secure_cookies: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value

    @field_validator("root_path")
    @classmethod
    def _normalize_root(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        return f"/{value.lstrip('/')}" if value else ""

    @property
    def public_media_url(self) -> str:
        return f"{self.root_path}{self.media_url.rstrip('/')}"

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def access_ttl(self) -> timedelta:
        return timedelta(minutes=self.access_ttl_minutes)
