from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

from scrape.scrape_web import Scrape
from scrape.book_csv import CSV_DATA_BOOK

app = FastAPI()
load_dotenv(dotenv_path="url.env")

@app.get("/")
async def read_root():
    return {"Title": "BookScraper-and-TTS"}

# @app.get("/bands/{band_id}")
# async def get_bands(band_id: int) -> dict:
#     band = next((b for b in BANDS if b["id"] == band_id), None)
#     if band is None:
#         raise HTTPException(status_code=404, detail="Band not found")
#     return band

@app.put("/books/update_data")
async def update_books_data():
    scrape = Scrape()
    csv_data = CSV_DATA_BOOK()
    try:
        all_books_data = scrape.scrape_all_pages_selenium(
            url=os.getenv("NEW_BOOK_URL"),
        )
        csv_data.update_csv(all_books_data)
        return JSONResponse(
            status_code=200, 
            content={
                "status": "success",
                "message": "Books data updated successfully",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    
@app.get("/books/get_data")
async def get_books_data():
    scrape = Scrape()
    try:
        data_books = CSV_DATA_BOOK.get_data()
        return JSONResponse(
            status_code=200, 
            content={
                "status": "success",
                "data": data_books
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))