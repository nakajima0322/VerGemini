# G_ScanBCD_Scanner.py

# 標準ライブラリのインポート
import sys
import cv2
import time
import os
import csv
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import numpy as np

# カスタムモジュールのインポート
from G_config import Config
from G_ScanBCD_Analyzer import G_ScanBCD_Analyzer
from G_ScanBCD_DataCollector import G_ScanBCD_DataCollector
from G_ScanBCD_CsvWriter import G_ScanBCD_CsvWriter
from G_ScanBCD_FixCSV import CSVHandler
from G_ScanBCD_Overlay import OverlayDisplay  # OverlayDisplay クラスをインポート

# ターミナル出力時文字化け対策
sys.stdout.reconfigure(encoding='utf-8')

class BarcodeScanner:
# 設定のデフォルト値
    DEFAULT_CONFIG = {
        "scan_log": "ScanBCD.log",
        "expected_length": 10,
        "barcode_type": "CODE39",
        "barcode_data": [],
        "scan_count": 0,
        "display_time": 30,
        "target_fps": 30,
        "scanned_info": [],
        "auto_stop": True,
        "idle_timeout": 300
    }

    def __init__(self, config, location, construction_number):
        self.config = config

        # 設定値の取得
        self.scan_log =         self.get_config_value("scan_log")
        self.expected_length =  self.get_config_value("expected_length")
        self.barcode_type =     self.get_config_value("barcode_type")
        self.barcode_data =     self.get_config_value("barcode_data")
        self.scan_count =       self.get_config_value("scan_count")
        self.display_time =     self.get_config_value("display_time")
        self.target_fps =       self.get_config_value("target_fps")
        self.scanned_info =     self.get_config_value("scanned_info")
        self.auto_stop =        self.get_config_value("auto_stop")
        self.idle_timeout =     self.get_config_value("idle_timeout")

        self.location = location
        self.construction_number = construction_number
        self.last_scan_time = time.time()

        self.success_count = 0  # 成功したスキャン数
        self.failure_count = 0  # 失敗したスキャン数
        self.duplicate_count = 0  # 重複したスキャン数
        self.last_frame_time = 0

        # ログ設定
        self._setup_logging()

        # アナライザー、データコレクター、CSVライターの初期化
        self.analyzer = G_ScanBCD_Analyzer(config)
        self.data_collector = G_ScanBCD_DataCollector()
        self.csv_writer = G_ScanBCD_CsvWriter(config)

		#オーバーレイの初期化
        self.overlay_display = OverlayDisplay(config)  # OverlayDisplay のインスタンスを作成

        # ディレクトリの作成
        self._create_data_dir()

        # CSVファイルのパス設定
        self.csv_file = os.path.join(self.data_dir, f"{self.construction_number}.csv")
        self.data_csv_file = "ScanBCD.dat"

        print("\nスキャナー起動中...")

        self.missing_keys = []
    def get_config_value(self, key):
        if self.config.get(key) is None:
            default_value = self.DEFAULT_VALUES.get(key)
            print(f"警告: 設定ファイルに '{key}' が存在しないため、デフォルト値 '{default_value}' を使用します。")
            return default_value
        else:
            return self.config.get(key)
        

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(self.scan_log, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _create_data_dir(self):
        self.data_dir = "data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def start(self):
        cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get("camera_width", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get("camera_height", 480))

        # data.csv を上書きモードで開く
        data_csv_file = open(self.data_csv_file, mode='w', newline='', encoding='utf-8')
        data_writer = csv.writer(data_csv_file)

        while True:
            current_time = time.time()
            elapsed_time = current_time - self.last_frame_time
            if elapsed_time < 1 / self.target_fps:
                time.sleep(1 / self.target_fps - elapsed_time)
                current_time = time.time()

            ret, frame = cap.read()
            if not ret:
                break

            barcodes = self.analyzer.analyze(frame)

            # 残り時間を計算
            remaining_time = max(0, self.idle_timeout - (time.time() - self.last_scan_time))

            # オーバーレイを描画
            self.display_scan_result(frame, barcodes, remaining_time)

            if barcodes:
                self.last_scan_time = time.time()  # バーコードが読み込まれた時間を更新

            for barcode in barcodes:
                barcode_info = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                if barcode_type == self.barcode_type and len(barcode_info) == self.expected_length:
                    if barcode_info not in self.barcode_data:
                        self.barcode_data.append(barcode_info)
                        self.scan_count += 1
                        self.success_count += 1  # 成功したスキャン数を更新
                        data = self.data_collector.collect(barcode_info, barcode_type, self.get_current_timestamp(), self.location, self.construction_number)
                        self.logger.info("スキャン結果: %s", data)
                        print(f"Scanned Barcode: {barcode_info} Type: {barcode_type}")

                        # {construction_number}.csv への出力（単体起動時以外）
                        if __name__ != "__main__":
                            with open(self.csv_file, mode='a', newline='', encoding='utf-8') as file:
                                writer = csv.writer(file)
                                writer.writerow(data.values())

                        # data.csv への出力（単体起動時のみ）
                        if __name__ == "__main__":
                            data_writer.writerow(data.values())
                    else:
                        self.duplicate_count += 1  # 重複したスキャン数を更新

            cv2.imshow('Barcode Scanner', frame)

            # ウィンドウの位置を右側に寄せる
            screen_width = 1366  # 画面の幅を設定（例として 1920 を使用）
            window_width = 640  # ウィンドウの幅を設定
            x = screen_width - window_width - 10  # 右端から 10 ピクセル内側に配置
            y = 10  # 上端から 10 ピクセル下に配置

            cv2.namedWindow('Barcode Scanner', cv2.WINDOW_NORMAL)
            cv2.moveWindow('Barcode Scanner', x, y)

            # 5分間バーコードが読み込まれなければ停止
            if self.auto_stop and remaining_time == 0:
                print(f"{self.idle_timeout / 60}分間バーコードが読み込まれなかったため、スキャンを停止します。")
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("スキャナー停止")
                break

            self.last_frame_time = current_time

        cap.release()
        cv2.destroyAllWindows()

        # data.csv ファイルを閉じる
        data_csv_file.close()

        # CSV 重複削除処理の追加（単体起動時以外）
        if __name__ != "__main__":
            handler = CSVHandler(self.csv_file, self.config)
            handler.find_duplicates()

    def display_scan_result(self, frame, barcodes, remaining_time):
        # OverlayDisplay の display_overlay メソッドを呼び出す
        self.scanned_info = self.overlay_display.display_overlay(
            frame, barcodes, self.scanned_info, self.scan_count, self.success_count,
            self.failure_count, self.duplicate_count, self.location,
            self.construction_number, remaining_time
        )

    def get_current_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    print("\n単体起動中...")
    config = Config("config.json")
    location = "_K1_"  # 単体起動用の初期値
    construction_number = "_4656_"  # 単体起動用の初期値
    scanner = BarcodeScanner(config=config, location=location, construction_number=construction_number)
    scanner.start()

def display_overlay(frame, barcodes, scanned_info, scan_count, success_count, failure_count, duplicate_count, config, location, construction_number, remaining_time):
    height, width, _ = frame.shape
    overlay_x = 10
    overlay_y = 30

    text_mapping = config.get("display_text_mapping", {})
    display_location = text_mapping.get(location, location)  # location を display_text_mapping で変換
    spec_text = f"Type: {config.get('barcode_type', '-')} | Digits: {config.get('expected_length', '-')} | Location: {display_location} | Construction: {construction_number}"

    font_scale = config.get("font_scale", 0.6)
    display_lines = config.get("display_lines", 1)

    # テキストを改行で分割
    spec_text_lines = spec_text.split(" | ")

    # 各行の幅を計算し、最大幅を取得
    max_text_width = 0
    text_heights = []
    for line in spec_text_lines:
        text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
        max_text_width = max(max_text_width, text_size[0])
        text_heights.append(text_size[1])

    # 背景の幅と高さを計算
    background_width = max_text_width + 20  # 余白を追加
    background_height = sum(text_heights) + 20 + (len(spec_text_lines) - 1) * 10  # 行間の余白を追加

    # 半透明の背景を描画
    overlay_color = (0, 0, 0)  # 背景色（黒）
    alpha = 0.5  # 半透明度
    overlay_rect = frame[overlay_y - 10:overlay_y + background_height - 10, overlay_x:overlay_x + background_width]
    overlay_rect = cv2.addWeighted(overlay_rect, alpha, np.full_like(overlay_rect, overlay_color, dtype=np.uint8), 1 - alpha, 0)
    frame[overlay_y - 10:overlay_y + background_height - 10, overlay_x:overlay_x + background_width] = overlay_rect

    # テキストを描画
    for i, line in enumerate(spec_text_lines):
        y_position = overlay_y + i * (text_heights[0] + 10)  # 行間の余白を追加
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

    for info in scanned_info:
        barcode_info = info['barcode']
        barcode_type = info['type']
        timestamp = info['timestamp']

        if time.time() - timestamp <= config.get("display_time", 3):
            text = f"{barcode_info} ({barcode_type})"
            cv2.putText(frame, text, (overlay_x, overlay_y + display_lines * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            overlay_y += 20

        if time.time() - timestamp > config.get("display_time", 3):
            scanned_info[:] = [info for info in scanned_info if time.time() - info['timestamp'] <= config.get("display_time", 3)]

    for barcode in barcodes:
        rect_points = barcode.polygon
        if len(rect_points) == 4:
            pts = np.array(rect_points, dtype=np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        else:
            x, y, w, h = barcode.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return scanned_info