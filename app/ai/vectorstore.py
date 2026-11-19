"""向量库封装：Chroma（本地持久化，零外部依赖）。

- 单 collection `hamifs_docs`，cosine 相似度
- 每条记录：id={documentId}_{chunkIndex}，document=切块原文，metadata={documentId, documentName, chunkIndex}
- chromadb 延迟导入：未安装时服务其余功能不受影响，AI 接口返回明确错误
- 换 Milvus（进阶阶段）只需替换本文件的实现，其余模块不动
"""
import threading
from pathlib import Path

from app.config import get_settings

COLLECTION_NAME = "hamifs_docs"

_lock = threading.Lock()
_collection = None  # 进程内单例


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:
            try:
                import chromadb
            except ImportError as e:
                raise RuntimeError("chromadb 未安装：请在虚拟环境执行 pip install chromadb") from e
            s = get_settings()
            Path(s.CHROMA_DIR).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=s.CHROMA_DIR)
            _collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
    return _collection


def add_chunks(document_id: int, document_name: str, chunks: list[str], vectors: list[list[float]]) -> int:
    col = _get_collection()
    ids = [f"{document_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"documentId": document_id, "documentName": document_name, "chunkIndex": i}
        for i in range(len(chunks))
    ]
    col.upsert(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
    return len(chunks)


def query(vector: list[float], top_k: int) -> list[dict]:
    """返回 [{text, documentId, documentName, chunkIndex, distance}]，按相似度升序（距离小=更相关）。"""
    col = _get_collection()
    res = col.query(query_embeddings=[vector], n_results=top_k, include=["documents", "metadatas", "distances"])
    hits: list[dict] = []
    if not res["ids"] or not res["ids"][0]:
        return hits
    for i, rid in enumerate(res["ids"][0]):
        meta = res["metadatas"][0][i] or {}
        hits.append({
            "id": rid,
            "text": res["documents"][0][i],
            "documentId": meta.get("documentId"),
            "documentName": meta.get("documentName", ""),
            "chunkIndex": meta.get("chunkIndex", 0),
            "distance": res["distances"][0][i],
        })
    return hits


def delete_document(document_id: int) -> int:
    """删除指定文档的全部向量（文档删除时必须联动，避免引用失效）。"""
    col = _get_collection()
    before = col.count()
    col.delete(where={"documentId": document_id})
    return before - col.count()


def count() -> tuple[int, int]:
    """返回 (总块数, 文档数)。"""
    col = _get_collection()
    total = col.count()
    docs: set = set()
    if total:
        res = col.get(include=["metadatas"])
        for meta in res["metadatas"] or []:
            if meta and meta.get("documentId") is not None:
                docs.add(meta["documentId"])
    return total, len(docs)
