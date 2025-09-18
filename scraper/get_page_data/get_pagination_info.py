import json
from selenium.webdriver.common.by import By


def get_pagination_info(driver):
    """Lấy thông tin phân trang từ ux-relay data"""
    try:
        relay_element = driver.find_element(By.CSS_SELECTOR, '[data-flatsome-relay]')
        relay_data = json.loads(relay_element.get_attribute('data-flatsome-relay'))
        
        current_page = relay_data.get('currentPage', 1)
        total_pages = relay_data.get('totalPages', 1)
        
        return current_page, total_pages
    except:
        # Fallback: đếm từ pagination links
        try:
            page_numbers = driver.find_elements(By.CSS_SELECTOR, '.page-numbers .page-number')
            max_page = 1
            for elem in page_numbers:
                if elem.text.strip().isdigit():
                    max_page = max(max_page, int(elem.text.strip()))
            return 1, max_page
        except:
            return 1, 1