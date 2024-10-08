from api.services import *


class VectorStore:
    def __init__(self, user_id=None):
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
                                                            length_function=len)
        self.model_embedding = model_embedding
        self.system_db = FAISS.load_local(SYSTEM_DATABASE, self.model_embedding,
                                          allow_dangerous_deserialization=True)
        self.system_retriever = self.system_db.as_retriever(search_kwargs=SEARCH_KWARGS, search_type=SEARCH_TYPE)

        try:
            self.user_db = FAISS.load_local(f'{USER_DATABASE}/{user_id}', self.model_embedding,
                                            allow_dangerous_deserialization=True)
            self.user_retriever = self.user_db.as_retriever(search_kwargs=SEARCH_KWARGS, search_type=SEARCH_TYPE)

        except:
            self.user_db = None
            self.user_retriever = None

    # For user
    # lấy ra db và retriever của conversation_id
    def check_user_db(self, user_id):
        db_user = FAISS.load_local(f'{USER_DATABASE}/{user_id}', self.model_embedding,
                                   allow_dangerous_deserialization=True)
        retriever_user = db_user.as_retriever(search_kwargs=SEARCH_KWARGS, search_type=SEARCH_TYPE)
        return db_user, retriever_user

    # Lấy ra retriever cho từng user mỗi khi hỏi câu hỏi đầu tiên và lưu vào trong cache

    def split_document(self, pdf_file):
        pdf_reader = PyPDFLoader(pdf_file)
        documents = pdf_reader.load()
        chunks = self.text_splitter.split_documents(documents)
        return chunks

    # Lưu vào vectorstore
    def create_vectorstore(self, chunks):
        db = FAISS.from_documents(chunks, self.model_embedding)
        # db.save_local(USER_DATABASE)
        return db

    # thêm vào vectorstore
    def merge_to_vectorstore(self, old_db, new_db, user_id):
        old_db.merge_from(new_db)
        old_db.save_local(f'{USER_DATABASE}/{user_id}')
        return old_db

    # xóa khỏi vectorstore theo id của chunks
    def delete_from_vectorstore(self, file_name, user_id):
        #db_user, retriever_user = self.check_user_db(user_id)
        db_user = self.user_db
        docstore = db_user.docstore._dict
        key_delete = []
        for key, values in docstore.items():
            if values.metadata['source'].endswith(f"{file_name}"):
                key_delete.append(key)
        db_user.delete(key_delete)
        db_user.save_local(f"{USER_DATABASE}/{user_id}")
        os.remove(f"{USER_DOCUMENT}/{user_id}/{file_name}")
        sql_conn.delete_file(file_name, user_id)

    # upload file và lưu vào vectorstore faiss, lưu file vào folder của conversation_id
    def upload_file(self, file: UploadFile = File(...), user_id: str = Form(...)):
        if file.filename.endswith('.pdf'):
            # Lấy ra file size
            file.file.seek(0, os.SEEK_END)
            file_size = round(file.file.tell() / (1024 * 1024), 2)
            file.file.seek(0)
            result = sql_conn.save_file_detail(file.filename, file_size, user_id)

            # Nếu result =1: thỏa mãn yêu cầu về total_size <50 và file_size <20
            if result == 1:
                # Lưu file vào folder
                folder_path = f"{USER_DOCUMENT}/{user_id}"
                os.makedirs(folder_path, exist_ok=True)

                with open(f"{folder_path}/{file.filename}", "wb") as buff:
                    shutil.copyfileobj(file.file, buff)
                chunks = self.split_document(f"{folder_path}/{file.filename}")

                # bỏ vào vectorstore mới
                new_db_for_user = self.create_vectorstore(chunks)
                try:
                    # Nếu đã có db, hợp nhất db cũ với db mới
                    #db_user = self.check_user_db(user_id)[0]
                    db_user = self.user_db
                    merged_db_user = self.merge_to_vectorstore(db_user, new_db_for_user, user_id)

                    #return merged_db_user
                except:  # Nếu chưa có db
                    new_db_for_user.save_local(f'{USER_DATABASE}/{user_id}')
                    #return new_db_for_user

                return f"Successfully uploaded {file.filename}, num_splits: {len(chunks)}"
            else:
                return """Failed to upload document, the total size limit is 50Mb and the file size limit is 20Mb.
                        You can delete existed document to upload an other one!"""
        else:
            return "Only pdf files are supported"

    # For system
    def create_db_from_files(self):
        loader = DirectoryLoader(SYSTEM_DOCUMENT, glob="*.pdf", loader_cls=PyPDFLoader)
        documents = loader.load()
        chunks = self.text_splitter.split_documents(documents)

        # Embedding
        db = FAISS.from_documents(chunks, self.model_embedding)
        db.save_local(SYSTEM_DATABASE)
        return db
