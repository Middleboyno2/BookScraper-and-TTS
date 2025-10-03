from langchain_community.llms import GPT4All
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from scrape.book_csv import CSV_DATA_BOOK


class ChatBot:
docs = load_all_csv("data")

# tạo embeddings bằng HuggingFace model (offline)
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# lưu dữ liệu vào vector DB (Chroma)
db = Chroma.from_documents(docs, embeddings, persist_directory="chroma_db")
db.persist()

# load mô hình local GPT4All
local_llm = GPT4All(model="models/ggml-gpt4all-j-v1.3-groovy.bin", verbose=True)

# tạo QA system
qa = RetrievalQA.from_chain_type(
    llm=local_llm,
    retriever=db.as_retriever(),
    chain_type="stuff"
)