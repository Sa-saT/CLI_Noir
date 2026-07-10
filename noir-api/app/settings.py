"""アプリ設定（pydantic-settings で .env を読み込む）。

設計指示書 § 認証 / § 2 技術スタックに対応。
機密値（SECRET_KEY 等）は .env に置き、リポジトリにはコミットしない。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- アプリ ---
    app_name: str = "CLI_Noir API"
    debug: bool = False

    # --- DB ---
    # 開発デフォルトは SQLite。本番は .env で上書きする。
    database_url: str = "sqlite:///./noir.db"

    # --- 認証（設計指示書 § 認証: access 30分 / refresh 7日） ---
    secret_key: str = "change-me-in-dotenv"  # 本番は必ず .env で上書き
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- CORS（フロント noir-client の開発サーバー） ---
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
