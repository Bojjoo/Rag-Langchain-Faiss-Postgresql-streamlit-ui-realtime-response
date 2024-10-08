from api.config import *
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from flashrank import Ranker
from langchain.retrievers import ContextualCompressionRetriever
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from langchain.callbacks import AsyncIteratorCallbackHandler

import asyncio
from typing import AsyncIterable

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.vectorstores import FAISS
import os
from fastapi import UploadFile, File, Form
import shutil
from api.database.database import SQLDatabase


load_dotenv(find_dotenv())


model_embedding = OpenAIEmbeddings(model=MODEL_EMBEDDING)
sql_conn = SQLDatabase()


class QuestionRequest(BaseModel):
    question: str
    conversation_id: str



