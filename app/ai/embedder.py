"""Embedding 客户端：OpenAI 兼容接口。

演示期：硅基流动（https://api.siliconflow.cn/v1，BAAI/bge-m3）
本地化：换 Ollama 等自建服务，只改 EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL
三个环境变量，代码不动。注意：问题向量与文档向量必须出自同一模型，换模型需全量重建索引。
"""
from openai import OpenAI

from app.config import get_settings


def _client() -> OpenAI:
    s = get_settings()
    if not s.EMBEDDING_API_KEY:
        raise RuntimeError("EMBEDDING_API_KEY 未配置（.env 或环境变量），无法调用向量化服务")
    return OpenAI(base_url=s.EMBEDDING_BASE_URL, api_key=s.EMBEDDING_API_KEY)


def embed(texts: list[str]) -> list[list[float]]:
    """批量向量化。切片分批以规避接口单请求条数/长度限制。"""
    if not texts:
        return []
    s = get_settings()
    client = _client()

    vectors: list[list[float]] = []
    batch = 32
    for i in range(0, len(texts), batch):
        resp = client.embeddings.create(model=s.EMBEDDING_MODEL, input=texts[i:i + batch])
        vectors.extend(item.embedding for item in resp.data)
    return vectors


def embed_query(question: str) -> list[float]:
    return embed([question])[0]
