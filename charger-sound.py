import customtkinter as ctk
import win32gui
import win32api
import time
import threading
import winsound
import json
import os
import sys
import ctypes
from tkinter import filedialog
import winreg
import webbrowser
from PIL import Image, ImageDraw, ImageFont, ImageTk
import psutil


try:
    import pystray
    from pystray import MenuItem as item
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

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
                full_command = f'"{exe_path}" --minimized'
            else:
                exe_path = os.path.abspath(__file__)
                full_command = f'"{sys.executable}" "{exe_path}" --minimized'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, full_command)
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
        "startup_label": "Run at Startup",
        "tray_show": "Show Window",
        "tray_stats": "Show System Stats",
        "tray_exit": "Exit"
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
        "startup_label": "Khởi động cùng Windows",
        "tray_show": "Hiện cửa sổ",
        "tray_stats": "Hiện thống kê hệ thống",
        "tray_exit": "Thoát"
    }
}

def load_settings():
    default_settings = {
        "plugged_sound": "wav/ahh.wav",
        "unplugged_sound": "wav/uhh.wav",
        "language": "en",
        "plugged_enabled": True,
        "unplugged_enabled": True,
        "show_stats": True
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

class StatsOverlay(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Stats")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.7) # Độ mờ thanh thoát hơn (70%)
        
        self.configure(fg_color="#1e1e1e") # Nền tối sang trọng
        
        # UI Elements (Bỏ bo góc và viền)
        self.container = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0, border_width=0)
        self.container.pack(fill="both", expand=True)
        
        self.label = ctk.CTkLabel(
            self.container, 
            text="Loading...", 
            font=("Consolas", 12, "bold"),
            text_color="#00ff00", # Màu xanh neon cho bắt mắt
            justify="left"
        )
        self.label.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Dragging functionality
        self.label.bind("<Button-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.do_drag)
        self.container.bind("<Button-1>", self.start_drag)
        self.container.bind("<B1-Motion>", self.do_drag)
        
        # Position at bottom-right corner of screen
        self.set_default_position()
        self.force_topmost()
        
    def force_topmost(self):
        try:
            # Force window to be at the very top using Win32 API
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            # HWND_TOPMOST = -1, SWP_NOMOVE = 2, SWP_NOSIZE = 1, SWP_SHOWWINDOW = 0x40
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 2 | 1 | 0x40)
        except:
            pass

    def start_drag(self, event):
        self.x = event.x
        self.y = event.y

    def do_drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def set_default_position(self):
        try:
            # Tìm Handle của Taskbar để tính toán ranh giới
            shell_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            taskbar_rect = win32gui.GetWindowRect(shell_hwnd)
            
            # Kích thước màn hình
            screen_width = self.winfo_screenwidth()
            
            # Kích thước Widget
            width = 240
            height = 50
            
            # Toạ độ X: Góc bên phải
            x = screen_width
            
            # Toạ độ Y: Nằm ngay TRÊN thanh Taskbar (taskbar_rect[1] là đỉnh của Taskbar)
            y = taskbar_rect[1] - (height + 15)
            
            self.geometry(f"{width}x{height}+{x}+{y}")
        except:
            # Dự phòng
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"240x50+{sw-250}+{sh-100}")

    def update_stats(self, text):
        self.label.configure(text=text)
        # Nhắc lại việc luôn nằm trên cùng mỗi khi cập nhật để không bị Taskbar đè
        self.lift()
        self.attributes("-topmost", True)




def get_wav_list():
    wav_dir = os.path.join(BASE_DIR, "wav")
    if not os.path.exists(wav_dir):
        os.makedirs(wav_dir)
        return []
    return [f for f in os.listdir(wav_dir) if f.lower().endswith(".wav")]

class ChargeSoundApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.tray_icon = None
        
        # UI Elements dictionary
        self.ui_elements = {}
        
        self.setup_ui()
        self.update_translations()
        
        # Khởi tạo Overlay trước tiên để tránh lỗi Race Condition
        self.overlay = StatsOverlay(self)
        if not settings.get("show_stats", True):
            self.overlay.withdraw()
            
        self.setup_tray()



        # Xử lý đóng cửa sổ và khởi động thu nhỏ
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        if "--minimized" in sys.argv:
            self.after(150, self.withdraw)

    def get_icon_image(self, emoji, stats=None):
        # Nếu có thông số stats, vẽ icon động
        if stats:
            cpu, ram, disk, up, down = stats
            img = Image.new('RGBA', (64, 64), (30, 30, 30, 255))
            draw = ImageDraw.Draw(img)
            
            # Vẽ background bars
            draw.rectangle([0, 0, 64, 64], outline=(60, 60, 60), width=1)
            
            # Chọn font (ưu tiên font hệ thống nhỏ)
            try:
                font = ImageFont.truetype("arial.ttf", 22)
                font_small = ImageFont.truetype("arial.ttf", 18)
            except:
                font = ImageFont.load_default()
                font_small = font

            # Vẽ CPU và RAM (2 thông số quan trọng nhất trên icon)
            # Chia làm 2 hàng
            draw.text((32, 16), f"C:{int(cpu)}", fill="#3b8ed0", font=font, anchor="mm")
            draw.text((32, 45), f"R:{int(ram)}", fill="#e67e22", font=font, anchor="mm")
            
            # Thêm vạch báo Disk ở cạnh trái
            disk_h = int((disk / 100) * 64)
            draw.rectangle([0, 64-disk_h, 4, 64], fill="#2ecc71")
            
            return img

        # Icon mặc định (từ file hoặc emoji)
        search_paths = []
        if getattr(sys, 'frozen', False):
            search_paths.append(os.path.join(getattr(sys, '_MEIPASS', ''), "icon.png"))
        
        try:
            current_script_dir = os.path.dirname(os.path.realpath(__file__))
            search_paths.append(os.path.join(current_script_dir, "icon.png"))
        except:
            pass
            
        search_paths.append(os.path.join(BASE_DIR, "icon.png"))
        search_paths.extend(["icon.png", "charger-sound.png"])
        
        icon_img = None
        for path in search_paths:
            if path and os.path.exists(path):
                try:
                    icon_img = Image.open(path)
                    break
                except Exception:
                    continue

        if icon_img: return icon_img
                
        try:
            img = Image.new('RGBA', (64, 64), (59, 142, 208, 255))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("seguiemj.ttf", 40)
            except:
                font = ImageFont.load_default()
            draw.text((32, 32), emoji, font=font, anchor="mm", fill="white")
            return img
        except:
            return Image.new('RGBA', (64, 64), (59, 142, 208, 255))

    def format_speed(self, b_per_s):
        if b_per_s < 1024: return f"{b_per_s:.0f}B/s"
        if b_per_s < 1024*1024: return f"{b_per_s/1024:.1f}K/s"
        return f"{b_per_s/(1024*1024):.1f}M/s"

    def start_stats_monitor(self):
        last_net_io = psutil.net_io_counters()
        last_time = time.time()

        def stats_loop():
            nonlocal last_net_io, last_time
            while True:
                if self.tray_icon:
                    try:
                        # Lấy thông số
                        cpu = psutil.cpu_percent(interval=None)
                        ram = psutil.virtual_memory().percent
                        disk = psutil.disk_usage('/').percent
                        
                        # Tính tốc độ mạng
                        now = time.time()
                        net_io = psutil.net_io_counters()
                        dt = now - last_time
                        up_speed = (net_io.bytes_sent - last_net_io.bytes_sent) / dt
                        down_speed = (net_io.bytes_recv - last_net_io.bytes_recv) / dt
                        
                        last_net_io = net_io
                        last_time = now

                        # Cập nhật Tooltip
                        status_text = (
                            f"CPU: {cpu}% | RAM: {ram}% | Disk: {disk}%\n"
                            f"↑ {self.format_speed(up_speed)} | ↓ {self.format_speed(down_speed)}"
                        )
                        self.tray_icon.title = status_text
                        
                        # Cập nhật Overlay (Taskbar Widget)
                        if settings.get("show_stats", True):
                            overlay_text = (
                                f"CPU:{int(cpu)}% | RAM:{int(ram)}% | Disk:{int(disk)}%\n"
                                f"Up:{self.format_speed(up_speed)} | Down:{self.format_speed(down_speed)}"
                            )
                            self.overlay.update_stats(overlay_text)
                        
                        # Cập nhật Icon (vẽ thông số)
                        self.tray_icon.image = self.get_icon_image("🔋", stats=(cpu, ram, disk, up_speed, down_speed))

                        
                    except Exception as e:
                        print(f"Stats Error: {e}")
                
                time.sleep(2)

        threading.Thread(target=stats_loop, daemon=True).start()


    def setup_tray(self):
        if not HAS_PYSTRAY: return
            
        def on_show(icon, item):
            self.show_window()

        def on_toggle_stats(icon, item):
            new_state = not settings.get("show_stats", True)
            settings["show_stats"] = new_state
            save_settings(settings)
            if new_state:
                self.overlay.deiconify()
                self.overlay.lift()
                self.overlay.force_topmost()
            else:
                self.overlay.withdraw()

        def on_exit(icon, item):
            self.quit_app()

        menu = pystray.Menu(
            item(lambda t: TRANSLATIONS[settings["language"]]["tray_show"], on_show, default=True),
            item(
                lambda t: TRANSLATIONS[settings["language"]]["tray_stats"], 
                on_toggle_stats,
                checked=lambda item: settings.get("show_stats", True)
            ),
            item(lambda t: TRANSLATIONS[settings["language"]]["about_name"], lambda: self.open_github()),
            pystray.Menu.SEPARATOR,
            item(lambda t: TRANSLATIONS[settings["language"]]["tray_exit"], on_exit)
        )
        
        self.tray_icon = pystray.Icon("ChargerSound", self.get_icon_image("🔋"), "Charger Sound", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # Bắt đầu luồng giám sát hệ thống
        self.start_stats_monitor()


    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        os._exit(0)

    def setup_ui(self):
        self.geometry("480x380")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Top Bar
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

        # Wav files
        self.wav_files = get_wav_list()
        self.refresh_wav_list()

        # Sections
        self.plugged_section = self.create_setting_section("plugged_sound", "plugged_enabled", "#3498db")
        ctk.CTkLabel(self.main_frame, text="", height=10).pack()
        self.unplugged_section = self.create_setting_section("unplugged_sound", "unplugged_enabled", "#e67e22")

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
        self.plugged_section["title_label"].configure(text=t["plugged_title"])
        self.plugged_section["checkbox"].configure(text=t["enabled_label"])
        self.unplugged_section["title_label"].configure(text=t["unplugged_title"])
        self.unplugged_section["checkbox"].configure(text=t["enabled_label"])

    def toggle_language(self):
        new_lang = "vi" if settings["language"] == "en" else "en"
        settings["language"] = new_lang
        save_settings(settings)
        self.update_translations()

    def create_setting_section(self, key, enabled_key, accent_color):
        section_frame = ctk.CTkFrame(self.main_frame, fg_color="#1a1a1a", border_width=1, border_color="#333")
        section_frame.pack(fill="x", pady=5)
        header_row = ctk.CTkFrame(section_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(12, 6))
        
        title_label = ctk.CTkLabel(header_row, text="...", font=("Inter", 15, "bold"), text_color=accent_color)
        title_label.pack(side="left")

        def toggle_enabled():
            settings[enabled_key] = checkbox.get()
            save_settings(settings)

        checkbox = ctk.CTkCheckBox(header_row, text="...", width=20, checkbox_width=18, checkbox_height=18, font=("Inter", 12), command=toggle_enabled)
        if settings.get(enabled_key, True): checkbox.select()
        else: checkbox.deselect()
        checkbox.pack(side="right")

        controls_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=(0, 12))

        current_val = settings[key]
        if os.path.isabs(current_val) or "/" in current_val or "\\" in current_val:
            current_val = os.path.basename(current_val)
        
        if current_val not in self.wav_files:
            if self.wav_files and not "Empty" in self.wav_files[0] and not "Trống" in self.wav_files[0]:
                current_val = self.wav_files[0]
            else:
                current_val = TRANSLATIONS[settings["language"]]["no_audio"]

        def on_select(choice):
            if any(x in choice for x in ["Empty", "Trống", "No", "Không"]): return
            settings[key] = f"wav/{choice}"
            save_settings(settings)

        option_menu = ctk.CTkOptionMenu(controls_frame, values=self.wav_files, command=on_select, width=300, fg_color="#333", button_color="#444")
        option_menu.set(current_val)
        option_menu.pack(side="left", padx=(0, 10))

        def test():
            selected = option_menu.get()
            if any(x in selected for x in ["Empty", "Trống", "No", "Không"]): return
            play_sound(f"wav/{selected}")

        test_btn = ctk.CTkButton(controls_frame, text="▶", width=38, height=32, command=test, fg_color=accent_color)
        test_btn.pack(side="right", padx=2)

        return {"title_label": title_label, "checkbox": checkbox, "menu": option_menu}

if __name__ == "__main__":
    threading.Thread(target=start_power_listener, daemon=True).start()
    app = ChargeSoundApp()
    app.mainloop()