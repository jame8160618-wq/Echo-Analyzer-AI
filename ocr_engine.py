# ocr_engine.py
from paddleocr import PaddleOCR

# 初始化放在全域，只載入一次
ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

def get_raw_text(cv_img):
    res = ocr.ocr(cv_img, cls=True)
    if not res or not res[0]:
        return []
    return [line[1][0] for line in res[0]]