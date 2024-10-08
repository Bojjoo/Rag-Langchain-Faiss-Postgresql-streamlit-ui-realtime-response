from api.routes import *


@router.get("/")
def read_root():
    return {
        'Hello This is Rag Langchain application on FastAPI !!!'
    }


@router.post("/get_retriever/")
def get_retriever(user_id: UserID):
    user_vectorstore = VectorStore(user_id.user_id)
    user_db = user_vectorstore.user_db
    user_retriever = user_vectorstore.user_retriever
    retriever_cache[f'{user_id.user_id}'] = user_retriever
    vectorstore_cache[f'{user_id.user_id}'] = user_db
    if user_db is not None:
        return {"OK"}
    else:
        return {"None"}


@router.post('/upload_data')
async def upload_file(file: UploadFile = File(...), user_id: str = Form(...)):
    vectorstore = VectorStore(user_id)
    chunks = vectorstore.upload_file(file, user_id)

    new_vectorstore = VectorStore(user_id)

    user_db = new_vectorstore.user_db
    user_retriever = new_vectorstore.user_retriever

    retriever_cache[f'{user_id}'] = user_retriever
    vectorstore_cache[f'{user_id}'] = user_db
    return chunks


@router.post('/get_answer/')
async def get_response(question_request: QuestionRequest):
    system_retriever = VectorStore(question_request.user_id).system_retriever
    prompt = bot.question_handler(system_retriever, question_request)
    generator = bot.send_message(prompt)
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post('/get_answer_about_users_data/')
async def get_response(question_request: QuestionRequest):
    try:
        user_retriever = retriever_cache[f'{question_request.user_id}']
        prompt = bot.question_handler(user_retriever, question_request)
        generator = bot.send_message(prompt)
        return StreamingResponse(generator, media_type="text/event-stream")
    except:
        return {"Error"}


@router.delete("/delete_file/")
def delete_file(file: FileDelete):
    user_id = file.user_id
    file_name = file.file_name
    vectorstore = VectorStore(user_id)
    try:
        vectorstore.delete_from_vectorstore(file_name, user_id)
        return 1
    except:
        return 0
    

