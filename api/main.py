from typing import Union
from fastapi import FastAPI, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
import time
import os
import logging

from dotenv import load_dotenv
from scrape.scrape_web import Scrape
from scrape.book_csv import CSV_DATA_BOOK
from chatbot.chatbot import ChatbotEngine


load_dotenv(dotenv_path="url.env")


# # Khởi tạo chatbot engine
# engine = ChatbotEngine()
# engine.init_engine_base()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global engine instance
chatbot_engine = None

# --- LIFESPAN CONTEXT MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo engine khi start app, cleanup khi shutdown"""
    global chatbot_engine
    
    logger.info("Khởi động ứng dụng...")
    try:
        chatbot_engine = ChatbotEngine(window_size=5)
        chatbot_engine.init_engine_base()
        logger.info("ChatbotEngine đã sẵn sàng!")
    except Exception as e:
        logger.error(f"Lỗi khởi tạo engine: {e}")
        raise
    
    yield
    
    logger.info("Đang dọn dẹp resources...")
    # Cleanup nếu cần
    chatbot_engine = None
    
# --- FASTAPI APP ---
app = FastAPI(
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    
# === DEPENDENCY ======================================================================================================================================

def get_engine():
    """Dependency để lấy engine instance"""
    if chatbot_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot engine chưa được khởi tạo"
        )
    return chatbot_engine

# ======================================================================================================================================================

# Tự động cập nhật dữ liệu sách 1 ngày/lần
def auto_update_books_data(engine: ChatbotEngine = Depends(get_engine)):
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
            if os.path.exists(engine.chroma_dir):
                engine.update_chroma_db()
            print(f"Hoàn thành {url_key}")
        except Exception as e:
            print(f"Lỗi khi cập nhật {url_key}: {e}")

    print("Tất cả dữ liệu sách đã được cập nhật xong.")
    
scheduler = BackgroundScheduler()
scheduler.add_job(auto_update_books_data, "interval", days=1)  # chạy mỗi ngày 1 lần
scheduler.start()


# === PYDANTIC MODELS ==================================================================================================================================

class BookInfo(BaseModel):
    title: str
    genre: str
    url: str
    img_path: str


class QuestionRequest(BaseModel):
    """Request model cho câu hỏi"""
    user_id: str = Field(..., min_length=1, description="ID của user")
    question: str = Field(..., min_length=1, description="Câu hỏi của user")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "question": "Giới thiệu sách trinh thám hay"
            }
        }


class AnswerResponse(BaseModel):
    """Response model cho câu trả lời"""
    answer: str = Field(..., description="Câu trả lời từ chatbot")
    user_id: str = Field(..., description="ID của user")
    book: Optional[List[BookInfo]] = Field(None, description="Danh sách sách được tìm thấy")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Dưới đây là một số sách trinh thám hay...",
                "user_id": "user123",
                "books": [
                    {
                    "title": "Lấy Tên Của Ai Lặng Lẽ Yêu Em",
                    "genre": "Lãng mạn",
                    "url": "https://ebookvie.com/ebook/lay-ten-cua-ai-lang-le-yeu-em/",
                    "img_path": "https://ebookvie.com/wp-content/uploads/2023/12/ebook-lay-ten-cua-ai-lang-le-yeu-em-prc-pdf-epub.jpg"
                    }
                ]
            }
        }


class SessionInfoResponse(BaseModel):
    """Response model cho thông tin session"""
    user_id: str
    exists: bool
    history_count: int
    window_size: Optional[int] = None


class MessageResponse(BaseModel):
    """Response model cho các thao tác thành công"""
    message: str
    user_id: str
    success: bool = True


class ActiveSessionsResponse(BaseModel):
    """Response model cho danh sách session active"""
    active_sessions: List[str]
    total_count: int


class HealthResponse(BaseModel):
    """Response model cho health check"""
    status: str
    engine_initialized: bool


# === API ENDPOINTS ====================================================================================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Chatbot API is running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Kiểm tra trạng thái của service"""
    return {
        "status": "healthy" if chatbot_engine is not None else "unhealthy",
        "engine_initialized": chatbot_engine is not None
    }


@app.post(
    "/ask",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    tags=["Chat"]
)
async def ask_question(
    request: QuestionRequest,
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Gửi câu hỏi và nhận câu trả lời
    
    - **user_id**: ID duy nhất của user (tự động tạo session nếu chưa có)
    - **question**: Câu hỏi cần trả lời
    """
    try:
        result = engine.ask(
            user_id=request.user_id,
            question=request.question
        )
        logger.info(f"metadata: {result.get('books')}")
        return result
    except Exception as e:
        logger.error(f"Lỗi khi xử lý câu hỏi: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý câu hỏi: {str(e)}"
        )


@app.get(
    "/session/{user_id}",
    response_model=SessionInfoResponse,
    tags=["Session Management"]
)
async def get_session_info(
    user_id: str,
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Lấy thông tin về session của user
    
    - **user_id**: ID của user
    """
    try:
        info = engine.get_session_info(user_id)
        return info
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi lấy thông tin session: {str(e)}"
        )


@app.get(
    "/session/{user_id}/history",
    response_model=List[Dict[str, Any]],
    tags=["Session Management"]
)
async def get_session_history(
    user_id: str,
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Lấy lịch sử hội thoại của user
    
    - **user_id**: ID của user
    """
    try:
        history = engine.get_session_history(user_id)
        
        # Convert messages to dict format
        history_dict = []
        for msg in history:
            history_dict.append({
                "type": msg.__class__.__name__,
                "content": msg.content
            })
        
        return history_dict
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi lấy lịch sử: {str(e)}"
        )


@app.delete(
    "/session/{user_id}/history",
    response_model=MessageResponse,
    tags=["Session Management"]
)
async def clear_session_history(
    user_id: str,
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Xóa lịch sử chat nhưng giữ session
    
    - **user_id**: ID của user
    """
    try:
        engine.clear_session(user_id)
        return {
            "message": "Đã xóa lịch sử chat",
            "user_id": user_id,
            "success": True
        }
    except Exception as e:
        logger.error(f"Lỗi khi xóa lịch sử: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xóa lịch sử: {str(e)}"
        )


@app.delete(
    "/session/{user_id}",
    response_model=MessageResponse,
    tags=["Session Management"]
)
async def end_session(
    user_id: str,
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Kết thúc và xóa hoàn toàn session của user
    
    - **user_id**: ID của user
    """
    try:
        engine.end_session(user_id)
        return {
            "message": "Đã kết thúc session",
            "user_id": user_id,
            "success": True
        }
    except Exception as e:
        logger.error(f"Lỗi khi kết thúc session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi kết thúc session: {str(e)}"
        )


@app.get(
    "/sessions/active",
    response_model=ActiveSessionsResponse,
    tags=["Session Management"]
)
async def get_active_sessions(
    engine: ChatbotEngine = Depends(get_engine)
):
    """
    Lấy danh sách tất cả session đang active
    """
    try:
        sessions = engine.get_active_sessions()
        return {
            "active_sessions": sessions,
            "total_count": len(sessions)
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi lấy danh sách session: {str(e)}"
        )


# --- ERROR HANDLERS ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Lỗi server không xác định",
            "detail": str(exc),
            "status_code": 500
        }
    )

    
    
    
    
    

# dict url env key -> csv path env key
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