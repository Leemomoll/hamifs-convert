"""AI 模块的请求/响应模型。"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """提问请求。Java 网关转发；历史上下文由 Java 拼进 question 或后续扩展 messages 字段。"""
    question: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20, description="检索条数，缺省用配置 TOP_K")


class Citation(BaseModel):
    """引用出处：前端点击可精确跳转到文档预览。"""
    documentId: int
    documentName: str
    chunkIndex: int
    snippet: str = Field(description="命中的切块原文（可截断展示）")
    score: float = Field(description="相似度得分（距离越小越相关，展示时取 1-distance）")


class IndexResult(BaseModel):
    """向量化结果。"""
    documentId: int
    fileName: str
    chunks: int = Field(description="本次入库的切块数")
    message: str = "ok"


class DeleteResult(BaseModel):
    documentId: int
    deleted: int = Field(description="删除的向量条数")


class IndexStatus(BaseModel):
    embeddingModel: str
    collection: str
    chunks: int = Field(description="向量库当前总块数")
    documents: int = Field(description="已向量化文档数（按 documentId 去重）")
    llmConfigured: bool = Field(description="LLM key 是否已配置")
    embeddingConfigured: bool = Field(description="Embedding key 是否已配置")
