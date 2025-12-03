# G_ProcessScanner.py

# 標準ライブラリのインポート
import sys
import cv2
import time
import os
import logging
from logging.handlers           import RotatingFileHandler
import numpy as np

# カスタムモジュールのインポート
from G_config import Config
from G_ScanBCD_Analyzer         import G_ScanBCD_Analyzer
from G_ProcessCsvWriter         import G_ProcessCsvWriter # G_ScanBCD_CsvWriter から変更
from G_ScanBCD_Overlay          import OverlayDisplay

# ターミナル出力時文字化け対策
sys.stdout.reconfigure(encoding='utf-8')

class ProcessScanner:
    REQUIRED_KEYS = {
        "scan_log",
        "expected_length",
        "barcode_type",
        "display_time",
        "target_fps",
        "auto_stop",
        "idle_timeout"
    }

    def __init__(self, config, construction_number, process_name, supplier_name):
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
        self.display_time =     self.config.get("display_time")
        self.target_fps =       self.config.get("target_fps")
        self.auto_stop =        self.config.get("auto_stop")
        self.idle_timeout =     self.config.get("idle_timeout")

        # 引数から受け取る情報
        self.construction_number =  construction_number
        self.process_name =         process_name
        self.supplier_name =        supplier_name

        # 内部状態変数
        self.last_scan_time =       time.time()
        self.success_count =    0
        self.failure_count =    0
        self.duplicate_count =  0
        self.scan_count =       0
        self.last_frame_time =  0
        self.barcode_data =     [] # このセッションでスキャンしたバーコードを保持

        # ログ設定
        self._setup_logging()

        # 各種モジュールの初期化
        self.analyzer =         G_ScanBCD_Analyzer(config)
        # G_ProcessCsvWriter を使用するように変更
        self.csv_writer =       G_ProcessCsvWriter(config, self.construction_number, self.process_name, self.supplier_name)
        self.overlay_display =  OverlayDisplay(config)

        # ディレクトリの作成
        self._create_data_dir()

        print("\n工程スキャナー起動中...")
        print(f"工事番号: {self.construction_number}, 工程: {self.process_name}, 納品業者: {self.supplier_name}")

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

            # オーバーレイを描画 (locationの代わりにprocess_nameを渡す)
            frame = self.display_scan_result(frame, barcodes, remaining_time)

            if barcodes:
                self.last_scan_time = time.time()

            for barcode in barcodes:
                barcode_info = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                if barcode_type == self.barcode_type and len(barcode_info) == self.expected_length:
                    if barcode_info not in self.barcode_data:
                        self.barcode_data.append(barcode_info)
                        self.scan_count += 1
                        self.success_count += 1
                        
                        # G_ProcessCsvWriter を使って書き込み
                        self.csv_writer.write(barcode_info, barcode_type)
                        
                        log_message = f"工程スキャン: {barcode_info}, 工事番号: {self.construction_number}, 工程: {self.process_name}, 業者: {self.supplier_name}"
                        self.logger.info(log_message)
                        print(f"Scanned: {barcode_info} (Type: {barcode_type})")

                        self.add_scanned_info(barcode_info, barcode_type)
                    else:
                        self.duplicate_count += 1

            if frame is not None and isinstance(frame, np.ndarray):
                cv2.imshow('Process Scanner', frame)
            else:
                print("Error: Invalid frame received.")

            # ウィンドウの位置を右側に寄せる
            screen_width = 1366
            window_width = 640
            x = screen_width - window_width - 10
            y = 10

            cv2.namedWindow('Process Scanner', cv2.WINDOW_NORMAL)
            cv2.moveWindow('Process Scanner', x, y)

            if self.auto_stop and remaining_time == 0:
                print(f"{self.idle_timeout / 60}分間バーコードが読み込まれなかったため、スキャンを停止します。")
                break

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("スキャナー停止")
                break

            self.last_frame_time = current_time

        cap.release()
        cv2.destroyAllWindows()
        print("工程スキャナーのメインループを終了しました。")
        print(f"スキャン結果: {self.scan_count} 件のバーコードを検出しました。")

    def display_scan_result(self, frame, barcodes, remaining_time):
        # OverlayDisplay を使用 (locationの代わりにprocess_nameを渡す)
        frame = self.overlay_display.display_overlay(
            frame, barcodes, self.scan_count,
            self.success_count, self.failure_count, self.duplicate_count,
            self.process_name, self.construction_number, remaining_time,
            self.config.get('barcode_type', '-'), self.config.get('expected_length', '-')
        )
        return frame
    
    def add_scanned_info(self, barcode_info, barcode_type):
        timestamp = time.time()
        self.overlay_display.scanned_info.append({
            'barcode': barcode_info,
            'type': barcode_type,
            'timestamp': timestamp
        })

def main():
    """
    コマンドライン引数から 'construction_no', 'process_name', 'supplier_name' を受け取って
    ProcessScannerを起動する。
    """
    if len(sys.argv) != 4:
        print("使用法: python G_ProcessScanner.py <工事番号> <工程名> <納品業者名>")
        sys.exit(1)

    construction_no = sys.argv[1]
    process_name = sys.argv[2]
    supplier_name = sys.argv[3]

    try:
        config = Config("config.json")
    except Exception as e:
        print(f"設定ファイル(config.json)の読み込みに失敗しました: {e}")
        # messageboxは使えないのでprintで
        sys.exit(1)

    try:
        scanner = ProcessScanner(
            config=config,
            construction_number=construction_no,
            process_name=process_name,
            supplier_name=supplier_name
        )
        scanner.start()
    except Exception as e:
        print(f"ProcessScanner の起動中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()