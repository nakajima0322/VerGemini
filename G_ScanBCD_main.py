# G_ScanBCD_main.py

import sys
import subprocess
import os
import json
import tkinter as tk
from tkinter import ttk
from G_ScanBCD_Location import LocationSelector
from G_ScanBCD_Scanner import BarcodeScanner
from G_ScanBCD_FixCSV import CSVHandler
from G_config import Config
from G_ScanBCD_Results import ResultDisplay


def load_configuration():
    """Loads the configuration from config.json."""
    print("設定ファイルを読み込んでいます...")
    try:
        config = Config("config.json")
        return config
    except FileNotFoundError:
        print("Error: 設定ファイル (config.json) が見つかりません。")
        return None
    except json.JSONDecodeError:
        print("Error: 設定ファイル (config.json) の形式が不正です。")
        return None
    except ValueError as e:
        print(f"Error: 設定ファイル (config.json) にエラーがあります: {e}")
        return None


def select_location_and_construction(config):
    """Handles the location and construction number selection."""
    print("場所と工事番号を選択してください...")
    location_selector = LocationSelector(config)
    location, construction_number = location_selector.get_location()

    if not location:
        print("⚠ 場所が選択されませんでした。処理を中止します。")
        return None, None

    print(f"✅ 選択された場所: {location}, 工事番号: {construction_number}")
    return location, construction_number


def start_barcode_scanning(config, location, construction_number):
    """Initializes and starts the barcode scanner."""
    print("バーコードスキャナーを起動しています...")
    scanner = BarcodeScanner(
        config=config, location=location, construction_number=construction_number
    )
    scanner.start()
    return scanner


def run_csv_duplicate_check(config, construction_number):
    """Runs the CSV duplicate check."""
    print("CSVの重複チェックを実行しています...")
    csv_file = os.path.join("data", f"{construction_number}.csv")
    handler = CSVHandler(csv_file, config)
    handler.find_duplicates()


def show_tool_launcher_dialog():
    """Displays a dialog to choose which subsequent tools to launch."""
    root = tk.Tk()
    root.title("ツール起動選択")

    # --- State Variables ---
    launch_drawing_viewer = tk.BooleanVar(value=True)
    launch_part_viewer = tk.BooleanVar(value=False)
    result = {"launch": False}

    # --- UI Setup ---
    frame = ttk.Frame(root, padding="20")
    frame.pack(expand=True, fill=tk.BOTH)

    ttk.Label(frame, text="次に起動するツールを選択してください:", font=("-size", 10)).pack(pady=(0, 10))

    # Checkboxes
    check_frame = ttk.Frame(frame)
    check_frame.pack(fill=tk.X, padx=5)
    ttk.Checkbutton(check_frame, text="保管場所照合ツール (G_DrawingNumberViewer.py)", variable=launch_drawing_viewer).pack(anchor=tk.W)
    ttk.Checkbutton(check_frame, text="部品情報表示ツール (G_PartInfoViewer.py)", variable=launch_part_viewer).pack(anchor=tk.W)

    # --- Button Logic ---
    def on_launch():
        result["launch"] = True
        root.destroy()

    def on_skip():
        result["launch"] = False
        root.destroy()

    # Buttons
    button_frame = ttk.Frame(frame)
    button_frame.pack(pady=(15, 0))
    ttk.Button(button_frame, text="起動", command=on_launch, width=10).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="スキップ", command=on_skip, width=10).pack(side=tk.LEFT, padx=5)
    
    # --- Window Positioning ---
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = root.winfo_reqwidth()
    window_height = root.winfo_reqheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"+{x}+{y}")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.focus_force()

    root.mainloop()

    # --- Post-Dialog Logic ---
    if result["launch"]:
        if launch_drawing_viewer.get():
            print("図面番号照合ツールを起動します...")
            try:
                subprocess.Popen([sys.executable, "G_DrawingNumberViewer.py"])
            except FileNotFoundError:
                print("エラー: G_DrawingNumberViewer.py が見つからないか、Pythonインタープリタのパスに問題があります。")
            except Exception as e:
                print(f"図面番号照合ツールの起動中にエラーが発生しました: {e}")

        if launch_part_viewer.get():
            print("部品情報表示ツールを起動します...")
            try:
                subprocess.Popen([sys.executable, "G_PartInfoViewer.py"])
            except FileNotFoundError:
                print("エラー: G_PartInfoViewer.py が見つからないか、Pythonインタープリタのパスに問題があります。")
            except Exception as e:
                print(f"部品情報表示ツールの起動中にエラーが発生しました: {e}")


def main():
    """Main function to run the barcode scanning application."""
    print("実行しています...")
    
    config = load_configuration()
    if config is None:
        return

    location, construction_number = select_location_and_construction(config)
    if location is None:
        return

    scanner = start_barcode_scanning(config, location, construction_number)
    if scanner is None:
        return

    run_csv_duplicate_check(config, construction_number)

    # ResultDisplay クラスのインスタンスを作成
    result_display = ResultDisplay()
    # show_results メソッドを呼び出し、スキャン結果を表示
    result_display.show_results(scanner.scan_count, location, construction_number)

    # 後続ツールの起動選択ダイアログを表示
    show_tool_launcher_dialog()

    print("バーコードスキャンアプリケーションのメイン処理を終了します。")


if __name__ == "__main__":
    print("起動中...")
    main()
