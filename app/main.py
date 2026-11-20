from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.router import router as ai_router
from app.api.routes import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

# 收敛跨域：默认只放开前端开发服务器，可用 CORS_ORIGINS 环境变量覆盖（逗号分隔）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ai_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}
