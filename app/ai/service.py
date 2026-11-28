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


def search(query: str, top_k: int = 6) -> list[dict]:
    """语义搜索：向量检索，返回命中块（不调 LLM，纯检索）。"""
    text = query.strip()
    if not text:
        return []
    hits = vectorstore.query(embedder.embed_query(text), top_k)
    return [
        {
            "documentId": h["documentId"],
            "documentName": h["documentName"],
            "chunkIndex": h["chunkIndex"],
            "snippet": h["text"][:200],
            "score": round(1.0 - h["distance"], 4),
        }
        for h in hits
    ]


_TAG_PROMPT = (
    "你是文档标签生成器。根据下面的文档片段，提炼 3~5 个最能概括主题的简短标签。"
    "要求：每个标签不超过 10 个字，中文优先；只输出 JSON 数组，不要任何解释，"
    '形如 ["标签1","标签2"]。\n\n文档片段：\n{content}'
)


def _parse_tags(raw: str) -> list[str]:
    """容忍 LLM 输出的代码围栏 / 前后杂文，提取 JSON 数组。"""
    import json
    import re

    text = (raw or "").strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        text = match.group(0)
    tags = json.loads(text)
    result: list[str] = []
    for t in tags if isinstance(tags, list) else []:
        if isinstance(t, str) and t.strip():
            result.append(t.strip()[:20])
    # 去重保序，最多 5 个
    seen: set[str] = set()
    unique = [t for t in result if not (t in seen or seen.add(t))]
    return unique[:5]


async def suggest_tags(document_id: int, file_name: str, data: bytes, max_tags: int = 5) -> dict:
    """上传自动打标签：提取文本 -> LLM 生成标签。失败抛异常，由调用方兜底。"""
    text = extractor.extract_text(data, file_name).strip()
    if not text:
        return {"documentId": document_id, "fileName": file_name, "tags": [],
                "message": "未提取到文本，无法生成标签"}
    messages = [
        {"role": "system", "content": "你只输出 JSON 数组，不输出任何其他内容。"},
        {"role": "user", "content": _TAG_PROMPT.format(content=text[:6000])},
    ]
    raw = await llm.chat_once(messages)
    return {
        "documentId": document_id,
        "fileName": file_name,
        "tags": _parse_tags(raw),
        "message": "ok",
    }


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
