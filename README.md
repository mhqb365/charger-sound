# 🔌 Charger Sound Configurator

Một ứng dụng giúp bạn tùy chỉnh âm thanh mỗi khi cắm hoặc rút sạc máy tính Windows

![Charger Sound App Interface](charger-sound.png)

## ✨ Tính năng nổi bật

-   🎨 **Giao diện Hiện đại**: Sử dụng CustomTkinter với phong cách Dark Mode cao cấp
-   🔊 **Tùy chọn Âm thanh**: Chọn bất kỳ tệp `.wav` nào có sẵn trong thư mục `wav`
-   ▶️ **Nghe thử**: Tích hợp nút Play để bạn nghe thử âm thanh đã chọn
-   🌐 **Đa ngôn ngữ**: Hỗ trợ tiếng Anh (Mặc định) và tiếng Việt
-   🔌 **Bật/Tắt riêng biệt**: Có thể chọn chỉ phát âm thanh khi cắm sạc hoặc khi rút sạc hoặc cả hai
-   🚀 **Khởi động cùng Windows**: Tự động chạy ứng dụng khi bạn bật máy tính
-   ⚙️ **Tự động lưu**: Ghi nhớ mọi cài đặt của bạn vào tệp `settings.json`

## 🛠️ Hướng dẫn cài đặt (Chạy từ mã nguồn)

1.  **Clone dự án**:
    ```bash
    git clone https://github.com/mhqb365/charger-sound.git
    cd charger-sound
    ```

2.  **Cài đặt thư viện cần thiết**:
    ```bash
    pip install customtkinter Pillow pywin32
    ```

3.  **Chạy ứng dụng**:
    ```bash
    python charger-sound.py
    ```

## 📦 Hướng dẫn Build file .exe

Để tạo file `.exe` duy nhất để sử dụng mà không cần cài đặt Python, sử dụng PyInstaller:

```powershell
pyinstaller --noconfirm --onefile --windowed --name "ChargerSound" --collect-all customtkinter charger-sound.py
```

**Lưu ý sau khi Build:**
-   Copy file `ChargerSound.exe` từ thư mục `dist/` ra ngoài
-   Đảm bảo thư mục `wav/` (chứa các file âm thanh) và `settings.json` nằm cùng thư mục với file `.exe`

## 📂 Cấu trúc thư mục

-   `charger-sound.py`: Mã nguồn chính của ứng dụng
-   `wav/`: Thư mục chứa các tệp âm thanh `.wav`
-   `settings.json`: Tệp lưu trữ cấu hình người dùng
-   `ChargerSound.spec`: Tệp cấu hình cho PyInstaller
