import os
import requests
import streamlit as st
import time
import sys
from api.database.database import SQLDatabase
from api.services.vectorstore_faiss import VectorStore
# Thêm thư mục mẹ vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import module từ thư mục mẹ

sql_conn = SQLDatabase()
sender = ['human', 'ai']


SYSTEM_URL = os.getenv("CHATBOT_URL", "http://127.0.0.1:8000/get_answer/")
USER_URL = os.getenv("CHATBOT_URL", "http://127.0.0.1:8000/get_answer_about_users_data/")
USER_RETRIEVER = os.getenv("RETRIEVER", "http://127.0.0.1:8000/get_retriever/")


def response_generator(text):
    for word in text.strip():
        yield word + ""
        time.sleep(0.01)


def handler_input(question: str, conversation_id: str, user_id: str, url):
    data = {
        "question": question,
        "conversation_id": conversation_id,
        "user_id": user_id
    }
    response = requests.post(url=url, json=data, stream=True)

    if response.status_code == 200:
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            # if chunk:
            yield chunk
    else:
        yield f"Error: {response.status_code} - {response.reason}"


def get_retriever(user_id: str):
    data = {
        "user_id": user_id
    }
    try:
        # Gửi yêu cầu POST đến endpoint FastAPI
        response = requests.post(url=USER_RETRIEVER, json=data)
        # Kiểm tra xem yêu cầu có thành công hay không
        if response.status_code == 200:
            # Trả về nội dung phản hồi
            return response.json()
        else:
            # Nếu có lỗi, trả về thông báo lỗi
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        # Bắt lỗi trong quá trình gọi API
        return f"Error: {str(e)}"


# Màn hình đăng nhập
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Login to access the chat")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Lấy mật khẩu từ cơ sở dữ liệu dựa trên username
        stored_password = sql_conn.get_password_of_user(username)

        # Kiểm tra nếu mật khẩu đúng
        if stored_password and stored_password == password:
            st.session_state["authenticated"] = True
            st.session_state["user_name"] = username
            st.success("Login successful! Welcome to the chat application.")
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")

# Nếu người dùng đã đăng nhập thành công, hiển thị giao diện chat
if st.session_state["authenticated"]:
    st.set_page_config(layout="wide")
    st.title("Hello welcome!")

    # Lấy ID user từ tên user
    st.session_state['user_id'] = sql_conn.get_userid_from_username(st.session_state["user_name"])
    user_id = st.session_state['user_id']
    # Lấy danh sách các phiên hội thoại từ cả System và User Data
    conversations_system = sql_conn.get_conversation_session_system(st.session_state["user_id"])
    conversations_user = sql_conn.get_conversation_session_user(st.session_state["user_id"])

    system_conversation_list = [i[0] for i in conversations_system]
    user_conversation_list = [i[0] for i in conversations_user]

    # Thêm menu chọn Conversation vào sidebar dưới dạng danh sách các nút
    with st.sidebar:
        st.info("Nice to meet you.")
################################################################
        # Nút upload data:
        # Thêm nút upload file vào sidebar
        st.sidebar.markdown(":green-background[**UpLoad Your Documents: **]")
        uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type=["pdf"])

        # Kiểm tra nếu người dùng chọn file
        if uploaded_file is not None:
            # Xác định URL của endpoint FastAPI và user_id
            api_endpoint = "http://127.0.0.1:8000/upload_data"

            if st.sidebar.button("Upload File"):
                # Gửi POST request với file trực tiếp từ Streamlit lên FastAPI
                with st.spinner("Uploading..."):
                    try:
                        # Định nghĩa multipart-form cho file và các thông tin khác
                        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                        data = {"user_id": st.session_state["user_id"]}

                        # Gửi request lên FastAPI
                        response = requests.post(api_endpoint, files=files, data=data)

                        # Hiển thị phản hồi
                        if response.status_code == 200:
                            st.success(f"Successfully uploaded {uploaded_file.name}.")
                            st.json(response.json())  # Hiển thị JSON trả về từ API
                        else:
                            st.error(f"Failed to upload file. Error {response.status_code}: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
################################################################
        # Thêm tùy chọn để tạo cuộc hội thoại mới
        st.markdown(":green-background[**Create New Conversation:**]")
        if st.button("Create New Conversation"):
            st.session_state["create_new_conversation"] = True

        # Nếu nhấn nút "Create New Conversation", hiển thị hộp nhập để người dùng nhập tên hội thoại
        if "create_new_conversation" in st.session_state and st.session_state["create_new_conversation"]:
            conversation_name = st.text_input("Enter the name of the new conversation:")

            # Chọn loại conversation
            conversation_type = st.radio(
                "Select Conversation Type:",
                ("Chat with System", "Chat with User Data"),
                key="conversation_type_radio"
            )

            if st.button("Submit"):
                if conversation_name:
                    # Tạo một phiên hội thoại mới với loại conversation đã chọn
                    is_user_data = True if conversation_type == "Chat with User Data" else False
                    sql_conn.create_conversation(conversation_name, st.session_state["user_id"], is_user_data)
                    st.success(f"New conversation '{conversation_name}' created successfully!")
                    st.session_state["create_new_conversation"] = False
                else:
                    st.warning("Conversation name cannot be empty.")
                st.rerun()

        st.header("All Conversations:", divider='orange')

        # Nhóm "System chat"
        st.markdown(":green-background[**Conversation with system:**]")
        if conversations_system:
            # Duyệt qua toàn bộ danh sách hội thoại với System và hiển thị dưới dạng nút
            for conv in conversations_system:
                if st.button(f"{conv[1]}", key=f"system_{conv[0]}", use_container_width= True):
                    st.session_state["selected_conversation_id"] = conv[0]
                    # st.experimental_rerun()  # Làm mới giao diện khi chọn một conversation
        else:
            st.warning("No system conversation sessions available.")

        # Nhóm "User's data chat"
        st.markdown(":green-background[**Conversation with your documents:**]")
        if conversations_user:
            # Lấy db Faiss của user
            user_retriever = get_retriever(st.session_state["user_id"])
            if user_retriever == "None":
                st.warning("Look like you have not uploaded any documents yet! Please upload your documents first!")

            # Duyệt qua toàn bộ danh sách hội thoại với User Data và hiển thị dưới dạng nút
            for conv in conversations_user:
                if st.button(f"{conv[1]}", key=f"user_{conv[0]}", use_container_width=True):
                    st.session_state["selected_conversation_id"] = conv[0]
                    # st.experimental_rerun()  # Làm mới giao diện khi chọn một conversation
        else:
            st.warning("No user data conversation sessions available.")

    # Hiển thị lịch sử hội thoại của phiên đã chọn
    try:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        if "selected_conversation_id" in st.session_state:
            chat_history = sql_conn.get_chat_history(st.session_state["selected_conversation_id"])
            st.session_state.messages = []
            # Cập nhật tin nhắn vào session_state.messages nếu có lịch sử
            if chat_history:
                st.session_state.messages = [
                    {"role": "user" if sender == "human" else "assistant", "output": message}
                    for sender, message in chat_history
                ]

        # Hiển thị các tin nhắn trong phiên hội thoại đã chọn
        if "messages" in st.session_state:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["output"])

            # Gửi tin nhắn mới trong giao diện chat
        if prompt := st.chat_input("What do you want to know?"):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "output": prompt})

            with st.chat_message("assistant"):
                assistant_message = st.empty()
                if st.session_state["selected_conversation_id"] in system_conversation_list:
                    response_stream = handler_input(
                        prompt, st.session_state["selected_conversation_id"], user_id, SYSTEM_URL)
                elif st.session_state["selected_conversation_id"] in user_conversation_list:
                    response_stream = handler_input(
                        prompt, st.session_state["selected_conversation_id"], user_id, USER_URL)

                # Stream and display the assistant's response
                output = ""
                for token in response_stream:
                    output += token
                    assistant_message.markdown(output)
                    time.sleep(0.01)
                st.session_state.messages.append({"role": "assistant", "output": output})
            if not output.startswith("Error:"):
                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[0], prompt)
                sql_conn.insert_chat(st.session_state["selected_conversation_id"], sender[1], output)

    except:
        st.warning("Please choose the conversation or create one!")


