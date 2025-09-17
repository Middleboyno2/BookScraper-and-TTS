from typing import Union

from fastapi import FastAPI
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

@app.get("/bands/")
def get_bands():
    return BANDS