import re

def parse_panel_to_dict(lines):
    found_this_time = []
    
    char_panel = {
        "攻擊": 0, "暴擊": 0, "暴擊傷害": 0,
        "屬性加成": 0, "普攻加成": 0, "重擊加成": 0,
        "技能加成": 0, "解放加成": 0
    }
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

    return char_panel