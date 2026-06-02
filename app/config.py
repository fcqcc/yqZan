from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///couple_v2.db"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72
    ADMIN_PASSWORD: str = "admin123"

    # 微信小程序配置
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    # 开发模式：为 true 时跳过微信 API 校验，用 code 的 hash 替代 openid
    # 已配置真实 AppID/Secret，通过 .env 文件设为 false
    WECHAT_MOCK_ENABLED: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
