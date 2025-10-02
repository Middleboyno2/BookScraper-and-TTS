from bs4 import BeautifulSoup
import json
import time
from selenium.webdriver.common.by import By

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Books:
    def __init__(self, driver):
        self.driver = driver
        
    # lấy thông tin sách từ trang hiện tại  
    def get_ebook_data(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        books = []
        products = soup.select(".product-small")
        
        for item in products:
            title_tag = item.select_one(".product-title a")
            
            if title_tag:
                title = title_tag.text.strip()
                link = title_tag.get("href", "")
                
                # Lấy thông tin lượt xem và tải xuống
                views_tag = item.select_one(".tdk-product-loop-custom-product-meta .last-updated-date span")
                downloads_tag = item.select_one(".tdk-product-loop-custom-product-meta .version")
                
                views = views_tag.text.strip() if views_tag else "0"
                downloads = downloads_tag.text.strip() if downloads_tag else "0"
                
                # Lấy category
                category_tag = item.select_one(".category")
                category = category_tag.text.strip() if category_tag else "null"
                
                # Lấy ảnh (ưu tiên data-src, fallback src)
                img_tag = item.select_one("img")
                img_path = ""
                if img_tag:
                    img_path = img_tag.get("data-src") or img_tag.get("src") or ""
                
                books.append({
                    "title": title,
                    #"author": "",
                    "genre": category,
                    # "status": "",
                    "url": link,
                    "img_path": img_path,
                    "views": views,
                    "downloads": downloads
                })
        
        return books
    
    
    # Lấy thông tin phân trang từ ux-relay data
    def get_pagination_info(self):
        try:
            relay_element = self.driver.find_element(By.CSS_SELECTOR, '[data-flatsome-relay]')
            relay_data = json.loads(relay_element.get_attribute('data-flatsome-relay'))
            
            current_page = relay_data.get('currentPage', 1)
            total_pages = relay_data.get('totalPages', 1)
            
            return current_page, total_pages
        except:
            # Fallback: đếm từ pagination links
            try:
                page_numbers = self.driver.find_elements(By.CSS_SELECTOR, '.page-numbers .page-number')
                max_page = 1
                for elem in page_numbers:
                    if elem.text.strip().isdigit():
                        max_page = max(max_page, int(elem.text.strip()))
                return 1, max_page
            except:
                return 1, 1
            
            
    # Đóng các popup quảng cáo có thể xuất hiện        
    def close_popups_and_ads(self):
        try:
            # Đợi một chút để popup load
            time.sleep(2)
            
            # Danh sách các selector có thể là popup/ads
            popup_selectors = [
                # Popup close buttons
                'button[class*="close"]',
                'button[class*="dismiss"]', 
                '[class*="modal"] button',
                '[class*="popup"] button',
                '.close-button',
                '.btn-close',
                
                # Ad close buttons
                '[id*="close"]',
                '[class*="ad-close"]',
                '[aria-label*="close" i]',
                '[title*="close" i]',
                
                # Overlay elements
                '.overlay',
                '.modal-backdrop',
                '.popup-overlay'
            ]
            
            for selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            self.driver.execute_script("arguments[0].click();", element)
                            print(f"Đã đóng popup với selector: {selector}")
                            time.sleep(1)
                            break
                except:
                    continue
                    
            # Kiểm tra nếu có tab/window mới bị mở
            if len(self.driver.window_handles) > 1:
                print("Phát hiện tab mới, đóng và quay về tab chính...")
                main_window = self.driver.window_handles[0]
                for handle in self.driver.window_handles[1:]:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                self.driver.switch_to.window(main_window)
                
        except Exception as e:
            print(f"Lỗi khi xử lý popup: {str(e)}")
            
            
    def safe_click_next_page(self):
        # Click an toàn vào nút next page với xử lý popup
        try:
            # Đóng popup trước khi click
            self.close_popups_and_ads()
            
            # Tìm nút next
            next_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.next.page-number'))
            )
            
            # Scroll đến button và đợi
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
            time.sleep(5)
        
            # Lưu URL hiện tại để kiểm tra
            current_url = self.driver.current_url
            
            # Click bằng JavaScript để tránh các element che
            self.driver.execute_script("arguments[0].click();", next_button)
            print("Đã click nút Next")
            
            # Đợi AJAX load
            time.sleep(5)
            
            # Xử lý popup sau khi click
            self.close_popups_and_ads()
            
            # Kiểm tra xem có bị redirect không
            if self.driver.current_url != current_url:
                print(f"Phát hiện redirect từ {current_url} sang {self.driver.current_url}")
                self.driver.get(current_url)  # Quay về trang gốc
                time.sleep(5)
                return False
            
            # Đợi nội dung mới load
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.product-small'))
            )
            
            # Thêm delay để đảm bảo hoàn tất
            time.sleep(5)
            
            return True
            
        except Exception as e:
            print(f"Lỗi khi click next page: {str(e)}")
            self.close_popups_and_ads()
            return False