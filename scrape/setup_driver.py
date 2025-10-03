from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver(headless=True):
    """Thiết lập Chrome driver với chặn quảng cáo và popup"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    
    # Các tùy chọn bảo mật và hiệu suất
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Chặn các loại nội dung có thể gây rắc rối
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    # chrome_options.add_argument("--disable-images")  # Tắt hình ảnh để tăng tốc
    
    # Chặn popup và redirect
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--block-new-web-contents")
    
    # Thêm user agent thực tế
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Tắt JavaScript không cần thiết (gây quảng cáo)
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,  # Chặn thông báo
            "media_stream": 2,   # Chặn camera/mic
            "geolocation": 2,    # Chặn vị trí
        },
        # "profile.managed_default_content_settings": {
        #     "images": 2  # Chặn hình ảnh
        # }
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Thiết lập timeout để tránh chờ lâu
    driver.set_page_load_timeout(60)
    
    return driver