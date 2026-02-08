import mss
import pygetwindow as gw
from pynput import keyboard
import requests
import io
import time

# 配置 API 位址
API_URL = "http://127.0.0.1:8000/analyze-echo"

def capture_and_send(slot):
    try:
        # 1. 尋找遊戲視窗
        windows = gw.getWindowsWithTitle("鳴潮")
        if not windows:
            print("❌ 找不到遊戲視窗！")
            return
        win = windows[0]
        
        # 2. 截圖
        with mss.mss() as sct:
            monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}
            sct_img = sct.grab(monitor)
            
            # 轉為 API 接受的檔案格式
            import PIL.Image as Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

        # 3. 發送給 API
        print(f"🚀 正在發送 Slot {slot} 的數據...")
        files = {'file': ('screenshot.png', img_byte_arr, 'image/png')}
        data = {'slot': slot}
        response = requests.post(API_URL, files=files, data=data)
        
        if response.status_code == 200:
            print(f"✅ Slot {slot} 同步成功！網頁應已更新。")
        else:
            print(f"⚠️ API 回傳錯誤: {response.text}")

    except Exception as e:
        print(f"🔴 發生錯誤: {e}")

def on_press(key):
    # F1 - F5 對應
    if key == keyboard.Key.f1: capture_and_send(1)
    elif key == keyboard.Key.f2: capture_and_send(2)
    elif key == keyboard.Key.f3: capture_and_send(3)
    elif key == keyboard.Key.f4: capture_and_send(4)
    elif key == keyboard.Key.f5: capture_and_send(5)

print("📡 客戶端已啟動！請保持 API 開啟。")
print("⌨️ 在遊戲內按下 [F1 - F5] 即可自動同步聲骸數據...")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()