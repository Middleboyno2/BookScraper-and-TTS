from api.main import auto_update_books_data
import torch

if __name__ == "__main__":
    # Chạy thử ngay 1 lần
    # auto_update_books_data()
    

    print(torch.cuda.is_available())   # True
    print(torch.cuda.get_device_name(0))  
    
    