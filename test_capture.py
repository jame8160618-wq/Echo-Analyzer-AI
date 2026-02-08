import mss
import pygetwindow as gw
from pynput import keyboard
from PIL import Image
from paddleocr import PaddleOCR
import re
import cv2
import numpy as np
import time
import re

# ==========================================
# 【使用者自定義區塊】
# ==========================================
# 5 個聲骸槽位
echo_slots = {i: {"暴擊率": 0, "暴擊傷害": 0, "攻擊百分比": 0, "固定攻擊": 0, "分數": 0} for i in range(1, 6)}

# 角色最終面板 (掃描結果)
char_panel = {
    "攻擊": 0, "暴擊": 0, "暴擊傷害": 0,
    "屬性加成": 0, "普攻加成": 0, "重擊加成": 0,
    "技能加成": 0, "解放加成": 0
}
DAMAGE_DISTRIBUTION = {
    "普攻": 0.20,
    "重擊": 0.20,
    "共鳴技能": 0.20,
    "共鳴解放": 0.20,
    "其他": 0.20
}

WEIGHTS = {
    "crit_rate": 2.0,   # 暴擊 1% = 2分
    "crit_dmg": 1.0,    # 暴傷 1% = 1分
    "atk_percent": 0.5  # 攻擊 1% = 0.5分
}
# ==========================================

# 初始化 OCR
ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
echo_list = []
saved_builds = {}  # <--- 修正：初始化方案儲存空間

def parse_panel_scrolling(lines):
    global char_panel
    found_this_time = []
    
    # 1. 預處理：極端錯字修正，並過濾掉干擾字符
    clean_lines = []
    for l in lines:
        c = l.replace(" ", "").replace("擎", "擊").replace("撃", "擊").replace("挚", "擊")
        c = c.replace("伤害", "傷害").replace("共鸣", "共鳴")
        clean_lines.append(c)

    # 2. 開始跨行解析
    for i in range(len(clean_lines)):
        line = clean_lines[i]
        
        # --- A. 處理攻擊力 (找「攻擊」的下一行) ---
        if "攻" in line or "擊" in line:
            # 檢查當前行或下一行是否有 + 號
            target_line = ""
            if "+" in line: target_line = line
            elif i+1 < len(clean_lines) and "+" in clean_lines[i+1]:
                target_line = clean_lines[i+1]
            
            if target_line:
                nums = re.findall(r"(\d+)", target_line)
                if len(nums) >= 2:
                    char_panel["攻擊"] = int(nums[0]) + int(nums[1])
                    found_this_time.append(f"攻擊({char_panel['攻擊']})")

        # 提取數字的通用工具 (抓取當前行或下一行的數字)
        def get_nearest_val(index):
            # 先找當前行
            nums = re.findall(r"(\d+\.?\d*)", clean_lines[index])
            if nums: return float(nums[-1])
            # 若無，找下一行
            if index + 1 < len(clean_lines):
                nums_next = re.findall(r"(\d+\.?\d*)", clean_lines[index+1])
                if nums_next: return float(nums_next[0])
            return None

        # --- B. 雙暴與百分比加成 (處理跨行) ---
        if "暴" in line:
            val = get_nearest_val(i)
            if val is not None:
                if "傷" in line or "害" in line:
                    char_panel["暴擊傷害"] = val
                    found_this_time.append("暴傷")
                else:
                    char_panel["暴擊"] = val
                    found_this_time.append("暴擊")

        elif "普" in line:
            val = get_nearest_val(i)
            if val is not None: char_panel["普攻加成"] = val; found_this_time.append("普攻")
            
        elif "重" in line:
            val = get_nearest_val(i)
            if val is not None: char_panel["重擊加成"] = val; found_this_time.append("重擊")

        elif "技能" in line or ("技" in line and "聲" not in line):
            val = get_nearest_val(i)
            if val is not None: char_panel["技能加成"] = val; found_this_time.append("技能")

        elif "解放" in line or "解" in line:
            val = get_nearest_val(i)
            if val is not None: char_panel["解放加成"] = val; found_this_time.append("解放")

        elif "加成" in line or "傷害" in line:
            # 屬性傷排除法
            exclude = ["普", "重", "技", "解", "效率", "防", "生", "抗", "能量"]
            if not any(k in line for k in exclude):
                val = get_nearest_val(i)
                if val is not None:
                    if val > char_panel.get("屬性加成", 0) or any(attr in line for attr in ["物理", "冷凝", "熱熔", "導電", "氣動", "湮滅"]):
                        char_panel["屬性加成"] = val
                        found_this_time.append("屬性")

    print(f"📊 本次掃描成功更新: {', '.join(found_this_time) if found_this_time else '完全沒抓到'}")

def capture_full_panel():
    try:
        win = gw.getWindowsWithTitle("鳴潮")[0]
        win.activate()
        time.sleep(0.2) # 給視窗一點點反應時間
        
        with mss.mss() as sct:
            monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}
            img_sct = sct.grab(monitor)
            img = Image.frombytes("RGB", img_sct.size, img_sct.bgra, "raw", "BGRX")
            
            w, h = img.size
            cropped = img.crop((int(w * 0.15), int(h * 0.10), int(w * 0.95), int(h * 0.90)))
            
            # --- 原色邏輯 + 銳化處理 ---
            cv_img = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
            cv_img = cv2.resize(cv_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # 增加一個簡單的銳化，讓文字邊緣更乾淨
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            cv_img = cv2.filter2D(cv_img, -1, kernel)
            
            cv2.imwrite("debug_panel_check.png", cv_img)
            
            res = ocr.ocr(cv_img, cls=True)
            if not res or not res[0]: 
                print("❌ OCR 沒抓到文字，請確認是否打開『更多屬性』面板")
                return
            
            lines = [line[1][0] for line in res[0]]
            parse_panel_scrolling(lines)
            
            # 🟢 這裡的輸出增加 .get() 防錯
            print(f"\n" + "="*30)
            print(f"📊 同步數據如下：")
            print(f"核心：攻 {char_panel.get('攻擊', 0)} | 暴 {char_panel.get('暴擊', 0)}% | 傷 {char_panel.get('暴擊傷害', 0)}%")
            print(f"加成：屬性 {char_panel.get('屬性加成', 0)}% | 普攻 {char_panel.get('普攻加成', 0)}% | 重擊 {char_panel.get('重擊加成', 0)}%")
            print(f"技能：{char_panel.get('技能加成', 0)}% | 解放 {char_panel.get('解放加成', 0)}%")
            print("="*30)
            
    except Exception as e: 
        print(f"🔴 系統報錯: {e}")

def capture_slot(slot_num):
    try:
        win = gw.getWindowsWithTitle("鳴潮")[0]
        with mss.mss() as sct:
            monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}
            img = Image.frombytes("RGB", sct.grab(monitor).size, sct.grab(monitor).bgra, "raw", "BGRX")
            w, h = img.size
            cropped = img.crop((int(w*0.72), int(h*0.25), int(w*0.98), int(h*0.52)))
            cv_img = cv2.cvtColor(np.array(cropped), cv2.COLOR_RGB2BGR)
            res = ocr.ocr(cv_img, cls=True)
            if not res or not res[0]: return
            data = parse_text_professional([line[1][0] for line in res[0]])
            
            # 【核心修正】計算分數包含攻擊百分比權重 0.5
            data["分數"] = (data["暴擊率"] * WEIGHTS["crit_rate"]) + \
                          (data["暴擊傷害"] * WEIGHTS["crit_dmg"]) + \
                          (data["攻擊百分比"] * WEIGHTS["atk_percent"])
            
            echo_slots[slot_num] = data
            print(f"✅ {slot_num}號位更新 | 詞條分: {data['分數']:.1f}")
    except Exception as e: print(f"錄入失敗: {e}")

def calculate_expectation(cr, cd, ap, flat_atk):
    """
    計算傷害期望值公式：
    final_atk = (基礎攻擊 * (1 + 攻擊%)) + 固定小攻擊
    期望值 = 攻擊 * [暴率 * 暴傷 + (1-暴率)] * (1 + 屬傷)
    """
    final_atk = (BASE_ATTACK * (1 + ap/100)) + flat_atk
    # 鳴潮基礎暴傷為 150%，OCR 抓到 13.8% 代表總暴傷為 163.8% (1.638)
    # 這裡假設 cd 抓到的是副詞條顯示的數字
    crit_multiplier = (cr/100) * (cd/100 + 1.5) + (1 - cr/100)
    expectation = final_atk * crit_multiplier * (1 + ATTR_BONUS)
    return expectation

def parse_text_professional(lines):
    """專業解析邏輯：處理錯字、拆行與小攻擊"""
    extracted = {"暴擊率": 0, "暴擊傷害": 0, "攻擊百分比": 0, "固定攻擊": 0}
    
    # 合併文字並過濾常見錯字
    full_content = "".join(lines).replace(" ", "").replace("挚", "擊").replace("撃", "擊").replace("灭", "")
    print(f"\nDEBUG 掃描內容: {full_content}")

    # 1. 抓暴擊率
    # 使用聯想匹配：找「暴」之後的數字
    cr_pattern = re.findall(r"暴[擊率]{1,2}.*?(\d+\.?\d*)%", full_content)
    for val in cr_pattern:
        f_val = float(val)
        if f_val < 12.0: 
            extracted["暴擊率"] = f_val
            break

    # 2. 抓暴擊傷害 (限制 12%~22% 區間，排除"加成"字眼)
    cd_pattern = re.findall(r"暴擊?傷害?(\d+\.?\d*)%", full_content)    
    # 傳統寫法：先篩選符合區間的數值
    cd_candidates = [float(v) for v in cd_pattern if 12.0 <= float(v) <= 22.0]    
    # 如果第一輪沒抓到，執行備案
    if not cd_candidates:
        alt_pattern = re.findall(r"(?<!加成)傷害(\d+\.?\d*)%", full_content)
        cd_candidates = [float(v) for v in alt_pattern if 12.0 <= float(v) <= 22.0]

    if cd_candidates:
        extracted["暴擊傷害"] = cd_candidates[0]

    # 3. 攻擊力 (區分百分比與固定值)
    # 這裡多加一個關鍵字過濾，防止抓到防禦力或生命值的百分比
    atk_matches = re.findall(r"攻擊.*?(\d+\.?\d*)(%?)", full_content)
    for num, unit in atk_matches:
        val = float(num)
        if unit == "%":
            # 鳴潮副詞條攻擊百分比通常在 6.4% ~ 11.6% 之間
            if 6.0 <= val <= 13.0: 
                extracted["攻擊百分比"] = val
        else:
            # 固定攻擊通常在 20~70 之間
            if 20 <= val <= 70: 
                extracted["固定攻擊"] = val
            
    return extracted


def preprocess_image(pil_img):
    """影像預處理：灰階放大"""
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    return upscaled

def show_summary():
    if not echo_list:
        print(">>> 目前沒有任何記錄。")
        return

    total_cr = sum(d["暴擊率"] for d in echo_list)
    total_cd = sum(d["暴擊傷害"] for d in echo_list)
    total_ap = sum(d["攻擊百分比"] for d in echo_list)
    total_flat = sum(d["固定攻擊"] for d in echo_list)

    exp = calculate_expectation(total_cr, total_cd, total_ap, total_flat)

    print("\n" + "█"*45)
    print(f"【 鳴潮全身 5 件套 - 總結報告 】")
    print(f"累計副詞條：")
    print(f" - 暴率: {total_cr:.1f}% | 暴傷: {total_cd:.1f}%")
    print(f" - 攻%: {total_ap:.1f}% | 固定攻擊: {total_flat:.0f}")
    print(f"---")
    print(f"🔥 總傷害期望值：{exp:.2f}")
    print(f"---")
    print(f"【 各項傷害預估 】")
    for key, weight in DAMAGE_DISTRIBUTION.items():
        print(f" - {key} ({weight*100:>2.0f}%): {exp * weight:.2f}")
    print("█"*45 + "\n")

def clear_data():
    global echo_list
    echo_list = []
    print("\n>>> 數據已清空。")

def on_press(key):
    try:
        # F1 ~ F5 對應 1 ~ 5 號位聲骸
        if key == keyboard.Key.f1: capture_slot(1)
        if key == keyboard.Key.f2: capture_slot(2)
        if key == keyboard.Key.f3: capture_slot(3)
        if key == keyboard.Key.f4: capture_slot(4)
        if key == keyboard.Key.f5: capture_slot(5)
        
        # F8 掃描面板 (滾動時按住或連按)
        if key == keyboard.Key.f8: capture_full_panel()
        
        # F12 總結
        if key == keyboard.Key.f12:
            print("\n" + "═"*55)
            print("【 鳴潮配裝最終匯總 - 槽位詳細數據 】")
            total_slots_score = 0
            for i in range(1, 6):
                s = echo_slots[i]
                if s["分數"] > 0:
                    total_slots_score += s["分數"]
                    # 這裡加上了 攻% 的顯示
                    print(f"{i}號位: {s['分數']:>5.1f} 分 | 暴{s['暴擊率']:>4.1f}% | 傷{s['暴擊傷害']:>4.1f}% | 攻{s['攻擊百分比']:>4.1f}%")
            
            print("-" * 35)
            # 期望值計算
            crit_m = (char_panel["暴擊"]/100) * (char_panel["暴擊傷害"]/100 + 1.5) + (1 - char_panel["暴擊"]/100)
            # 屬性總加成 = 屬性加成 + 解放加成 (這裡可依需求調整公式)
            total_exp = char_panel["攻擊"] * crit_m * (1 + (char_panel["屬性加成"])/100)
            
            print(f"📊 面板加成摘要：")
            print(f"   普攻:{char_panel['普攻加成']}% | 重擊:{char_panel['重擊加成']}% | 技能:{char_panel['技能加成']}% | 解放:{char_panel['解放加成']}%")
            print(f"🎯 角色最終期望輸出預估: {total_exp:.2f}")
            print("═"*55)
        # 重建退出功能
        if key == keyboard.Key.esc:
            print("\n>>> 程式已安全退出。")
            return False            
            
    except AttributeError: pass

print(">>> [F1-F5] 錄入對應位置聲骸 | [F8] 滾動掃描面板 | [F12] 總結報告|[Esc]退出")
with keyboard.Listener(on_press=on_press) as listener:
    listener.join()