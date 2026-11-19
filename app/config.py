from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 服务
    APP_NAME: str = "hamifs-convert"
    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # 任务限制（对齐技术方案：单任务超时 120s，上传 <=100MB）
    TASK_TIMEOUT_SECONDS: int = 120
    MAX_UPLOAD_MB: int = 100
    MAX_CONCURRENCY: int = 4

    # 存储后端：local（开发期默认） | s3（MinIO / 云 OSS）
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./data"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "hamifs-convert"
    PRESIGN_EXPIRES_SECONDS: int = 3600

    # Celery（可选：不配置则用进程内后台线程执行）
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # ── AI / RAG ─────────────────────────────────────────────
    # LLM（OpenAI 兼容）：演示期 DeepSeek；自建换 vLLM/Ollama 只改这三个
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.3
    # Embedding（OpenAI 兼容）：演示期硅基流动 bge-m3；本地化换 Ollama 同样三个变量
    # ⚠️ DeepSeek 无 embedding 接口，embedding 必须另配；问题与文档必须同模型，换模型需全量重建
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    # 向量库：Chroma 本地持久化目录（换 Milvus 只改 vectorstore.py 实现）
    CHROMA_DIR: str = "./data/chroma"
    # 切块参数（RAG 效果核心，真实语料上迭代调优）
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
