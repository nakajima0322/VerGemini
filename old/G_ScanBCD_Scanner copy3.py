import sys
sys.stdout.reconfigure(encoding='utf-8')

import cv2
import time
import csv
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime
from G_config import Config
from G_barcode_status_manager import BarcodeStatusManager, Status

class BarcodeScanner:
    def __init__(self, config_path="config.json", scan_log="scanned_barcodes.csv", expected_length=10, location="Kabuto 1F", construction_number="1234"):
        start_time = time.time()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t初期化開始")
        self.config = Config(config_path)
        self.scan_log = scan_log
        self.expected_length = expected_length
        self.location = location
        self.construction_number = construction_number
        self.barcode_data = []
        self.scan_count = 0
        self.scanned_info = []
        self.display_time = self.config.get("display_time", 3)
        self.status_manager = BarcodeStatusManager()
        self.last_update_time = time.time()
        self.scan_interval = 0.5
        self.scanning = False
        self.printed_barcodes = set()
        init_end_time = time.time()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t初期化完了\t{init_end_time - start_time:.3f} 秒")

        cap_start_time = time.time()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tカメラキャプチャ開始")
        self.cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get("camera_width", 640))
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get("camera_height", 480))
        cap_end_time = time.time()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tカメラキャプチャ完了\t{cap_end_time - cap_start_time:.3f} 秒")

        self.last_frame_time = 0
        self.last_expired_check_time = 0
        self.target_fps = 30 # 目標フレームレート
        self.barcode_manager = BarcodeStatusManager(scan_log, location, construction_number) # BarcodeStatusManagerのインスタンスを生成し、属性に代入

    def start(self, auto_stop=True):
        self.scanning = True
        try:
            while True:
                current_time = time.time()

                # フレームレート制御
                elapsed_time = current_time - self.last_frame_time
                if elapsed_time < 1 / self.target_fps:
                    time.sleep(1 / self.target_fps - elapsed_time)
                    current_time = time.time()

                frame_start_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tフレーム読み込み開始")
                ret, frame = self.cap.read()
                if not ret:
                    break
                frame_end_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tフレーム読み込み完了\t{frame_end_time - frame_start_time:.3f} 秒")

                barcode_start_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tバーコード検出開始")
                barcodes = decode(frame)
                barcode_end_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tバーコード検出完了\t{barcode_end_time - barcode_start_time:.3f} 秒")

                for barcode in barcodes:
                    barcode_info_start_time = time.time()
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tバーコード情報処理開始")

                    barcode_data = barcode.data.decode('utf-8') # バーコードデータをUTF-8でデコード
                    barcode_type = barcode.type # バーコードタイプを取得

                    # バーコードデータの検証やデータベースへの登録など、必要な処理をここに追加
                    # 例: バーコードデータの長さをチェック
                    if len(barcode_data) != 10:
                        print(f"警告: バーコードデータの長さが不正です: {barcode_data}")
                        continue

                    # バーコードの状態を更新
                    status = self.barcode_manager.update_status(barcode_data, barcode_type)

                    # ユーザーインターフェースへの表示やログへの記録など、必要な処理をここに追加
                    print(f"バーコード: {barcode_data}, タイプ: {barcode_type}, ステータス: {status}")

                    barcode_info_end_time = time.time()
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tバーコード情報処理完了\t{barcode_info_end_time - barcode_info_start_time:.3f} 秒")

                # 期限切れ情報削除 (一定時間ごと)
                if current_time - self.last_expired_check_time >= 60: # 60秒ごとに実行
                    remove_start_time = time.time()
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t期限切れ情報削除開始")
                    self.remove_expired_data()
                    remove_end_time = time.time()
                    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t期限切れ情報削除完了\t{remove_end_time - remove_start_time:.3f} 秒")
                    self.last_expired_check_time = current_time

                display_start_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t画面表示開始")
                self.display(frame, barcodes)
                display_end_time = time.time()
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t画面表示完了\t{display_end_time - display_start_time:.3f} 秒")

                if auto_stop and len(self.barcode_data) >= self.expected_length:
                    break

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                self.last_frame_time = current_time # フレーム処理時間を更新

        finally:
            self.scanning = False
            self.cap.release()
            cv2.destroyAllWindows()

    def remove_expired_data(self): # メソッドを定義
        """期限切れ情報を削除する"""
        self.barcode_manager.remove_expired_barcodes() # BarcodeStatusManagerのメソッドを呼び出す


    def get_current_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    script_start_time = time.time()
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tスクリプト開始")
    scanner = BarcodeScanner()
    scanner.start(auto_stop=True)
    script_end_time = time.time()
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\tスクリプト終了\t{script_end_time - script_start_time:.3f} 秒")