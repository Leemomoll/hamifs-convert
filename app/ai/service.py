"""AI 服务编排：入库流水线 + 检索问答。

入库：extract -> chunk -> embed -> chroma
问答：embed_query -> chroma 检索 -> 拼 prompt -> LLM 流式生成
"""
import json
from collections.abc import AsyncIterator

from app.ai import chunker, embedder, extractor, llm, vectorstore
from app.ai.schemas import ChatRequest, Citation
from app.config import get_settings


def index_document(document_id: int, file_name: str, data: bytes) -> dict:
    """文档入库（Java 在上传成功后调用）。返回入库块数。"""
    text = extractor.extract_text(data, file_name).strip()
    if not text:
        # 扫描版 PDF 等无文本层的情况：明确告知，二期接 OCR
        return {"chunks": 0, "message": "未提取到文本（可能是扫描件，需 OCR 支持），已跳过向量化"}

    chunks = chunker.chunk_text(text)
    if not chunks:
        return {"chunks": 0, "message": "文本过短，无法有效切块"}

    vectors = embedder.embed(chunks)
    n = vectorstore.add_chunks(document_id, file_name, chunks, vectors)
    return {"chunks": n, "message": "ok"}


def delete_document(document_id: int) -> int:
    return vectorstore.delete_document(document_id)


def index_status() -> dict:
    s = get_settings()
    chunks, docs = vectorstore.count()
    return {
        "embeddingModel": s.EMBEDDING_MODEL,
        "collection": vectorstore.COLLECTION_NAME,
        "chunks": chunks,
        "documents": docs,
        "llmConfigured": bool(s.LLM_API_KEY),
        "embeddingConfigured": bool(s.EMBEDDING_API_KEY),
    }


async def chat_stream(req: ChatRequest) -> AsyncIterator[str]:
    """SSE 事件流：delta(文本增量)* -> citations -> done。

    事件格式（每行 data: <json>\\n\\n）：
      {"type":"delta","content":"..."}        文本增量，前端追加渲染
      {"type":"citations","items":[...]}      引用出处（回答前发出，前端可先渲染卡片）
      {"type":"done"}                          结束
      {"type":"error","message":"..."}         失败（key 未配/模型报错等）
    """
    s = get_settings()

    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        top_k = req.top_k or s.TOP_K
        hits = vectorstore.query(embedder.embed_query(req.question), top_k)
        citations = [
            Citation(
                documentId=h["documentId"] or 0,
                documentName=h["documentName"],
                chunkIndex=h["chunkIndex"],
                snippet=h["text"][:200],
                score=round(1.0 - h["distance"], 4),
            )
            for h in hits
        ]
        yield _sse({"type": "citations", "items": [c.model_dump() for c in citations]})

        contexts = [{"documentName": h["documentName"], "text": h["text"]} for h in hits]
        messages = llm.build_context_prompt(req.question, contexts)
        async for delta in llm.stream_chat(messages):
            yield _sse({"type": "delta", "content": delta})
        yield _sse({"type": "done"})
    except Exception as e:  # noqa: BLE001 —— 统一转 SSE error 事件，避免流式连接直接断掉
        yield _sse({"type": "error", "message": str(e)})
