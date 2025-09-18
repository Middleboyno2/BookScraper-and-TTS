from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


BANDS =[
    {"id": 1,"name":"The Beatles", "genre": "Rock"},
    {"id": 2,"name":"Metallica","genre": "Metal"},
    {"id": 3,"name":"Miles Davis","genre": "Jazz"},
    {"id": 4,"name":"Taylor Swift","genre": "Pop"},
]

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.get("/bands/{band_id}")
async def get_bands(band_id: int) -> dict:
    band = next((b for b in BANDS if b["id"] == band_id), None)
    if band is None:
        raise HTTPException(status_code=404, detail="Band not found")
    return band