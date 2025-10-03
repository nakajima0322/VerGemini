# G_ScanBCD_Analyzer.py

import cv2
from pyzbar.pyzbar import decode

class G_ScanBCD_Analyzer:
    def __init__(self, config):
        self.config = config
        print("\nバーコード解析開始...")

    def analyze(self, image):
        # 画像をグレースケールに変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # バーコードを検出
        barcodes = decode(gray)
        
        # 解析結果と、未変更のオリジナル画像を返す
        return barcodes, image
