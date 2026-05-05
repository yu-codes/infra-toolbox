"""
應用程式設定模組

透過 pydantic-settings 從環境變數讀取設定。
環境變數名稱自動對應欄位名稱（不分大小寫），例如：
  GEOSERVER_URL → geoserver_url
  SHARED_DIR    → shared_dir
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    geoserver_url: str = "http://localhost:8080/geoserver"
    geoserver_username: str = "admin"
    geoserver_password: str = "geoserver"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
