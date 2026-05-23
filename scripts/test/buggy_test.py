def compute_data():
    print("[SYSTEM] Bắt đầu tính toán dữ liệu...")
    
    # Lỗi cố ý: Cố gắng truy cập index ngoài giới hạn của mảng (IndexError)
    data_list = [1, 2, 3]
    value = data_list[5] 
    
    print(f"Giá trị tìm được: {value}")
    print("[SYSTEM] Tính toán hoàn tất!")

if __name__ == "__main__":
    compute_data()
