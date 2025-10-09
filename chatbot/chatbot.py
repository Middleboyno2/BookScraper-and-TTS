from langchain_community.llms import GPT4All
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory


from dotenv import load_dotenv
import os
import glob
import pandas as pd
import uuid
from langchain.schema import Document
import re
import unicodedata
from hashlib import md5


load_dotenv(dotenv_path="url.env")

# MODEL_ID = os.getenv("MODEL_GEMMA_ID")
MODEL_PATH = os.getenv("MODEL_GPT4ALL_PATH")
DATA_DIR = "data"
CHROMA_DIR = "chroma_db"

class MyCustomHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Token: {token}", end="", flush=True)

class ChatbotEngine:
    """
    ChatbotEngine có khả năng:
      - Load tất cả CSV làm knowledge base
      - Khởi tạo Chroma + GPT4All
      - Quản lý nhiều session (mỗi session có memory riêng)
    """
    def __init__(self, data_dir=DATA_DIR, model_path=MODEL_PATH, chroma_dir=CHROMA_DIR, window_size=5):
        self.data_dir = data_dir
        self.model_path = model_path
        self.chroma_dir = chroma_dir
        self.window_size = window_size

        self.local_llm = None
        self.retriever = None
        self.sessions = {}  # Lưu {session_key: ConversationalRetrievalChain}
        
        
    @staticmethod
    def normalize_text(text):
        """
        Chuẩn hóa text: loại bỏ dấu, chuyển thành chữ thường
        Dùng để tăng khả năng tìm kiếm
        """
        if not isinstance(text, str):
            return str(text)
        
        # Chuyển về chữ thường
        text = text.lower()
        
        # Loại bỏ dấu tiếng Việt
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        
        # Loại bỏ ký tự đặc biệt, giữ lại chữ, số và khoảng trắng
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Loại bỏ khoảng trắng thừa
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def lower_text(text):
        """Chuyển text về chữ thường, giữ nguyên dấu"""
        if not isinstance(text, str):
            return str(text)
        return text.lower()

    # --- LOAD CSV ---
    def load_all_csv(self):
        """Đọc tất cả CSV trong data_dir -> list Document"""
        documents = []
        for file in glob.glob(f"{self.data_dir}/**/*.csv", recursive=True):
            df = pd.read_csv(file)

            for _, row in df.iterrows():
                # Content gốc (có dấu)
                original_content = f"{row['title']} {row['genre']}"
                
                # content chuẩn hóa (chữ thường)
                lower_content = self.lower_text(original_content)
                
                # Content chuẩn hóa (không dấu) để tăng khả năng tìm kiếm
                normalized_content = self.normalize_text(original_content)
                
                # Kết hợp cả 2 để search được cả có dấu và không dấu
                combined_content = f"{original_content} {lower_content} {normalized_content}"
                
                metadata = {
                    "title": row.get("title", "Unknown"),
                    "title_lower": self.lower_text(row.get("title", "Unknown")),
                    "title_normalized": self.normalize_text(row.get("title", "Unknown")),
                    "genre": row.get("genre", "Unknown"),
                    "url": row.get("url", "Unknown"),
                    "img_path": row.get("img_path", "Unknown"),
                    "views": row.get("views", 0),
                    "downloads": row.get("downloads", 0),
                    "category": os.path.relpath(file, self.data_dir)
                }
                
                documents.append(Document(page_content=combined_content, metadata=metadata))
        return documents
    
    def update_chroma_db(self):
        """
        Cập nhật Chroma DB từ các file CSV trong data_dir.
        - Chỉ thêm document mới chưa tồn tại trong DB.
        - Không xóa dữ liệu cũ.
        """
        print("Đang đọc dữ liệu từ CSV...")
        docs, ids = self.load_all_csv()

        print(f"Tổng số tài liệu quét được: {len(docs)}")

        # Kết nối hoặc khởi tạo DB
        db = Chroma(
            persist_directory=self.chroma_dir,
            embedding_function=self.embeddings
        )

        # Lấy danh sách ID đã có trong DB
        existing_data = db.get()
        existing_ids = set(existing_data["ids"])
        print(f"DB hiện có {len(existing_ids)} tài liệu.")

        # So sánh và lọc ra những tài liệu mới
        new_docs, new_ids = [], []
        for doc, id_ in zip(docs, ids):
            if id_ not in existing_ids:
                new_docs.append(doc)
                new_ids.append(id_)

        # Nếu có dữ liệu mới thì thêm vào DB
        if new_docs:
            print(f"Thêm {len(new_docs)} tài liệu mới vào DB...")
            db.add_documents(new_docs, ids=new_ids)
            db.persist()
            print("Cập nhật DB thành công!")
        else:
            print("Không có tài liệu mới để thêm. DB đã cập nhật.")

        # Tạo retriever để dùng cho LLM
        self.retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 100}
        )

        return db

    def init_engine_base(self):
        """Chỉ khởi tạo embeddings, vector DB và LLM (chưa tạo chain/memory)"""
        print(">> Đang load dữ liệu CSV...")
        docs = self.load_all_csv()

        print(">> Đang tạo embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="dangvantuan/vietnamese-embedding",
            encode_kwargs={"normalize_embeddings": True}
        )
        
        if not os.path.exists(self.chroma_dir):
            db = Chroma.from_documents(docs, embeddings, persist_directory=self.chroma_dir)
        else:
            db = Chroma(
                persist_directory=self.chroma_dir,
                embedding_function=embeddings
            )
        
        print(f"Số lượng embeddings hiện tại: {db._collection.count()}")

        # Tạo retriever với search_kwargs để tăng số kết quả
        self.retriever = db.as_retriever(
            search_type="mmr",       # đa dạng két quả
            search_kwargs={
                "k": 5,  # Số lượng vừa phải
                "fetch_k": 20,  # Fetch nhiều để có nhiều lựa chọn
                "lambda_mult": 0.5  # Đa dạng hóa kết quả
            }
        )

        print(">> Load LLM local GPT4All...")
        self.local_llm = GPT4All(
            model=self.model_path,
            callbacks=[MyCustomHandler()],
            verbose=True
        )
        print(">> Khởi tạo engine hoàn tất.")

    # --- SESSION MANAGEMENT ---
    def _create_chain(self):
        """Tạo 1 chain mới (memory riêng)"""
        
        #===================================================================================================================================================
        # Template cho việc trả lời dựa trên context và lịch sử chat
        template = """Bạn là một chatbot tên MrLoi, việc của bạn là tìm kiếm và đưa ra thông tin sách, trả lời bằng tiếng Việt.
        Dùng thông tin trong context để trả lời.
        Hướng dẫn trả lời:
        - Nếu tìm thấy sách phù hợp, trả lời: Tên sách, thể loại, link URL và link ảnh
        - Nếu không tìm thấy, nói: "Không tìm thấy dữ liệu cho sách này" và trả về toàn bộ thông tin sách tìm được
        - Trả lời đầy đủ thông tin một cách tự nhiên

        Lịch sử chat:
        {chat_history}

        Thông tin sách tìm được:
        {context}

        Câu hỏi hiện tại: {question}
        Trả lời:"""

        prompt = PromptTemplate(
            input_variables=["context","chat_history", "question"],
            template=template
        )

        # Sử dụng ConversationBufferWindowMemory với window_size
        memory = ConversationBufferWindowMemory(
            k=self.window_size,  # Giữ k cặp hội thoại gần nhất
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        return ConversationalRetrievalChain.from_llm(
            llm=self.local_llm,
            retriever=self.retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": prompt},
            return_source_documents=True,
            verbose=True
        )

    def ask(self, user_id: str, question: str):
        """
        Trả lời câu hỏi cho user_id cụ thể.
        Tự động tạo session mới nếu user_id chưa tồn tại.
        
        Args:
            user_id: ID của user từ client
            question: Câu hỏi của user
            
        Returns:
            dict: {"answer": str, "user_id": str, "is_new_session": bool}
        """
        if not self.local_llm or not self.retriever:
            raise RuntimeError("Engine chưa được khởi tạo. Gọi init_engine_base() trước.")

        # Kiểm tra xem user_id đã có session chưa
        is_new_session = user_id not in self.sessions
        
        if is_new_session:
            print(f">> Tạo session mới cho user: {user_id}")
            self.sessions[user_id] = self._create_chain()
        
        # Lấy chain của user
        chain = self.sessions[user_id]
        
        # Thực hiện truy vấn
        result = chain.invoke({"question": question})
        
        return {
            "answer": result["answer"],
            "user_id": user_id,
            "is_new_session": is_new_session
        }

    def get_session_history(self, user_id: str):
        """
        Lấy lịch sử hội thoại của user_id
        
        Args:
            user_id: ID của user
            
        Returns:
            list: Danh sách các message trong memory
        """
        if user_id not in self.sessions:
            return []
        
        chain = self.sessions[user_id]
        memory = chain.memory
        
        # Lấy chat history
        return memory.load_memory_variables({}).get("chat_history", [])

    def clear_session(self, user_id: str):
        """
        Xóa lịch sử chat của user nhưng giữ session
        
        Args:
            user_id: ID của user
        """
        if user_id in self.sessions:
            chain = self.sessions[user_id]
            chain.memory.clear()
            print(f">> Đã xóa lịch sử chat của user: {user_id}")
        else:
            print(f">> User {user_id} không có session")

    def end_session(self, user_id: str):
        """
        Kết thúc và xóa hoàn toàn session của user
        
        Args:
            user_id: ID của user
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            print(f">> Đã kết thúc session của user: {user_id}")
        else:
            print(f">> User {user_id} không có session để kết thúc")

    def get_active_sessions(self):
        """
        Lấy danh sách các user_id đang có session active
        
        Returns:
            list: Danh sách user_id
        """
        return list(self.sessions.keys())

    def get_session_info(self, user_id: str):
        """
        Lấy thông tin về session của user
        
        Args:
            user_id: ID của user
            
        Returns:
            dict: Thông tin session
        """
        if user_id not in self.sessions:
            return {
                "user_id": user_id,
                "exists": False,
                "history_count": 0
            }
        
        history = self.get_session_history(user_id)
        
        return {
            "user_id": user_id,
            "exists": True,
            "history_count": len(history),
            "window_size": self.window_size
        }