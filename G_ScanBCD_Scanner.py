# G_ScanBCD_Scanner.py

# 標準ライブラリのインポート
import sys
import cv2
import time
import os
import csv
from datetime                   import datetime
import logging
from logging.handlers           import RotatingFileHandler
import numpy as np

# カスタムモジュールのインポート
from G_config import Config
from G_ScanBCD_Analyzer         import G_ScanBCD_Analyzer
from G_ScanBCD_DataCollector    import G_ScanBCD_DataCollector
from G_ScanBCD_CsvWriter        import G_ScanBCD_CsvWriter
from G_ScanBCD_FixCSV           import CSVHandler
from G_ScanBCD_Overlay          import OverlayDisplay

# ターミナル出力時文字化け対策
sys.stdout.reconfigure(encoding='utf-8')

class BarcodeScanner:
# 要求される設定値のキー
    REQUIRED_KEYS = {
        "scan_log",
        "expected_length",
        "barcode_type",
        "barcode_data",
        "scan_count",
        "display_time",
        "target_fps",
        "auto_stop",
        "idle_timeout"
    }

    def __init__(self, config, location, construction_number):
        self.config = config

        missing_keys=[]
        for key in self.REQUIRED_KEYS:
            if self.config.get(key) is None:
                  missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"設定ファイルに以下のキーが存在しません: {', '.join(missing_keys)}")
        

        # 設定値の取得
        self.scan_log =         self.config.get("scan_log")
        self.expected_length =  self.config.get("expected_length")
        self.barcode_type =     self.config.get("barcode_type")
        self.barcode_data =     self.config.get("barcode_data")
        self.scan_count =       self.config.get("scan_count")
        self.display_time =     self.config.get("display_time")
        self.target_fps =       self.config.get("target_fps")
        self.auto_stop =        self.config.get("auto_stop")
        self.idle_timeout =     self.config.get("idle_timeout")

        self.location =             location
        self.construction_number =  construction_number
        self.last_scan_time =       time.time()

        self.success_count =    0  # 成功したスキャン数
        self.failure_count =    0  # 失敗したスキャン数
        self.duplicate_count =  0  # 重複したスキャン数
        self.last_frame_time =  0

        # ログ設定
        self._setup_logging()

        # アナライザー、データコレクター、CSVライターの初期化
        self.analyzer =         G_ScanBCD_Analyzer(config)
        self.data_collector =   G_ScanBCD_DataCollector()
        self.csv_writer =       G_ScanBCD_CsvWriter(config)

		#オーバーレイの初期化
        self.overlay_display =  OverlayDisplay(config)  # OverlayDisplay のインスタンスを作成

        # ディレクトリの作成
        self._create_data_dir()

        # CSVファイルのパス設定
        if __name__ == "__main__":
            self.data_file = self.config.get("data_file", "ScanBCD.dat")
            self.csv_file = os.path.join(self.log_dir, self.data_file)
        else:
            self.csv_file = os.path.join(self.data_dir, f"{self.construction_number}.csv")

        print("\nスキャナー起動中...")

    def _setup_logging(self):
        log_dir = self.config.get("log_dir", "log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.scan_log = os.path.join(log_dir, self.config.get("scan_log", "scan.log"))
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(self.scan_log, maxBytes=1024*1024, backupCount=5, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _create_data_dir(self):
        self.data_dir = self.config.get("data_dir", "data")
        self.log_dir = self.config.get("log_dir", "log")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start(self):
        cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get("camera_width", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get("camera_height", 480))

        # data.csv を上書きモードで開く
        if __name__ == "__main__":
            data_csv_file = open(self.csv_file, mode='w', newline='', encoding='utf-8')
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

            barcodes, frame = self.analyzer.analyze(frame)

            # 残り時間を計算
            remaining_time = max(0, self.idle_timeout - (time.time() - self.last_scan_time))

            # オーバーレイを描画
            frame = self.display_scan_result(frame, barcodes, remaining_time) #戻り値を受け取る

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
                        
                        #scanned_infoへの追加
                        self.add_scanned_info(barcode_info, barcode_type)
                    else:
                        self.duplicate_count += 1  # 重複したスキャン数を更新

            if frame is not None and isinstance(frame, np.ndarray):
                cv2.imshow('Barcode Scanner', frame)
            else:
                print("Error: Invalid frame received.")

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
        if __name__ == "__main__":
            data_csv_file.close()

        # CSV 重複削除処理の追加（単体起動時以外）
        if __name__ != "__main__":
            handler = CSVHandler(self.csv_file, self.config)
            handler.find_duplicates()

    def display_scan_result(self, frame, barcodes, remaining_time):
        # OverlayDisplay クラスの display_overlay メソッドを呼び出す
        frame = self.overlay_display.display_overlay(
            frame, barcodes, self.scan_count,
            self.success_count, self.failure_count, self.duplicate_count,
            self.location, self.construction_number, remaining_time,
            self.config.get('barcode_type', '-'), self.config.get('expected_length', '-')
        )
        return frame #フレームを返す
    
    def add_scanned_info(self, barcode_info, barcode_type):
        timestamp = time.time()
        self.overlay_display.scanned_info.append({
            'barcode': barcode_info,
            'type': barcode_type,
            'timestamp': timestamp
        })

    def get_current_timestamp(self):
        # ... (タイムスタンプ取得) ...
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    print("\n単体起動中...")
    config = Config("config.json")
    location = "_K1_"  # 単体起動用の初期値
    construction_number = "_4656_"  # 単体起動用の初期値
    scanner = BarcodeScanner(config=config, location=location, construction_number=construction_number)
    scanner.start()
