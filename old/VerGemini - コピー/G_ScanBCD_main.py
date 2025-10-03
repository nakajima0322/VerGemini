# G_ScanBCD_main.py

import os
import csv
import tkinter as tk
from tkinter import ttk
from G_ScanBCD_Location import LocationSelector
from G_ScanBCD_Scanner import BarcodeScanner
from G_ScanBCD_FixCSV import CSVHandler  # 追加
from G_config import Config

def show_scan_results(scan_count, csv_file, location, construction_number):
    # ダイアログウィンドウを作成
    root = tk.Tk()
    root.title("スキャン結果")

    # ウィジェットの作成
    construction_label_title = tk.Label(root, text="工事番号:", font=("Helvetica", 16))
    construction_label_title.pack(pady=5)
    construction_label = tk.Label(root, text=f"{construction_number}", font=("Helvetica", 20))
    construction_label.pack(pady=10)

    location_label_title = tk.Label(root, text="保管場所:", font=("Helvetica", 16))
    location_label_title.pack(pady=5)
    location_label = tk.Label(root, text=f"{location}", font=("Helvetica", 20))
    location_label.pack(pady=10)

    scan_count_label_title = tk.Label(root, text="スキャンしたバーコードの数:", font=("Helvetica", 16))
    scan_count_label_title.pack(pady=5)
    scan_count_label = tk.Label(root, text=f"{scan_count}", font=("Helvetica", 20))
    scan_count_label.pack(pady=10)

    close_button = tk.Button(root, text="閉じる", command=root.destroy, font=("Helvetica", 14))
    close_button.pack(pady=10)

    # ウィンドウのサイズを自動調整
    root.update_idletasks()  # ウィジェットのサイズを計算
    extra_width = 50  # 幅方向に余裕を追加
    extra_height = 20  # 高さ方向に余裕を追加
    window_width = root.winfo_reqwidth() + extra_width
    window_height = root.winfo_reqheight() + extra_height

    # ウィンドウの位置を画面の右寄せで表示
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - window_width - 10  # 右端から10ピクセル内側
    y = 10  # 上端から10ピクセル下
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # ダイアログを表示
    root.mainloop()

def main():
    config = Config("config.json")

    location_selector = LocationSelector(config)
    location, construction_number = location_selector.get_location()

    if not location:
        print("⚠ 場所が選択されませんでした。処理を中止します。")
        return

    print(f"✅ 選択された場所: {location}, 工事番号: {construction_number}")

    scanner = BarcodeScanner(config=config, location=location, construction_number=construction_number)
    scanner.start()

    # CSV 重複削除処理の追加
    csv_file = os.path.join("data", f"{construction_number}.csv")  # 修正: CSVファイルのパスを修正
    handler = CSVHandler(csv_file, config)
    handler.find_duplicates()

    # スキャン結果をダイアログで表示
    show_scan_results(scanner.scan_count, csv_file, location, construction_number)

if __name__ == "__main__":
    main()