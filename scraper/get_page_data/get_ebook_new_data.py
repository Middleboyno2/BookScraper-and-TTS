from bs4 import BeautifulSoup


# lấy thông tin sách từ ebook-moi
def get_ebook_new_data(driver):
    """Trích xuất dữ liệu từ trang hiện tại"""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
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
            category = category_tag.text.strip() if category_tag else "Hot"
            
            books.append({
                "title": title,
                "author": "",
                "genre": category,
                "status": "",
                "url": link,
                "file_path": "",
                "views": views,
                "downloads": downloads
            })
    
    return books