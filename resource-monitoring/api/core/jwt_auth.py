"""
JWT 認證模組

處理 JWT 密鑰管理、令牌生成和驗證
- 當 JWT_ENABLED=true 時，自動生成或載入密鑰
- 當 JWT_ENABLED=false 時，跳過所有 JWT 相關操作
"""

import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import jwt
from fastapi import HTTPException, Request

from core.config import settings


class JWTManager:
    """JWT 管理器"""

    def __init__(self):
        self._secret_key: Optional[str] = None
        self._initialized: bool = False

    @property
    def is_enabled(self) -> bool:
        """檢查 JWT 是否啟用"""
        return settings.JWT_ENABLED

    @property
    def secret_key(self) -> Optional[str]:
        """取得 JWT 密鑰（僅在 JWT 啟用時有效）"""
        if not self.is_enabled:
            return None
        if not self._initialized:
            self._initialize()
        return self._secret_key

    def _initialize(self) -> None:
        """初始化 JWT 密鑰"""
        if self._initialized:
            return

        if not self.is_enabled:
            print("[JWT] JWT is disabled - skipping secret key initialization")
            self._initialized = True
            return

        # 優先使用環境變數中的密鑰
        import os

        env_secret = os.getenv("JWT_SECRET_KEY")
        if env_secret and env_secret.strip():
            self._secret_key = env_secret.strip()
            print("[JWT] Using JWT_SECRET_KEY from environment")
        else:
            # 嘗試從檔案載入
            secret_file = settings.JWT_SECRET_FILE
            if secret_file.exists():
                self._secret_key = secret_file.read_text().strip()
                print(f"[JWT] Loaded JWT_SECRET_KEY from {secret_file}")
            else:
                # 自動生成新密鑰
                self._secret_key = secrets.token_urlsafe(32)
                self._save_secret_to_file()
                print(f"[JWT] Generated new JWT_SECRET_KEY and saved to {secret_file}")

        # 儲存令牌資訊
        self._save_token_info()
        self._initialized = True

    def _save_secret_to_file(self) -> None:
        """儲存密鑰到檔案"""
        try:
            secret_file = settings.JWT_SECRET_FILE
            secret_file.parent.mkdir(parents=True, exist_ok=True)
            secret_file.write_text(self._secret_key)
            secret_file.chmod(0o600)
        except Exception as e:
            print(f"[JWT] Warning: Could not save JWT_SECRET_KEY to file: {e}")

    def _save_token_info(self) -> None:
        """儲存令牌資訊供用戶參考"""
        if not self._secret_key:
            return

        token = self.generate_token("sample-client")
        now = datetime.utcnow()
        expires_at = now + timedelta(days=365 * settings.JWT_EXPIRATION_YEARS)

        info = {
            "generated_at": now.isoformat(),
            "jwt_enabled": True,
            "algorithm": settings.JWT_ALGORITHM,
            "expiration_years": settings.JWT_EXPIRATION_YEARS,
            "expires_at": expires_at.isoformat(),
            "sample_token": token,
            "usage": {
                "curl": f'curl -H "Authorization: Bearer {token}" http://localhost:10003/system-metrics',
                "python": f"headers = {{'Authorization': 'Bearer {token}'}}",
                "javascript": f"headers: {{'Authorization': `Bearer {token}`}}",
            },
        }

        try:
            info_file = settings.JWT_TOKEN_INFO_FILE
            info_file.parent.mkdir(parents=True, exist_ok=True)
            info_file.write_text(json.dumps(info, indent=2))
            print(f"[JWT] Token info saved to {info_file}")
        except Exception as e:
            print(f"[JWT] Warning: Could not save token info: {e}")

    def generate_token(self, subject: str = "client") -> str:
        """生成 JWT 令牌"""
        if not self.is_enabled:
            raise ValueError("JWT is disabled")

        now = datetime.utcnow()
        expires_at = now + timedelta(days=365 * settings.JWT_EXPIRATION_YEARS)

        payload = {
            "sub": subject,
            "iat": now,
            "exp": expires_at,
        }
        return jwt.encode(payload, self._secret_key, algorithm=settings.JWT_ALGORITHM)

    def verify_token(self, token: str) -> dict:
        """驗證 JWT 令牌"""
        if not self.is_enabled:
            raise ValueError("JWT is disabled")

        try:
            payload = jwt.decode(
                token, self._secret_key, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            raise HTTPException(
                status_code=401, detail=f"Authentication failed: {str(e)}"
            )


# 單例 JWT 管理器
jwt_manager = JWTManager()


async def verify_jwt_token(request: Request) -> dict:
    """
    FastAPI 依賴項：驗證 JWT Token

    如果 JWT_ENABLED=false，跳過驗證直接返回
    如果 JWT_ENABLED=true，驗證 Authorization header 中的 Bearer token

    Args:
        request: FastAPI Request 對象

    Returns:
        解碼後的 JWT payload 或 unauthenticated 標記

    Raises:
        HTTPException: 如果 token 無效
    """
    # 如果 JWT 認證被禁用，跳過驗證
    if not jwt_manager.is_enabled:
        return {"sub": "unauthenticated", "jwt_enabled": False}

    # 從 Authorization header 獲取令牌
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.replace("Bearer ", "", 1)
    return jwt_manager.verify_token(token)


def initialize_jwt() -> None:
    """初始化 JWT 模組（在應用程式啟動時呼叫）"""
    if jwt_manager.is_enabled:
        # 觸發初始化
        _ = jwt_manager.secret_key
        print("[JWT] JWT initialization complete")
    else:
        print(
            "[JWT] JWT is disabled - all endpoints are accessible without authentication"
        )
