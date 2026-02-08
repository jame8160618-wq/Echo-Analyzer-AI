# Echo-Analyzer-AI
# 🎮 鳴潮聲骸數據自動化分析儀 (Echo Analyzer AI)(測試版)

這是一個結合 **影像辨識 (Computer Vision)** 與 **數據分析** 的全端工具，旨在解決玩家在評估遊戲裝備（聲骸）時計算繁瑣的痛點。

## 🚀 核心功能
- **自動辨識**：角色總面板截取角色全屬性展開圖(目前版本請截取複數張直至底部以確保屬性皆被計入)，聲骸部分上傳遊戲聲骸套裝全螢幕截圖，自動擷取左側聲骸圖示與右側屬性數值。
- **數據繼承**：支援分次上傳，分別紀錄五個槽位的數據，無需重複輸入。
- **期望值演算法**：根據數學期望值公式，整合「傷害佔比權重」(目前傷害佔比需自行調整)與「傷害乘區」進行加權評分，以便比較更換聲骸前後差異。

## 🛠️ 技術棧
- **後端**: Python, FastAPI
- **影像處理**: OpenCV (座標校準、區域裁切)
- **文字辨識**: Tesseract OCR / PaddleOCR
- **前端**: HTML5, CSS3, JavaScript (Vanilla JS)

## 📊 數學模型
本工具使用以下加權期望值公式：
單下期望值 = 總攻擊力*{暴擊期望乘區}*加成修正項

- 暴擊期望乘區 = [(1 -暴擊率)+ (暴擊率*暴擊傷害)]
- 加成修正項 = 1 + 屬性加成 + 特定動作加成(普攻/重擊/技能/解放/其他)


## 📸 畫面展示
![介面預覽]
<img width="1920" height="1080" alt="角色面板截圖" src="https://github.com/user-attachments/assets/47149ad3-fa12-4790-a6fd-773d0521e2e7" />
<img width="1920" height="1080" alt="聲骸測試" src="https://github.com/user-attachments/assets/3819a59c-9c3b-4d34-b436-a5f6fbb5c969" />
<img width="1180" height="907" alt="image" src="https://github.com/user-attachments/assets/ecf6dbd8-756e-4d0b-8429-444eab48ed24" />

