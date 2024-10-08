from api.services.chatbot import ChatBot
from api.services.vectorstore_faiss import VectorStore
from fastapi import UploadFile, File, Form, APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

bot = ChatBot()
router = APIRouter()
retriever_cache = {}
vectorstore_cache = {}


class QuestionRequest(BaseModel):
    question: str
    conversation_id: str
    user_id: str


class UserID(BaseModel):
    user_id: str


class FileDelete(BaseModel):
    file_name: str
    user_id: str
