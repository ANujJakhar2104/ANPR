from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Storage
    DATABASE_URL: str = "sqlite:///./data/anpr.db"
    UPLOAD_DIR: str = "./data/uploads"
    OUTPUT_DIR: str = "./data/outputs"

    # ANPR models - point these at your existing weight files
    COCO_MODEL_PATH: str = "./models/yolov8n.pt"
    PLATE_MODEL_PATH: str = "./models/license_plate_detector.pt"
    OCR_USE_GPU: bool = False

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"


settings = Settings()
