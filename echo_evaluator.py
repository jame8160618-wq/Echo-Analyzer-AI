import re

WEIGHTS = {
    "crit_rate": 2.0,   # 暴擊 1% = 2分
    "crit_dmg": 1.0,    # 暴傷 1% = 1分
    "atk_percent": 0.5  # 攻擊 1% = 0.5分
}

def evaluate_echo_stats(lines):
    """
    從 OCR 文字清單中解析副詞條並計算分數
    """
    extracted = {"暴擊率": 0, "暴擊傷害": 0, "攻擊百分比": 0, "固定攻擊": 0, "分數": 0}
    
    # 2. 搬移原有的預處理與解析邏輯 (parse_text_professional)
    # 增加更多 OCR 錯字替換
    full_content = "".join(lines).replace(" ", "")
    full_content = full_content.replace("挚", "擊").replace("撃", "擊").replace("稟", "擊").replace("繋", "擊")

    # 抓暴擊率：更寬鬆的匹配，只要有「暴」跟「%」中間夾數字就抓
    # 使用非貪婪匹配，並確保數字在合理範圍 (6%-11%)
    cr_pattern = re.findall(r"暴.*?(\d+\.?\d*)%", full_content)
    for val in cr_pattern:
        f_val = float(val)
        if 6.0 <= f_val <= 11.0: # 聲骸副詞條暴率固定在此範圍
            extracted["暴擊率"] = f_val
            break

    # 抓暴擊傷害
    cd_pattern = re.findall(r"暴擊?傷害?(\d+\.?\d*)%", full_content)    
    cd_candidates = [float(v) for v in cd_pattern if 12.0 <= float(v) <= 22.0]    
    if not cd_candidates:
        alt_pattern = re.findall(r"(?<!加成)傷害(\d+\.?\d*)%", full_content)
        cd_candidates = [float(v) for v in alt_pattern if 12.0 <= float(v) <= 22.0]

    if cd_candidates:
        extracted["暴擊傷害"] = cd_candidates[0]

    # 抓攻擊力 (百分比與固定值)
    atk_matches = re.findall(r"攻擊.*?(\d+\.?\d*)(%?)", full_content)
    for num, unit in atk_matches:
        val = float(num)
        if unit == "%":
            if 6.0 <= val <= 13.0: 
                extracted["攻擊百分比"] = val
        else:
            if 20 <= val <= 70: 
                extracted["固定攻擊"] = val
                
    # 3. 計算分數 (搬移評分公式)
    extracted["分數"] = round(
        (extracted["暴擊率"] * WEIGHTS["crit_rate"]) + \
        (extracted["暴擊傷害"] * WEIGHTS["crit_dmg"]) + \
        (extracted["攻擊百分比"] * WEIGHTS["atk_percent"]), 
        1
    )
            
    return {
    "暴擊率": extracted["暴擊率"],
    "暴擊傷害": extracted["暴擊傷害"],
    "攻擊百分比": extracted["攻擊百分比"],
    "分數": extracted["分數"]
}