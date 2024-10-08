import psycopg2
from api.config import *
from datetime import datetime
import secrets


class SQLDatabase:
    def __init__(self):
        conn = psycopg2.connect(database=DATABASE, host=HOST, port=PORT, user=USER, password=PASSWORD)
        self.cur = conn.cursor()
        conn.set_session(autocommit=True)

    # Thêm tin nhắn sau mỗi câu hỏi và câu trả lời
    def insert_chat(self, conversation_id, sender, message_text):
        query = "INSERT INTO messages (conversation_id, sender, message_text) VALUES (%s, %s, %s)"
        self.cur.execute(query, (conversation_id, sender, message_text))

    # Lấy ra user_id từ username (unique)
    def get_userid_from_username(self, username):
        self.cur.execute(f"select user_id from users where username='{username}'")
        return self.cur.fetchall()[0][0]
    
    # Lấy ra các conversation session QA với system của user dựa vào userid
    def get_conversation_session_system(self, user_id):
        self.cur.execute(f"select conversation_id, conversation_name from conversations where user_id='{user_id}' and user_data= False")
        a=self.cur.fetchall()
        return a
    
    # Lấy ra các conversation session QA với userdata của user dựa vào userid
    def get_conversation_session_user(self,user_id):
        self.cur.execute(f"select conversation_id, conversation_name from conversations where user_id='{user_id}' and user_data= True")
        a = self.cur.fetchall()
        return a

    # tạo ra một conversation mới
    def create_conversation(self, conversation_name, user_id, is_user_data):
        conversation_id = datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(4)
        self.cur.execute(
            f"INSERT INTO conversations(conversation_id, conversation_name, user_id, user_data) VALUES ('{conversation_id}', '{conversation_name}', '{user_id}', {is_user_data})")

    # Lấy ra user_id tương ứng với conversation_id vừa nhập vào
    def get_userid_from_cid(self, conversation_id):
        self.cur.execute(f"select user_id from conversations where conversation_id='{conversation_id}'")
        a = self.cur.fetchall()
        return a[0][0]

    # Lấy ra history chat từ mỗi conversation_id: 8 lịch sử chat = 4 cuộc hội thoại
    def get_chat_history(self, conversation_id):
        self.cur.execute(f"select sender, message_text from messages where conversation_id='{conversation_id}' order by message_id")
        return self.cur.fetchall()[-8::]
    
    # Lấy ra mk của user để đăng nhập
    def get_password_of_user(self, name):
        self.cur.execute(f"select password from users where username='{name}'")
        return self.cur.fetchall()[0][0]

    # Đăng kí tài khoản
    def register_account(self, name, password):
        id = datetime.now().strftime("%Y%m%d%H%m") + secrets.token_hex(4)
        try:
            self.cur.execute(f"insert into users(user_id, username, password) VALUES('{id}','{name}','{password}')")
            print("Register account successfully!")
        except:
            print(f"The name {name} is existed!")

    # Lưu thông tin file của user vào table files
    def get_total_size(self, user_id):
        self.cur.execute(f"select sum(size) from files where user_id='{user_id}'")
        total_size = self.cur.fetchall()[0][0]
        return total_size

    def save_file_detail(self, file_name, file_size, user_id):
        total_size = self.get_total_size(user_id)
        if total_size is None or (total_size < 50 and file_size < 20):
            file_id = datetime.now().strftime("%m%d%H%M%S") + secrets.token_hex(4)
            self.cur.execute(f"insert into files(file_id,file_name,size,user_id) values ('{file_id}','{file_name}','{file_size}','{user_id}')")
            return 1
        elif total_size > 50 or file_size > 20:
            return 0

    # Lấy ra các file của user_id
    def get_files(self, user_id):
        self.cur.execute(f"select file_name, size from files where user_id='{user_id}'")
        files = self.cur.fetchall()
        return files

    # Xóa thông tin file của user khỏi files
    def delete_file(self, file_name, user_id):
        self.cur.execute(f"select file_id from files where file_name='{file_name}' and user_id='{user_id}'")
        a = self.cur.fetchall()
        lst = []
        for i in a:
            lst.append(i[0])
        for i in lst:
            self.cur.execute(f"delete from files where file_id ='{i}'")

    # Xóa conversation
    def delete_conversation(self,conversation_id):
        self.cur.execute(f"delete from messages where conversation_id='{conversation_id}'")
        self.cur.execute(f"delete from conversations where conversation_id={conversation_id}")

