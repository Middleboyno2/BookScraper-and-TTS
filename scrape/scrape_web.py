from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
from dotenv import load_dotenv

# Local imports
from scrape.setup_driver import setup_driver
from scrape.book_csv import CSV_DATA_BOOK # update_csv
from scrape.books import Books


load_dotenv(dotenv_path="url.env")
class Scrape:
    @staticmethod
    def scrape_all_pages_selenium(url):
        # Cào tất cả trang sử dụng Selenium
        driver = setup_driver(headless=False)  # Set False để xem quá trình
        all_books = []
        max_pages = None
        
        try:
            print(f"Đang truy cập: {url}")
            driver.get(url)
            scrape = Books(driver)
            # Đợi trang load
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
            )
            
            current_page, total_pages = scrape.get_pagination_info()
            print(f"Phát hiện {total_pages} trang")
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
                print(f"Giới hạn cào {max_pages} trang")
            
            page_count = 0
            
            while page_count < total_pages:
                page_count += 1
                current_page, _ = scrape.get_pagination_info()
                
                print(f"Đang cào trang {current_page}...")
                
                # Lấy dữ liệu trang hiện tại
                page_data = scrape.get_ebook_data()
                all_books.extend(page_data)
                
                print(f"Đã cào {len(page_data)} sách từ trang {current_page}")
                
                # Nếu chưa đến trang cuối thì click next
                if page_count < total_pages:
                    if not scrape.safe_click_next_page():
                        print("Không thể chuyển sang trang tiếp theo hoặc bị redirect")
                        break
                        
                    # Kiểm tra lại pagination sau khi chuyển trang
                    time.sleep(2)
                    new_current, _ = scrape.get_pagination_info()
                    if new_current <= current_page:
                        print("Phát hiện không chuyển trang được, dừng lại")
                        break
            
            print(f"\nTổng cộng đã cào {len(all_books)} sách từ {page_count} trang")
            
        finally:
            driver.quit()
        
        return pd.DataFrame(all_books)


# cào dữ liệu
if __name__ == "__main__":
    url = "https://ebookvie.com/ebook-hot/"
    
    print("Bắt đầu cào dữ liệu với Selenium...")
    scraper = Scrape()
    csv = CSV_DATA_BOOK()
    
    # Cào dữ liệu
    all_books_data = scraper.scrape_all_pages_selenium(
        url=os.getenv("NEW_BOOK_URL"),
    )
    
    # Cập nhật CSV
    csv.update_csv(all_books_data)
    
    # Thống kê
    if os.path.exists(os.getenv("data_book_path")):
        final_data = pd.read_csv(os.getenv("data_book_path"))
        print(f"\nThống kê cuối cùng:")
        print(f"- Tổng số sách: {len(final_data)}")
        if 'genre' in final_data.columns:
            print(f"- Các thể loại: {final_data['genre'].nunique()} loại")