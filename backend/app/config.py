from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure Communication Services
    acs_connection_string: str

    # Azure AI Services — Voice Live API (multi-service AIServices resource)
    cognitive_services_endpoint: str
    voice_live_model: str = "gpt-4o-mini"

    # Azure OpenAI — ticket classification after call ends
    azure_openai_endpoint: str
    azure_openai_chat_deployment: str = "gpt-4o-mini"

    # App
    callback_host: str  # public URL (Dev Tunnel or deployed hostname), no trailing slash
    log_level: str = "INFO"


settings = Settings()
