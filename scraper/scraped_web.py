from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

# Local imports
from setup_driver import setup_driver # setup_driver
from update_csv import update_csv # update_csv
from safe_click import safe_click_next_page # safe_click_next_page
from get_page_data.get_ebook_coming_soon_data import get_ebook_coming_soon_data
from get_page_data.get_pagination_info import get_pagination_info
from get_page_data.get_ebook_hot_data import get_ebook_hot_data
from get_page_data.get_ebook_new_data import get_ebook_new_data



CSV_FILE = "data/books.csv"

def scrape_all_pages_selenium(url,func, max_pages=None):
    # Cào tất cả trang sử dụng Selenium
    driver = setup_driver(headless=False)  # Set False để xem quá trình
    all_books = []
    
    try:
        print(f"Đang truy cập: {url}")
        driver.get(url)
        
        # Đợi trang load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
        )
        
        current_page, total_pages = get_pagination_info(driver)
        print(f"Phát hiện {total_pages} trang")
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
            print(f"Giới hạn cào {max_pages} trang")
        
        page_count = 0
        
        while page_count < total_pages:
            page_count += 1
            current_page, _ = get_pagination_info(driver)
            
            print(f"Đang cào trang {current_page}...")
            
            # Lấy dữ liệu trang hiện tại
            page_data = func(driver)
            all_books.extend(page_data)
            
            print(f"Đã cào {len(page_data)} sách từ trang {current_page}")
            
            # Nếu chưa đến trang cuối thì click next
            if page_count < total_pages:
                if not safe_click_next_page(driver):
                    print("Không thể chuyển sang trang tiếp theo hoặc bị redirect")
                    break
                    
                # Kiểm tra lại pagination sau khi chuyển trang
                time.sleep(2)
                new_current, _ = get_pagination_info(driver)
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
    
    # Cào dữ liệu
    all_books_data = scrape_all_pages_selenium(
        url=url,
        func=get_ebook_coming_soon_data,
        # max_pages=None 
    )
    
    # Cập nhật CSV
    update_csv(all_books_data)
    
    # Thống kê
    if os.path.exists(CSV_FILE):
        final_data = pd.read_csv(CSV_FILE)
        print(f"\nThống kê cuối cùng:")
        print(f"- Tổng số sách: {len(final_data)}")
        if 'genre' in final_data.columns:
            print(f"- Các thể loại: {final_data['genre'].nunique()} loại")