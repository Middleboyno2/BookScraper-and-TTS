from langchain_community.llms import GPT4All
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory


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
    def __init__(self, data_dir=DATA_DIR, model_path=MODEL_PATH, chroma_dir=CHROMA_DIR):
        self.data_dir = data_dir
        self.model_path = model_path
        self.chroma_dir = chroma_dir

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
                content = f"{row['title']} {row['genre']} {row['url']} {row['img_path']} {row['views']} {row['downloads']}"
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

        print("✅ Engine đã sẵn sàng (retriever + model).")

    # --- SESSION MANAGEMENT ---
    def _create_chain(self):
        """Tạo 1 chain mới (memory riêng)"""
        template = """Bạn là chatbot giới thiệu sách, trả lời bằng tiếng Việt.
        Dùng thông tin trong Context để trả lời.
        Nếu có sách phù hợp thì trả lời tên + link.
        Nếu không có thì nói: "Không tìm thấy dữ liệu cho truyện này".

        Context: {context}
        Question: {question}
        Answer:"""

        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=template
        )

        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        return ConversationalRetrievalChain.from_llm(
            llm=self.local_llm,
            retriever=self.retriever,
            memory=memory,
            combine_docs_chain_kwargs={"prompt": prompt}
        )

    def ask(self, user_id: str, question: str, session_id: str = None):
        """Trả lời câu hỏi — tự khởi tạo session nếu chưa có"""
        if not self.local_llm or not self.retriever:
            raise RuntimeError("Engine chưa được khởi tạo. Gọi init_engine_base() trước.")

        # Nếu user chưa có session list
        if user_id not in self.sessions:
            self.sessions[user_id] = {}

        # Nếu chưa có session_id thì tạo mới
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"Tạo session_id mới cho user {user_id}: {session_id}")

        # Nếu session_id chưa tồn tại -> tạo chain mới
        if session_id not in self.sessions[user_id]:
            self.sessions[user_id][session_id] = self._create_chain()
            print(f"Tạo chain mới cho {user_id}:{session_id}")

        chain = self.sessions[user_id][session_id]
        result = chain({"question": question})
        return {"answer": result["answer"], "session_id": session_id}

    def end_session(self, user_id: str, session_id: str):
        """Xoá session"""
        if user_id in self.sessions and session_id in self.sessions[user_id]:
            del self.sessions[user_id][session_id]
            print(f"Đã xoá session {session_id} của user {user_id}")
            if not self.sessions[user_id]:
                del self.sessions[user_id]
        else:
            print(f"Session {session_id} không tồn tại cho user {user_id}")