"""/ai 路由：对齐《AI 智能问答接口文档》（Java 网关转发，前端不直连）。"""
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.ai import service
from app.ai.schemas import ChatRequest, DeleteResult, IndexResult, IndexStatus

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", summary="提问（SSE 流式返回回答 + 引用出处）")
async def chat(req: ChatRequest):
    return StreamingResponse(
        service.chat_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/index/{document_id}", summary="文档向量化入库（Java 上传成功后调用）", response_model=IndexResult)
async def index_document(document_id: int, file: UploadFile = File(...)):
    data = await file.read()
    try:
        result = service.index_document(document_id, file.filename or "unnamed", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        # key 未配置 / chromadb 未安装等环境问题
        raise HTTPException(status_code=503, detail=str(e)) from e
    return IndexResult(documentId=document_id, fileName=file.filename or "unnamed", **result)


@router.delete("/index/{document_id}", summary="删除指定文档的全部向量（文档删除时联动）", response_model=DeleteResult)
async def delete_index(document_id: int):
    try:
        deleted = service.delete_document(document_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return DeleteResult(documentId=document_id, deleted=deleted)


@router.get("/index/status", summary="索引进度：已入库块数/文档数、key 配置状态", response_model=IndexStatus)
async def index_status():
    return service.index_status()


@router.post("/index/rebuild", summary="全量重建索引（需 Java 逐文档重新提交，见接口文档）")
async def rebuild():
    raise HTTPException(
        status_code=501,
        detail="重建索引由 Java 端编排：查出全部文档后逐个调 POST /ai/index/{id} 覆盖写入；本服务不做全量缓存",
    )


@router.get("/health", summary="AI 模块健康检查")
async def ai_health():
    try:
        status = service.index_status()
        return {"status": "ok", "indexedChunks": status["chunks"], "indexedDocuments": status["documents"]}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "reason": str(e)}
