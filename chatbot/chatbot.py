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

    # --- LOAD CSV ---
    def load_all_csv(self):
        """Đọc tất cả CSV trong data_dir -> list Document"""
        documents = []
        for file in glob.glob(f"{self.data_dir}/**/*.csv", recursive=True):
            df = pd.read_csv(file)

            for _, row in df.iterrows():
                content = f"{row['title']} {row['genre']} {row['url']} {row['img_path']}"
                metadata = {
                    "title": row.get("title", "Unknown"),
                    "genre": row.get("genre", "Unknown"),
                    "url": row.get("url", "Unknown"),
                    "img_path": row.get("img_path", "Unknown"),
                    "views": row.get("views", 0),
                    "downloads": row.get("downloads", 0),
                    "category": os.path.relpath(file, self.data_dir)
                }
                documents.append(Document(page_content=content, metadata=metadata))
        return documents

    def init_engine_base(self):
        """Chỉ khởi tạo embeddings, vector DB và LLM (chưa tạo chain/memory)"""
        print(">> Đang load dữ liệu CSV...")
        docs = self.load_all_csv()

        print(">> Đang tạo embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="dangvantuan/vietnamese-embedding",
            encode_kwargs={"normalize_embeddings": True}
        )

        print(">> Khởi tạo Chroma DB...")
        db = Chroma.from_documents(docs, embeddings, persist_directory=self.chroma_dir)
        self.retriever = db.as_retriever()

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
        template = """Bạn là chatbot giới thiệu sách, trả lời bằng tiếng Việt.
        Dùng thông tin trong Context để trả lời.
        Nếu có sách phù hợp thì trả lời tittle + link url sách + link ảnh.
        Nếu không có thì nói: "Không tìm thấy dữ liệu cho sách này" và đưa ra vài gợi ý cho cuốn sách có liên quan.

        Context: {context}
        Question: {question}
        Answer:"""

        prompt = PromptTemplate(
            input_variables=["context", "question"],
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
            return_source_documents=False
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