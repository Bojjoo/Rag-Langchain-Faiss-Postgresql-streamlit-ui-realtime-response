from api.services import *


class ChatBot:
    def __init__(self):
        self.model_llm = None
        self.model_reformulate_question = ChatOpenAI(temperature=TEMPERATURE, model=MODEL_LLM)
        self.model_rerank = Ranker(model_name=MODEL_RERANK, max_length=5000)
        self.sender = ['human', 'ai']

    # Reformulate the question based on history
    def reformulate_question(self, question, history):
        remake_question_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REGENERATE_QUESTION_PROMPT),
                ("system", "Chat history: \n {chat_history}"),
                # MessagesPlaceholder(variable_name="chat_history"),
                ("system", "Reformulate this input: {question}"),
            ]
        )
        question_pt = remake_question_prompt.format(chat_history=history, question=question)
        new_question = self.model_reformulate_question.invoke(question_pt)
        return new_question.content

    # Retrieve relevant data
    def retriever(self, question, retriever):
        compressor = FlashrankRerank(client=self.model_rerank, top_n=5)  # Khai báo model rerank
        # retrieve data trước, sau đó bỏ vào model rerank để tính lại kết quả
        compression_retriever = ContextualCompressionRetriever(base_compressor=compressor, base_retriever=retriever)

        compressed_docs = compression_retriever.invoke(question)

        content_text = "\n\n---\n\n".join([doc.page_content for doc in compressed_docs
                                           if doc.metadata['relevance_score'] > 0.5])
        return compressed_docs, content_text

    # Get response
    def prompt_llm(self, question, context, history):
        llm_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PROMPT_TEMPLATE),
                ("system", "Chat history: \n {chat_history}\n"),
                ("system", "Context about relevant data: \n"),
                ("system", "{context}\n"),
                ("system", "Answer the question based on the above context: {question}"),
            ]
        )
        prompt = llm_prompt.format(chat_history=history, context=context, question=question)
        return prompt

    def question_handler(self, retriever, question_request: QuestionRequest):
        question = question_request.question
        conversation_id = question_request.conversation_id

        # Get history and generate new question
        history = sql_conn.get_chat_history(conversation_id)
        new_question = self.reformulate_question(question, history)

        # Retrieve and get answer
        context = self.retriever(new_question, retriever=retriever)[1]
        prompt = self.prompt_llm(new_question, context, history)
        return prompt

    async def send_message(self, prompt: str) -> AsyncIterable[str]:
        callback = AsyncIteratorCallbackHandler()
        self.model_llm = ChatOpenAI(temperature=TEMPERATURE, model=MODEL_LLM, streaming=True, callbacks=[callback])
        task = asyncio.create_task(
            self.model_llm.ainvoke(prompt)
        )

        try:
            async for token in callback.aiter():
                yield token
        except Exception as e:
            print(f"Caught exception: {e}")
        finally:
            callback.done.set()
        await task



        
    
