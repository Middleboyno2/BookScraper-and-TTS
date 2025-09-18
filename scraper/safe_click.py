import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from close_popups_and_ads import close_popups_and_ads

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