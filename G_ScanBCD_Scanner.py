# G_ScanBCD_Scanner.py

# 標準ライブラリのインポート
import sys
import cv2
import time
import os
import csv
import json
from datetime                   import datetime
import logging
from logging.handlers           import RotatingFileHandler
import numpy as np

import tkinter as tk # Tkinterダイアログの親を管理するためにインポート
# カスタムモジュールのインポート
from G_config import Config
from G_ScanBCD_Analyzer         import G_ScanBCD_Analyzer
from G_ScanBCD_DataCollector    import G_ScanBCD_DataCollector
from G_ScanBCD_CsvWriter        import G_ScanBCD_CsvWriter
from G_ManualEntryDialog        import ManualEntryDialog # 新しいダイアログをインポート
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
        # バーコードなし部品用設定
        self.no_barcode_type = self.config.get("no_barcode_type", "NO_BARCODE")
        self.no_barcode_prefix = self.config.get("no_barcode_prefix", "99") # 固定プレフィックス
        self.manual_drawing_barcode_type = self.config.get("manual_entry_drawing_barcode_type", "MANUAL_DRAWING") # 新しいタイプ


        self.location =             location
        self.construction_number =  construction_number
        self.last_scan_time =       time.time()

        self._tk_dialog_parent_window = None # Tkinterダイアログの親ウィンドウ用
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

    def _generate_no_barcode_id(self):
        """
        バーコードなし部品用の代替IDを生成し、専用のシーケンスファイルに状態を保存する。
        形式: 固定プレフィックス(2桁) + 工事番号(4桁) + 連番(4桁)
        """
        sequence_file = os.path.join(self.config.get("data_dir", "data"), "sequences.json")
        sequences = {}
        
        # シーケンスファイルが存在すれば読み込む
        if os.path.exists(sequence_file):
            with open(sequence_file, 'r', encoding='utf-8') as f:
                try:
                    sequences = json.load(f)
                except json.JSONDecodeError:
                    print(f"⚠ シーケンスファイル {sequence_file} が破損しています。新しいファイルを作成します。")
                    sequences = {}

        # 現在の工事番号の次のシーケンス番号を取得 (存在しなければ1から)
        current_construction_no = self.construction_number
        next_seq = sequences.get(current_construction_no, 1)
        
        # 4桁のゼロ埋め文字列にフォーマット
        seq_str = str(next_seq).zfill(4)
        
        # 新しいIDを生成
        new_id = f"{self.no_barcode_prefix}{current_construction_no}{seq_str}"
        
        # シーケンス番号を更新
        sequences[current_construction_no] = next_seq + 1
        
        # シーケンスファイルを更新
        with open(sequence_file, 'w', encoding='utf-8') as f:
            json.dump(sequences, f, indent=4, ensure_ascii=False)
            
        return new_id

    def _register_no_barcode_item(self):
        """バーコードなし部品を手動で登録する"""
        print("バーコードなし部品を手動登録します...")
        barcode_info = self._generate_no_barcode_id()
        barcode_type = self.no_barcode_type

        if barcode_info not in self.barcode_data:
            self.barcode_data.append(barcode_info)
            self.scan_count += 1
            self.success_count += 1
            data = self.data_collector.collect(barcode_info, barcode_type, self.get_current_timestamp(), self.location, self.construction_number)
            self.logger.info("手動登録: %s", data)
            print(f"Manually Registered: {barcode_info} Type: {barcode_type}")

            with open(self.csv_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(data.values())

            self.add_scanned_info(barcode_info, barcode_type)
            self.last_scan_time = time.time() # アイドルタイムリセット
        else:
            # 通常は発生しないはずだが、ID生成ロジックに問題があった場合など
            print(f"⚠ 生成された代替ID {barcode_info} は既に存在します。")

    def _get_tk_dialog_parent(self):
        """ダイアログの親となる非表示のTkルートウィンドウが利用可能であることを保証する"""
        if self._tk_dialog_parent_window is None or not self._tk_dialog_parent_window.winfo_exists():
            # 存在しないか破棄されていれば、新しい非表示のルートウィンドウを作成
            self._tk_dialog_parent_window = tk.Tk()
            self._tk_dialog_parent_window.withdraw() # 非表示にする
        return self._tk_dialog_parent_window

    def _register_manual_drawing_item(self):
        """図番検索による手動登録ダイアログを表示し、結果を登録する"""
        print("図番による手動登録を開始します...")
        # 余計な空白ウィンドウを防ぐため、適切な親をTkinterダイアログに渡す
        dialog_parent = self._get_tk_dialog_parent()
        dialog = ManualEntryDialog(dialog_parent, self.config, self.location, self.construction_number)
        selected_part_info = dialog.get_result()

        if selected_part_info:
            barcode_info = selected_part_info["barcode_info"] # 発注伝票No
            # ダイアログの結果からbarcode_typeを使用
            barcode_type = selected_part_info["barcode_type"]

            if barcode_info not in self.barcode_data:
                self.barcode_data.append(barcode_info)
                self.scan_count += 1 # スキャン数としてカウント（手動登録も1件として）
                self.success_count += 1
                data = self.data_collector.collect(barcode_info, barcode_type, self.get_current_timestamp(), self.location, self.construction_number)
                self.logger.info(f"図番手動登録 ({barcode_type}): {data} (部品情報: {selected_part_info})")
                print(f"Manually Registered (Drawing): {barcode_info} Type: {barcode_type}")

                # CSVへの書き込み (単体起動時と通常起動時で共通化)
                with open(self.csv_file, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(data.values())

                self.add_scanned_info(barcode_info, barcode_type)
                self.last_scan_time = time.time() # アイドルタイムリセット
            else:
                print(f"⚠ {barcode_type} で登録しようとした発注伝票番号 {barcode_info} は既にスキャン/登録済みです。")
        else:
            print("図番による手動登録はキャンセルされました。")

    def start(self):
        cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get("camera_width", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get("camera_height", 480))

        # data.csv を上書きモードで初期化（単体起動時のみ）
        if __name__ == "__main__":
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
                # ヘッダー行が必要な場合はここで書き込む (例)
                # writer = csv.writer(file)
                # writer.writerow(["barcode_info", "construction_number", "location", "barcode_type", "timestamp"])
                pass # 初期化のみ行う

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

                        # CSVファイルへの書き込み
                        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as file:
                            writer = csv.writer(file)
                            writer.writerow(data.values())

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

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27: # qキーまたはESCキー
                print("スキャナー停止")
                break
            elif key == ord('n'): # 'N'キーでバーコードなし部品を登録
                self._register_no_barcode_item()
            elif key == ord('m'): # 'M'キーで図番による手動登録
                self._register_manual_drawing_item()

            self.last_frame_time = current_time

        cap.release()
        cv2.destroyAllWindows()

        # もし作成されていれば、非表示のTkinterルートをクリーンアップ
        if self._tk_dialog_parent_window and self._tk_dialog_parent_window.winfo_exists():
            self._tk_dialog_parent_window.destroy()
        print("バーコードスキャナーのメインループを終了しました。")

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
    standalone_display_time = 300
    config.set("display_time", standalone_display_time)
    print(f"\t display_time を {standalone_display_time} 秒に設定しました。")
    location = "_K1_"
    print(f"\t location を {location} に設定しました。")
    construction_number = "_4656_"
    print(f"\t construction_number を {construction_number} に設定しました。")
    scanner = BarcodeScanner(config=config, location=location, construction_number=construction_number)
    scanner.start()
