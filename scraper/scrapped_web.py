from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

# Local imports
import setup_driver # setup_driver
import close_popups_and_ads # close_popups_and_ads 
from get_page_data import get_ebook_coming_soon_data, get_pagination_info, get_ebook_hot_data, get_ebook_new_data # get_pagination_info


CSV_FILE = "books.csv"



def safe_click_next_page(driver):
    # Click an toàn vào nút next page với xử lý popup
    try:
        # Đóng popup trước khi click
        close_popups_and_ads(driver)
        
        # Tìm nút next
        next_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.next.page-number'))
        )
        
        # Scroll đến button và đợi
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(5)
    
        # Lưu URL hiện tại để kiểm tra
        current_url = driver.current_url
        
        # Click bằng JavaScript để tránh các element che
        driver.execute_script("arguments[0].click();", next_button)
        print("Đã click nút Next")
        
        # Đợi AJAX load
        time.sleep(5)
        
        # Xử lý popup sau khi click
        close_popups_and_ads(driver)
        
        # Kiểm tra xem có bị redirect không
        if driver.current_url != current_url:
            print(f"Phát hiện redirect từ {current_url} sang {driver.current_url}")
            driver.get(current_url)  # Quay về trang gốc
            time.sleep(5)
            return False
        
        # Đợi nội dung mới load
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
        )
        
        # Thêm delay để đảm bảo hoàn tất
        time.sleep(5)
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi click next page: {str(e)}")
        close_popups_and_ads(driver)
        return False

def scrape_all_pages_selenium(url, max_pages=None):
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
            page_data = get_ebook_hot_data(driver)
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

def update_csv(new_data: pd.DataFrame):
    if new_data.empty:
        print("Không có dữ liệu mới để cập nhật")
        return
    
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        combined = new_data
        print("Tạo file CSV mới")
    else:
        try:
            old_data = pd.read_csv(CSV_FILE)
            print(f"Dữ liệu cũ: {len(old_data)} sách")
            combined = pd.concat([old_data, new_data]).drop_duplicates(subset=["title", "url"])
            print(f"Sau khi loại bỏ trùng lặp: {len(combined)} sách")
        except pd.errors.EmptyDataError:
            combined = new_data
            print("File CSV cũ trống, tạo mới")
    
    combined.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
    print(f"Đã lưu {len(combined)} sách vào {CSV_FILE}")

# cào dữ liệu
if __name__ == "__main__":
    url = "https://ebookvie.com/ebook-hot/"
    
    print("Bắt đầu cào dữ liệu với Selenium...")
    
    # Cào dữ liệu
    all_books_data = scrape_all_pages_selenium(
        url=url,
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