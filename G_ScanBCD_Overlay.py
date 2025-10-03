# G_ScanBCD_Overlay.py
import cv2
import time
import numpy as np

class OverlayDisplay:
    # 要求される設定値のキー
    REQUIRED_KEYS = {
        "font_scale",
        "display_lines",
        "overlay_alpha",
        "overlay_color",
        "display_text_mapping",
        "display_time",
        "barcode_type",
        "expected_length",
    }

    def __init__(self, config):
        self.config = config
        self.scanned_info = []  # scanned_infoをインスタンス変数として保持
        self.last_seen = {}  # バーコードの最終検出時間と位置を記録
        self.detection_timeout = 1.0  # 検出が途切れてから矩形を消すまでの時間

        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if self.config.get(key) is None:
                missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"設定ファイルに以下のキーが存在しません: {', '.join(missing_keys)}")

    def display_overlay(
            self,
            frame,
            barcodes,
            scan_count,
            success_count,
            failure_count,
            duplicate_count,
            location,
            construction_number,
            remaining_time,
            barcode_type,
            expected_length):

        height, width, _ = frame.shape
        overlay_x = 30
        overlay_y = 30

        text_mapping = self.config.get("display_text_mapping")
        display_location = text_mapping.get(location, location)
        spec_text = f"Type: {self.config.get('barcode_type')} | Digits: {self.config.get('expected_length')} | Location: {display_location} | Construction: {construction_number}"

        font_scale = self.config.get("font_scale")
        display_lines = self.config.get("display_lines")

        # テキストを改行で分割
        spec_text_lines = spec_text.split(" | ")

        # 背景サイズの計算
        max_text_width = 0
        total_text_height = 0
        for line in spec_text_lines:
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            max_text_width = max(max_text_width, text_size[0])  # 最大幅を取得
            total_text_height += text_size[1] + 10 - 7  # 各行の高さと行間の余白を加算

        background_width = max_text_width
        background_height = total_text_height

        # 背景の描画範囲を調整
        background_top = overlay_y - 12 - 10  # 上端をテキストの開始位置に合わせる
        background_bottom = overlay_y + background_height + 20  # 下端を背景の高さに合わせる
        background_left = overlay_x - 7 - 10
        background_right = overlay_x + background_width + 20

        # 半透明の背景を描画
        overlay_rect = frame[background_top:background_bottom, background_left:background_right]
        alpha = self.config.get("overlay_alpha")
        overlay_color = self.config.get("overlay_color")
        overlay_rect = cv2.addWeighted(overlay_rect, alpha, np.full_like(overlay_rect, overlay_color, dtype=np.uint8), 1 - alpha, 0)
        frame[background_top:background_bottom, background_left:background_right] = overlay_rect

        # テキストを描画
        for i, line in enumerate(spec_text_lines):
            y_position = overlay_y + i * (cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0][1] + 10)
            cv2.putText(frame, line, (overlay_x, y_position), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

        # スキャンされたバーコードの総数を表示
        scan_text = f"Scans: {scan_count}"
        cv2.putText(frame, scan_text, (width - 200, height - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

        # 重複したスキャン数を表示
        duplicate_text = f"Duplicates: {duplicate_count}"
        cv2.putText(frame, duplicate_text, (width - 200, height - 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2, cv2.LINE_AA)

        # 残り時間を表示
        remaining_time_text = f"Time left: {int(remaining_time)}s"
        cv2.putText(frame, remaining_time_text, (width - 200, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2, cv2.LINE_AA)

        for info in self.scanned_info:  # インスタンス変数から参照
            barcode_info = info['barcode']
            barcode_type = info['type']
            timestamp = info['timestamp']

            if time.time() - timestamp <= self.config.get("display_time"):
                text = f"{barcode_info} ({barcode_type})"
                cv2.putText(frame, text, (overlay_x, overlay_y + display_lines * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                overlay_y += 20

            if time.time() - timestamp > self.config.get("display_time"):
                self.scanned_info[:] = [info for info in self.scanned_info if time.time() - info['timestamp'] <= self.config.get("display_time")]

        # --- バーコードの矩形と情報の描画 --- 
        current_time = time.time()

        # 現フレームで検出されたバーコードでlast_seenを更新
        for barcode in barcodes:
            barcode_info_str = barcode.data.decode('utf-8')
            self.last_seen[barcode_info_str] = {'barcode': barcode, 'timestamp': current_time}

        # last_seenにあるバーコードを描画（色分けしつつ）
        to_remove = []
        for barcode_info, seen_data in self.last_seen.items():
            elapsed_time = current_time - seen_data['timestamp']

            if elapsed_time > self.detection_timeout:
                to_remove.append(barcode_info)
                continue

            # 時間経過で色を決定
            if elapsed_time < 0.2:
                color = (0, 255, 0)  # 緑
            elif elapsed_time < 0.5:
                color = (0, 255, 255) # 黄
            else:
                color = (0, 0, 255)  # 赤

            barcode_obj = seen_data['barcode']
            
            # 矩形を描画
            rect_points = barcode_obj.polygon
            if len(rect_points) == 4:
                pts = np.array(rect_points, dtype=np.int32).reshape((-1, 1, 2))
            else:
                x, y, w, h = barcode_obj.rect
                pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32).reshape((-1, 1, 2))
            
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

            # テキストを描画
            text = f"{barcode_info} ({barcode_obj.type})"
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(frame, (pts[0][0][0], pts[0][0][1] - text_h - 15), (pts[0][0][0] + text_w, pts[0][0][1] - 10), color, -1)
            cv2.putText(frame, text, (pts[0][0][0], pts[0][0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)

        # タイムアウトしたバーコードを辞書から削除
        for key in to_remove:
            del self.last_seen[key]

        return frame
