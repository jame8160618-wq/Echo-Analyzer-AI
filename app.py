import os
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from ocr_engine import get_raw_text
from core_logic import parse_panel_to_dict
from echo_evaluator import evaluate_echo_stats

app = FastAPI()

# 1. 建立儲存圖片的資料夾
SAVE_DIR = "static/echoes"
os.makedirs(SAVE_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 功能一：總面板分析 ---
@app.post("/analyze-panel")
async def analyze_panel(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    lines = get_raw_text(img)
    result = parse_panel_to_dict(lines)
    return {"status": "success", "type": "panel", "data": result}

# --- 功能二：聲骸評分與圖示紀錄 (修正座標邏輯) ---
@app.post("/analyze-echo")
async def analyze_echo(file: UploadFile = File(...), slot: int = Form(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    h, w, _ = img.shape

    # --- 針對全螢幕截圖 (圖1) 的聲骸列表裁切邏輯 ---
    # 橫向範圍：左側邊欄圓圈區域 (約 1% 到 8% 寬度處)
    left = int(w * 0.01)   
    right = int(w * 0.08)

    # 縱向範圍：
    # 由於 Slot 1 (Cost 4) 圖示較大且位置較高，其中心點約在 20% 處
    # Slot 2-5 間距較固定，Slot 2 中心約在 37% 處
    if slot == 1:
        y_center = 0.195  # 第一格中心
        half_height = 0.053 # 第一格較大，給予較大的半徑
    else:
        # slot 2 開始的基準點與間距 (12.8% 是平均間距)
        top_start_others = 0.34
        slot_gap = 0.10
        y_center = top_start_others + (slot - 2) * slot_gap
        half_height = 0.045 # 後續格子較小

    y_start = int(h * (y_center - half_height))
    y_end = int(h * (y_center + half_height))
    
    # 執行裁切
    icon_img = img[max(0, y_start):min(h, y_end), max(0, left):min(w, right)]
    
    if icon_img.size > 0:
        icon_path = f"{SAVE_DIR}/slot_{slot}.png"
        cv2.imwrite(icon_path, icon_img)

    # --- OCR 解析：解析全螢幕右側的數值區域 ---
    # 注意：OCR 應該掃描全圖，但核心數值通常在右側
    lines = get_raw_text(img)
    result = evaluate_echo_stats(lines)
    
    return {
        "status": "success",
        "slot": slot,
        "icon_url": f"http://127.0.0.1:8000/static/echoes/slot_{slot}.png",
        "data": result
    }