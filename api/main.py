from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler
import time
import os

from dotenv import load_dotenv
from scrape.scrape_web import Scrape
from scrape.book_csv import CSV_DATA_BOOK
from chatbot.chatbot import ChatbotEngine



app = FastAPI()

load_dotenv(dotenv_path="url.env")

# Khởi tạo chatbot engine
engine = ChatbotEngine()
engine.init_engine()

# Tự động cập nhật dữ liệu sách 1 ngày/lần
def auto_update_books_data():
    scrape = Scrape()
    csv_data = CSV_DATA_BOOK()
    
    for url_key, path_key in category_map.items():
        url = os.getenv(url_key)
        csv_file = os.getenv(path_key)
        
        if not url or not csv_file:
            print(f"Bỏ qua {url_key} vì thiếu URL hoặc PATH trong .env")
            continue
        
        try:
            print(f"Đang cập nhật: {url_key} -> {csv_file}")
            all_books_data = scrape.scrape_all_pages_selenium_2(url)
            csv_data.update_csv(csv_file, all_books_data)
            print(f"Hoàn thành {url_key}")
        except Exception as e:
            print(f"Lỗi khi cập nhật {url_key}: {e}")

    print("Tất cả dữ liệu sách đã được cập nhật xong.")
    
scheduler = BackgroundScheduler()
scheduler.add_job(auto_update_books_data, "interval", days=1)  # chạy mỗi ngày 1 lần
scheduler.start()


@app.get("/")
async def read_root():
    return {"Title": "BookScraper-and-TTS"}

@app.post("/ask")
async def ask(ques: str):
    answer = engine.ask(ques)
    return {"question": ques, "answer": answer}

# @app.get("/bands/{band_id}")
# async def get_bands(band_id: int) -> dict:
#     band = next((b for b in BANDS if b["id"] == band_id), None)
#     if band is None:
#         raise HTTPException(status_code=404, detail="Band not found")
#     return band

# @app.put("/books/update_data")
# async def update_books_data():
#     scrape = Scrape()
#     csv_data = CSV_DATA_BOOK()
#     try:
#         all_books_data = scrape.scrape_all_pages_selenium(
#             url=os.getenv("NEW_BOOK_URL"),
#         )
#         csv_data.update_csv(all_books_data)
#         return JSONResponse(
#             status_code=200, 
#             content={
#                 "status": "success",
#                 "message": "Books data updated successfully",
#             }
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))    
    
# @app.get("/books/get_data")
# async def get_books_data():
#     csv_data = CSV_DATA_BOOK()
#     try:
#         data_books = csv_data.get_data()
#         return JSONResponse(
#             status_code=200, 
#             content={
#                 "status": "success",
#                 "data": data_books
#             }
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# dict: {key url : key path}
category_map = {
    "ADVENTURE_URL": "data_adventure_path",
    "DETECTIVE": "data_detective_path",
    "TIME_TRAVEL": "data_time_travel_path",
    "HORROR": "data_horror_path",
    "FICTION": "data_fiction_path",

    "CHILDREN": "data_children_path",
    "COMICS": "data_comics_path",
    "EDUCATION": "data_education_path",
    "POETRY": "data_poetry_path",

    "COMEDY": "data_comedy_path",
    "MEDICINE": "data_medicine_path",
    "NOVEL": "data_novels_path",
    "PHILOSOPHY": "data_philosophy_path",
    "ROMANCE": "data_romance_path",

    "ECONOMIC_FINANCE": "data_economic_finance_path",
    "FENG_SHUI": "data_feng_shui_path",
    "LIFE_SKILL": "data_life_skills_path",
    "MANAGEMENT": "data_management_path",
    "PSYCHOLOGY": "data_psychology_path",

    "CULTURE_SOCIETY": "data_culture_society_path",
    "HISTORY": "data_history_path",
    "GEOGRAPHY": "data_geography_path",
    "MEMOIR": "data_memoirs_path",

    "18+BOOK": "data_18+_path",
    "XIANXIA": "data_xianxia_path",
    "SHORT_STORY": "data_short_stories_path",
    "WUXIA": "data_wuxia_path",
}