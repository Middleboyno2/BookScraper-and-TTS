# Copilot Instructions for BookScraper-and-TTS

## Project Overview
This project integrates web scraping, RAG-based chatbot, and TTS (Text-to-Speech) to provide audiobook and information services for Vietnamese literature from `ebookvie.com`. It exposes a FastAPI backend for API access and is designed for easy integration with mobile apps.

## Architecture & Key Components
- **scraper/**: Contains all web scraping logic using Selenium and BeautifulSoup. Main entry: `scraped_web.py` (calls `Books` in `books.py`, uses `setup_driver.py` for browser setup, and `update_csv.py` for CSV management).
- **data/books.csv**: Central data store for scraped book metadata. Updated incrementally.
- **rag_model/**: (Planned) For Retrieval-Augmented Generation chatbot logic and vector database.
- **tts_model/**: (Planned) For TTS model and voice assets.
- **api/main.py**: FastAPI endpoints. Example endpoints are present; extend for project APIs.
- **pyproject.toml**: Project dependencies (uses Python >=3.13, `uv` for environment management).

## Developer Workflows
- **Environment**: Use Python 3.13+ and install dependencies with `uv` (see README for details).
- **Run API server**: `uv run uvicorn main:app --reload` from the `api/` directory.
- **Scraping**: Run `scraped_web.py` to scrape and update `data/books.csv`. Scraper is modular—adjust `max_pages` or scraping logic as needed.
- **Data update**: All new book data is merged and deduplicated in `update_csv.py`.

## Project Conventions
- **Vietnamese comments and variable names** are common, especially in scraping modules.
- **CSV as primary data exchange** between scraper and other modules.
- **Headless browser**: Scraper defaults to headless Chrome but can be toggled for debugging.
- **No hardcoded credentials**: Use `url.env` for environment variables.

## Integration & Extensibility
- **API**: Extend `api/main.py` for new endpoints. Follow FastAPI patterns.
- **RAG/TTS**: Place new models or logic in `rag_model/` and `tts_model/`.
- **Mobile integration**: APIs are designed for easy mobile app consumption.

## Examples
- To scrape all books: Run `scraped_web.py` (edit for custom URLs or page limits).
- To update API: Add new routes in `api/main.py` using FastAPI.

## References
- See `README.md` for setup and usage details.
- Key files: `scraper/scraped_web.py`, `scraper/books.py`, `scraper/update_csv.py`, `api/main.py`, `pyproject.toml`.

---
For questions or unclear conventions, check Vietnamese comments in code or ask for clarification.
