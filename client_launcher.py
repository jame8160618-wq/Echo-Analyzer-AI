# client_launcher.py
import mss, cv2, requests
from pynput import keyboard
# ... (原本截圖視窗的 logic)

def on_press(key):
    if key == keyboard.Key.f1: send_to_api(1)
    # ... 到 f5
    if key == keyboard.Key.f8: send_to_api("panel")

def send_to_api(mode):
    # 1. 執行原本的 MSS 截圖 (抓取聲骸區域或全螢幕)
    # 2. 將圖片存成 Bytes
    # 3. 呼叫你的 API：
    #    if mode == "panel": url = "/analyze-panel"
    #    else: url = "/analyze-echo"
    #    requests.post(url, files={"file": img_bytes})