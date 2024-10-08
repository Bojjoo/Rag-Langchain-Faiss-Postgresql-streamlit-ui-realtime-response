from fastapi import FastAPI
from api.routes.routes import router
import uvicorn


app = FastAPI(
    title="RAG_APP",
    description="Hello! This is Rag Langchain application on FastAPI!!!"
)

# Include tất cả các endpoint từ router
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
