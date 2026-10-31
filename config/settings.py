import os
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    SettingsConfigDict = None

    class BaseSettings:
        def __init__(self, **kwargs):
            annotations = getattr(self.__class__, "__annotations__", {})
            for name, typ in annotations.items():
                default = getattr(self.__class__, name, None)
                raw = os.getenv(name, kwargs.get(name, default))
                if typ is bool:
                    value = str(raw).lower() in {"1", "true", "yes", "on"}
                elif typ is int:
                    value = int(raw)
                elif typ is float:
                    value = float(raw)
                else:
                    value = raw
                setattr(self, name, value)

class Settings(BaseSettings):
    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App Config
    APP_NAME: str = "AgentGraph Sentinel"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    DEBUG: bool = True
    
    # LLM Config (OpenRouter / OpenAI / Anthropic)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "minimax/minimax-m2.1" # Default cheap model
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Fallback Keys
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: str = ""
    
    # Detection Thresholds
    GRAPH_ANOMALY_THRESHOLD: float = 0.3
    NODE_RISK_THRESHOLD: float = 0.7
    
    # Paths
    LOG_DIR: str = "logs"
    DATA_DIR: str = "data"

@lru_cache()
def get_settings():
    return Settings()
