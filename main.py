import argparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.fid.api import router as fid_router
# from app.hdc.api import router as hdc_router

app = FastAPI(title="HDC相关接口后台", version="1.0.0", max_body_size=400 * 1024 * 1024)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "HDC接口后台服务", "status": "healthy"}


app.include_router(fid_router)
# app.include_router(hdc_router)

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="启动 FastAPI 服务")

    parser.add_argument("--port", type=int, default=8000, help="服务运行的端口号 (默认: 8000)")

    args = parser.parse_args()

    print(f"正在启动服务，端口：{args.port}")

    # 4. 运行 uvicorn，使用解析到的端口
    uvicorn.run("main:app", host="0.0.0.0", port=args.port)
