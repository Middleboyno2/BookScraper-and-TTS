from langchain_community.llms import GPT4All
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.prompts import PromptTemplate

from dotenv import load_dotenv
import os
import glob
import pandas as pd
from langchain.schema import Document


load_dotenv(dotenv_path="url.env")

MODEL_ID = os.getenv("MODEL_GEMMA_ID")
MODEL_PATH = os.getenv("MODEL_GPT4ALL_PATH")
DATA_DIR = "data"
CHROMA_DIR = "chroma_db"

class MyCustomHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"Token: {token}", end="", flush=True)

class ChatbotEngine:
    def __init__(self, data_dir=DATA_DIR, model_path=MODEL_PATH, chroma_dir=CHROMA_DIR):
        self.data_dir = data_dir
        self.model_path = model_path
        self.chroma_dir = chroma_dir
        self.qa = None

    def load_all_csv(self):
        """Đọc toàn bộ file CSV trong data_dir và tạo list Document"""
        documents = []
        for file in glob.glob(f"{self.data_dir}/**/*.csv", recursive=True):
            df = pd.read_csv(file)
            print(df.columns)

            for _, row in df.iterrows():
                # CSV có cột: title, genre, url, img_path, views, downloads
                content = f"{row['title']} {row['genre']} {row['url']} {row['views']} {row['downloads']}"
                metadata = {
                    "title": row.get('title', 'Unknown'),
                    "genre": row.get('genre', 'Unknown'),
                    "url": row.get('url', 'Unknown'),
                    "img_path": row.get('img_path', 'Unknown'),
                    "views": row.get('views', 0),
                    "downloads": row.get('downloads', 0),
                    "category": os.path.dirname(file).split(os.sep)[-1]
                }
                documents.append(Document(page_content=content, metadata=metadata))
        return documents

    def init_engine(self):
        """Khởi tạo embeddings, vector DB và LLM"""
        print(">> Đang load dữ liệu CSV...")
        docs = self.load_all_csv()

        print(">> Đang tạo embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="dangvantuan/vietnamese-embedding",
            encode_kwargs={"normalize_embeddings": True}
        )


        print(">> Khởi tạo Chroma DB...")
        db = Chroma.from_documents(docs, embeddings, persist_directory=self.chroma_dir)
        
        print(">> Load LLM local GPT4All...")
        local_llm = GPT4All(
            model=self.model_path,
            callbacks=[MyCustomHandler()],   # in token khi stream
            verbose=True
        )
        
        template = """Bạn là chatbot giới thiệu sách.
        Dùng thông tin trong Context để trả lời.
        Nếu có sách khớp thì trả lời tên + link.
        Nếu không có thì nói: "Không tìm thấy dữ liệu cho truyện này".

        Context: {context}

        Question: {question}

        Answer:"""
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=template,
        )

        self.qa = RetrievalQA.from_chain_type(
            llm=local_llm,
            retriever=db.as_retriever(),
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt}
        )
        
    def ask(self, question: str):
        if not self.qa:
            raise RuntimeError("Engine chưa được khởi tạo. Hãy gọi init_engine() trước.")
        return self.qa.invoke(question)
