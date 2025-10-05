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
    def scrape_all_pages_selenium(self, url):
        # Cào tất cả trang sử dụng Selenium
        driver = setup_driver(headless=False)  # Set False để xem quá trình
        all_books = []
        
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
    
    
    # Dành cho các trang có pagination đơn giản
    def scrape_all_pages_selenium_2(self, url):
        driver = setup_driver(headless=False)  # Set False để xem quá trình
        all_books = []

        try:
            print(f"Đang truy cập: {url}")
            driver.get(url)
            scrape = Books(driver)

            # Đợi trang load
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
            )

            # Lấy thông tin tổng số trang
            current_page, total_pages = scrape.get_pagination_info()
            print(f"Phát hiện {total_pages} trang")

            # Loop qua từng page theo URL /page/{n}/
            for page in range(1, total_pages + 1):
                if page == 1:
                    page_url = url  # trang đầu
                else:
                    if url.endswith("/"):
                        page_url = f"{url}page/{page}/"
                    else:
                        page_url = f"{url}/page/{page}/"

                print(f"\nĐang cào trang {page}: {page_url}")
                driver.get(page_url)

                # Đợi load sản phẩm
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
                    )
                except Exception:
                    print(f"Trang {page} không load được, bỏ qua.")
                    continue

                page_data = scrape.get_ebook_data()
                all_books.extend(page_data)

                print(f"Đã cào {len(page_data)} sách từ trang {page}")
                time.sleep(5)  # tránh bị ban IP

            print(f"\nTổng cộng đã cào {len(all_books)} sách từ {total_pages} trang")

        finally:
            driver.quit()
        
        df = pd.DataFrame(all_books)

        # Xóa trùng theo toàn bộ cột
        df = df.drop_duplicates()

        # check trùng theo "url" (link ebook) thôi:
        df = df.drop_duplicates(subset=["title"], keep="first")

        return df




# cào dữ liệu
# if __name__ == "__main__":
#     url = "https://ebookvie.com/ebook-hot/"
    
#     print("Bắt đầu cào dữ liệu với Selenium...")
#     scraper = Scrape()
#     csv = CSV_DATA_BOOK()
    
#     # Cào dữ liệu
#     all_books_data = scraper.scrape_all_pages_selenium(
#         url=os.getenv("NEW_BOOK_URL"),
#     )
    
#     # Cập nhật CSV
#     csv.update_csv(csv_file= os.getenv("data_book_path"),new_data = all_books_data)
    
#     # Thống kê
#     if os.path.exists(os.getenv("data_book_path")):
#         final_data = pd.read_csv(os.getenv("data_book_path"))
#         print(f"\nThống kê cuối cùng:")
#         print(f"- Tổng số sách: {len(final_data)}")
#         if 'genre' in final_data.columns:
#             print(f"- Các thể loại: {final_data['genre'].nunique()} loại")