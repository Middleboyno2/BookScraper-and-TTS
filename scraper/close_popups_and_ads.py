import time
from selenium.webdriver.common.by import By

def close_popups_and_ads(driver):
    # Đóng các popup quảng cáo có thể xuất hiện
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
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        driver.execute_script("arguments[0].click();", element)
                        print(f"Đã đóng popup với selector: {selector}")
                        time.sleep(1)
                        break
            except:
                continue
                
        # Kiểm tra nếu có tab/window mới bị mở
        if len(driver.window_handles) > 1:
            print("Phát hiện tab mới, đóng và quay về tab chính...")
            main_window = driver.window_handles[0]
            for handle in driver.window_handles[1:]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(main_window)
            
    except Exception as e:
        print(f"Lỗi khi xử lý popup: {str(e)}")