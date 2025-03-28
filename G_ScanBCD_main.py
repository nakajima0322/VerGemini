# G_ScanBCD_main.py

import os
import tkinter as tk
import json
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


if __name__ == "__main__":
    main()
