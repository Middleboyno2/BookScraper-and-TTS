import os
import pandas as pd
CSV_FILE = "data/books.csv"

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