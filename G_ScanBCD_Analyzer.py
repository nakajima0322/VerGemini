# G_ScanBCD_Analyzer.py

import cv2
import numpy as np
from pyzbar.pyzbar import decode
import time

class G_ScanBCD_Analyzer:
    def __init__(self, config):
        self.config = config
        self.last_seen = {}  # バーコードが最後に検出された時間を記録する辞書
        self.timeout = 1.0  # バーコードが検出されなくなってから、矩形を消すまでの時間（秒）

        print("\nバーコード解析開始...")

    def analyze(self, image):
        # 画像の前処理（必要に応じて）
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # グレースケール変換
        # ... その他の画像処理 ...

        # バーコード検出
        barcodes = decode(gray)

        # バーコードの矩形領域と情報を画像に描画
        for barcode in barcodes:
            # 矩形領域の描画
            rect_points = barcode.polygon
            if len(rect_points) == 4:
                pts = np.array(rect_points, dtype=np.int32)
                pts = pts.reshape((-1, 1, 2))
            else:
                x, y, w, h = barcode.rect
                pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32)
                pts = pts.reshape((-1, 1, 2))

            # バーコード情報の表示
            barcode_info = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            text = f"{barcode_info} ({barcode_type})"
            cv2.putText(image, text, (pts[0][0][0], pts[0][0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # バーコードの検出状態を更新
            self.last_seen[barcode_info] = time.time()

            # バーコードの検出状態に応じて、矩形の色を変更
            elapsed_time = time.time() - self.last_seen[barcode_info]
            if elapsed_time < 0.2:
                color = (0, 255, 0)  # 緑色
            elif elapsed_time < 0.5:
                color = (0, 255, 255)  # 黄色
            else:
                color = (0, 0, 255)  # 赤色

            cv2.polylines(image, [pts], isClosed=True, color=color, thickness=2)

        # タイムアウトしたバーコードを削除
        to_remove = []
        for barcode_info, last_seen_time in self.last_seen.items():
            if time.time() - last_seen_time > self.timeout:
                to_remove.append(barcode_info)
        for barcode_info in to_remove:
            del self.last_seen[barcode_info]

        return barcodes, image
