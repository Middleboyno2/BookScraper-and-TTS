import os
import csv
import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path="url.env")

class CSV_DATA_BOOK:
    CSV_FILE = os.getenv("data_book_path")  
    
    # cập nhật dữ liệu vào CSV
    def update_csv(self, new_data: pd.DataFrame):

        if new_data.empty:
            print("Không có dữ liệu mới để cập nhật")
            return
        
        if not os.path.exists(self.CSV_FILE) or os.path.getsize(self.CSV_FILE) == 0:
            combined = new_data
            print("Tạo file CSV mới")
        else:
            try:
                old_data = pd.read_csv(self.CSV_FILE)
                print(f"Dữ liệu cũ: {len(old_data)} sách")
                combined = pd.concat([old_data, new_data]).drop_duplicates(subset=["title", "url"])
                print(f"Sau khi loại bỏ trùng lặp: {len(combined)} sách")
            except pd.errors.EmptyDataError:
                combined = new_data
                print("File CSV cũ trống, tạo mới")
        
        combined.to_csv(self.CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"Đã lưu {len(combined)} sách vào {self.CSV_FILE}")
        
    # lấy dữ liệu từ CSV
    def get_data(self) -> list:
        if os.path.exists(self.CSV_FILE) and os.path.getsize(self.CSV_FILE) > 0:
            books = []
            with open(self.CSV_FILE, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    books.append(row)
            return books
        else:
            print("File CSV không tồn tại hoặc trống")
            return books