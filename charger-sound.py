import customtkinter as ctk
import win32gui
import win32api
import time
import threading
import winsound
import json
import os
import sys
from tkinter import filedialog
import winreg
import webbrowser

# Xác định thư mục cơ sở (hỗ trợ cả exe và script)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")

def set_startup(enabled):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ChargerSound"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(__file__)
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Startup toggle error: {e}")

def is_startup_enabled():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ChargerSound"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except:
        return False

# Dịch thuật
TRANSLATIONS = {
    "en": {
        "window_title": "Charger Sound Configurator",
        "header": "CHARGER SOUND",
        "plugged_title": "🔌 When Plugged",
        "unplugged_title": "🔋 When Unplugged",
        "status_active": "🟢 System is Active",
        "footer_tip": "Automatically scanning '.wav' files in folder",
        "empty_list": "Empty (add .wav files to 'wav' folder)",
        "no_audio": "No audio",
        "lang_name": "Tiếng Việt",
        "about_name": "About",
        "listener_start": "⚡ Listening for power events...",
        "plugged_log": "🔌 Plugged in",
        "unplugged_log": "🔋 On battery",
        "enabled_label": "Enable",
        "startup_label": "Run at Startup"
    },
    "vi": {
        "window_title": "Cấu hình Âm thanh Sạc Pin",
        "header": "ÂM THANH SẠC",
        "plugged_title": "🔌 Khi cắm sạc",
        "unplugged_title": "🔋 Khi rút sạc",
        "status_active": "🟢 Hệ thống đang hoạt động",
        "footer_tip": "Tự động quét tệp .wav trong thư mục 'wav'",
        "empty_list": "Trống (vui lòng thêm file .wav vào thư mục 'wav')",
        "no_audio": "Không có âm thanh",
        "lang_name": "English",
        "about_name": "Thông tin",
        "listener_start": "⚡ Đang lắng nghe sự kiện nguồn...",
        "plugged_log": "🔌 Đã kết nối sạc",
        "unplugged_log": "🔋 Đã ngắt sạc",
        "enabled_label": "Kích hoạt",
        "startup_label": "Khởi động cùng Windows"
    }
}

def load_settings():
    default_settings = {
        "plugged_sound": "wav/ahh.wav",
        "unplugged_sound": "wav/uhh.wav",
        "language": "en",
        "plugged_enabled": True,
        "unplugged_enabled": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
                return default_settings
        except Exception:
            pass
    return default_settings

def save_settings(settings_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, indent=4)

# Biến toàn cục
settings = load_settings()
last_state = None
last_trigger_time = 0

def play_sound(file_path):
    if not file_path:
        return
    # Xử lý đường dẫn tương đối
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DIR, file_path)
        
    if os.path.exists(file_path):
        try:
            winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as e:
            print(f"Error playing sound: {e}")

def trigger_action(plugged):
    global last_trigger_time
    now = time.time()
    if now - last_trigger_time < 1.5:
        return  # chống spam khi driver gửi nhiều event cùng lúc
        
    last_trigger_time = now
    lang = settings.get("language", "en")

    if plugged:
        print(TRANSLATIONS[lang]["plugged_log"])
        if settings.get("plugged_enabled", True):
            play_sound(settings.get("plugged_sound"))
    else:
        print(TRANSLATIONS[lang]["unplugged_log"])
        if settings.get("unplugged_enabled", True):
            play_sound(settings.get("unplugged_sound"))

def on_power_change():
    global last_state
    try:
        status = win32api.GetSystemPowerStatus()
        plugged = status['ACLineStatus'] == 1

        if last_state is None or plugged != last_state:
            last_state = plugged
            trigger_action(plugged)
    except Exception as e:
        print(f"Power check error: {e}")

def wndproc(hwnd, msg, wparam, lparam):
    WM_POWERBROADCAST = 0x218
    PBT_APMPOWERSTATUSCHANGE = 0xA
    if msg == WM_POWERBROADCAST:
        if wparam == PBT_APMPOWERSTATUSCHANGE:
            on_power_change()
    return 1

def start_power_listener():
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = wndproc
    wc.lpszClassName = "PowerListener"
    
    try:
        class_atom = win32gui.RegisterClass(wc)
        win32gui.CreateWindow(
            class_atom,
            "PowerListener",
            0,
            0, 0, 0, 0,
            0, 0, 0, None
        )
        lang = settings.get("language", "en")
        print(TRANSLATIONS[lang]["listener_start"])
        # Lấy trạng thái ban đầu
        on_power_change()
        win32gui.PumpMessages()
    except Exception as e:
        print(f"Listener error: {e}")

def get_wav_list():
    wav_dir = os.path.join(BASE_DIR, "wav")
    if not os.path.exists(wav_dir):
        os.makedirs(wav_dir)
        return []
    return [f for f in os.listdir(wav_dir) if f.lower().endswith(".wav")]

from PIL import Image, ImageDraw, ImageFont, ImageTk

class ChargeSoundApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # UI Elements dictionary for easy text update
        self.ui_elements = {}
        
        self.setup_ui()
        self.set_icon("🔋")
        self.update_translations()

    def set_icon(self, emoji):
        try:
            # Create a 64x64 image
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Use Windows Emoji Font
            try:
                font = ImageFont.truetype("seguiemj.ttf", 48)
            except:
                font = ImageFont.load_default()
                
            draw.text((32, 32), emoji, font=font, anchor="mm")
            
            photo = ImageTk.PhotoImage(img)
            self.iconphoto(True, photo)
            self._icon_ref = photo # Keep reference
        except Exception as e:
            print(f"Icon error: {e}")

    def setup_ui(self):
        self.geometry("480x380")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Top Bar for Language and Startup options
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=20, pady=(10, 0))

        # Startup toggle
        self.startup_cb = ctk.CTkCheckBox(
            self.top_bar, 
            text="Startup", 
            width=20, 
            checkbox_width=18, 
            checkbox_height=18,
            font=("Inter", 12),
            command=self.toggle_startup_reg
        )
        if is_startup_enabled():
            self.startup_cb.select()
        self.startup_cb.pack(side="left")

        self.lang_btn = ctk.CTkButton(
            self.top_bar, 
            text="Language", 
            width=100, 
            height=28,
            fg_color="#333",
            hover_color="#444",
            command=self.toggle_language
        )
        self.lang_btn.pack(side="right", padx=(5, 0))

        # About button
        self.about_btn = ctk.CTkButton(
            self.top_bar, 
            text="About", 
            width=70, 
            height=28,
            fg_color="#1a1a1a",
            border_width=1,
            border_color="#333",
            hover_color="#444",
            command=self.open_github
        )
        self.about_btn.pack(side="right")

        # Main frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # Header
        self.header = ctk.CTkLabel(
            self.main_frame, 
            text="CHARGER SOUND", 
            font=("Inter", 26, "bold"),
            text_color="#3b8ed0"
        )
        self.header.pack(pady=(10, 20))

        # Lấy danh sách tệp wav
        self.wav_files = get_wav_list()
        self.refresh_wav_list()

        # Plugged setting
        self.plugged_section = self.create_setting_section(
            "plugged_sound", 
            "plugged_enabled",
            "#3498db"
        )

        # Space
        ctk.CTkLabel(self.main_frame, text="", height=10).pack()

        # Unplugged setting
        self.unplugged_section = self.create_setting_section(
            "unplugged_sound", 
            "unplugged_enabled",
            "#e67e22"
        )

    def open_github(self):
        webbrowser.open_new_tab("https://github.com/mhqb365/charger-sound")

    def toggle_startup_reg(self):
        set_startup(self.startup_cb.get())

    def refresh_wav_list(self):
        self.wav_files = get_wav_list()
        lang = settings["language"]
        if not self.wav_files:
            self.wav_files = [TRANSLATIONS[lang]["empty_list"]]

    def update_translations(self):
        lang = settings["language"]
        t = TRANSLATIONS[lang]
        
        self.title(t["window_title"])
        self.header.configure(text=t["header"])
        self.lang_btn.configure(text=t["lang_name"])
        self.about_btn.configure(text=t["about_name"])
        self.startup_cb.configure(text=t["startup_label"])
        
        # Update section titles & checkboxes
        self.plugged_section["title_label"].configure(text=t["plugged_title"])
        self.plugged_section["checkbox"].configure(text=t["enabled_label"])
        
        self.unplugged_section["title_label"].configure(text=t["unplugged_title"])
        self.unplugged_section["checkbox"].configure(text=t["enabled_label"])
        
        # Update dropdowns if empty
        if not get_wav_list():
            new_vals = [t["empty_list"]]
            self.plugged_section["menu"].configure(values=new_vals)
            self.plugged_section["menu"].set(t["empty_list"])
            self.unplugged_section["menu"].configure(values=new_vals)
            self.unplugged_section["menu"].set(t["empty_list"])

    def toggle_language(self):
        new_lang = "vi" if settings["language"] == "en" else "en"
        settings["language"] = new_lang
        save_settings(settings)
        self.update_translations()

    def create_setting_section(self, key, enabled_key, accent_color):
        section_frame = ctk.CTkFrame(self.main_frame, fg_color="#1a1a1a", border_width=1, border_color="#333")
        section_frame.pack(fill="x", pady=5)

        # Header row with title and checkbox
        header_row = ctk.CTkFrame(section_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(12, 6))

        title_label = ctk.CTkLabel(
            header_row, 
            text="...", 
            font=("Inter", 15, "bold"),
            text_color=accent_color
        )
        title_label.pack(side="left")

        def toggle_enabled():
            settings[enabled_key] = checkbox.get()
            save_settings(settings)

        checkbox = ctk.CTkCheckBox(
            header_row, 
            text="...", 
            width=20, 
            checkbox_width=18, 
            checkbox_height=18,
            font=("Inter", 12),
            command=toggle_enabled
        )
        if settings.get(enabled_key, True):
            checkbox.select()
        else:
            checkbox.deselect()
        checkbox.pack(side="right")

        controls_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=(0, 12))

        # Xác định giá trị hiện tại (chỉ lấy tên file)
        current_val = settings[key]
        if os.path.isabs(current_val) or "/" in current_val or "\\" in current_val:
            current_val = os.path.basename(current_val)
        
        lang = settings["language"]
        if current_val not in self.wav_files:
            if self.wav_files and not "Empty" in self.wav_files[0] and not "Trống" in self.wav_files[0]:
                current_val = self.wav_files[0]
            else:
                current_val = TRANSLATIONS[lang]["no_audio"]

        def on_select(choice):
            if any(x in choice for x in ["Empty", "Trống", "No", "Không"]):
                return
            settings[key] = f"wav/{choice}"
            save_settings(settings)

        option_menu = ctk.CTkOptionMenu(
            controls_frame,
            values=self.wav_files,
            command=on_select,
            width=300,
            fg_color="#333",
            button_color="#444",
            button_hover_color="#555",
            dropdown_hover_color="#3b8ed0"
        )
        option_menu.set(current_val)
        option_menu.pack(side="left", padx=(0, 10))

        def test():
            selected = option_menu.get()
            if any(x in selected for x in ["Empty", "Trống", "No", "Không"]):
                return
            play_sound(f"wav/{selected}")

        test_btn = ctk.CTkButton(
            controls_frame, 
            text="▶", 
            width=38, 
            height=32,
            command=test,
            fg_color=accent_color,
            hover_color="#555"
        )
        test_btn.pack(side="right", padx=2)

        return {
            "title_label": title_label,
            "checkbox": checkbox,
            "menu": option_menu
        }

if __name__ == "__main__":
    # Khởi chạy thread listener
    thread = threading.Thread(target=start_power_listener, daemon=True)
    thread.start()

    # Chạy giao diện
    app = ChargeSoundApp()
    app.mainloop()