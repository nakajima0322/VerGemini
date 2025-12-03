﻿import csv
import os
import sys
from typing import List, Dict
from G_config import Config
from G_ScanBCD_FixCSV import CSVHandler # CSVHandlerをインポート

def _normalize_id_string(id_str: str) -> str:
    """ID文字列を正規化 (先頭ゼロ削除、オールゼロなら"0")"""
    if not id_str:
        return ""
    stripped_id = id_str.lstrip('0')
    return stripped_id if stripped_id else "0"

def load_source_data(
    filepath: str,
    order_col_name: str,
    drawing_col_name: str,
    parts_col_name: str,
) -> Dict[str, Dict[str, str]]:
    """
    発注伝票CSV (例: 3804s.csv) を読み込み、正規化された発注伝票No.をキーとする辞書を返す。
    """
    source_map = {}
    if not os.path.exists(filepath):
        print(f"エラー: 発注伝票CSVファイルが見つかりません: {filepath}")
        return source_map
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8-sig') as file: # utf-8-sig でBOM対応
            reader = csv.DictReader(file)
            
            required_cols_in_source = [order_col_name, drawing_col_name, parts_col_name]
            missing_cols = [col for col in required_cols_in_source if col not in reader.fieldnames]
            if missing_cols:
                print(f"エラー: 発注伝票CSVに必要なカラム名が見つかりません: {', '.join(missing_cols)}. ファイル: {os.path.basename(filepath)}")
                print(f"    期待されるカラム名: {order_col_name}, {drawing_col_name}, {parts_col_name}")
                print(f"    CSVファイルのヘッダー: {reader.fieldnames}")
                return source_map

            for row_number, row_data in enumerate(reader, 2): # ヘッダー行の次からなので2から開始
                order_no_from_csv = row_data.get(order_col_name, "").strip()
                drawing_no = row_data.get(drawing_col_name, "").strip()
                parts_no = row_data.get(parts_col_name, "").strip()

                if order_no_from_csv:
                    normalized_order_no = _normalize_id_string(order_no_from_csv)
                    if normalized_order_no in source_map:
                        print(f"情報: 発注伝票CSV ({filepath}) の {row_number}行目: 発注伝票№ '{order_no_from_csv}' (正規化後 '{normalized_order_no}') が重複しています。以前のデータが上書きされます。")
                    
                    source_map[normalized_order_no] = {
                        "drawing": drawing_no,
                        "parts": parts_no,
                        # 他に必要な情報があればここに追加
                    }
            if not source_map:
                print(f"情報: 発注伝票CSV ({filepath}) は空か、有効なデータがありませんでした。")
    except Exception as e:
        print(f"エラー: 発注伝票CSV ({filepath}) の読み込み中にエラー: {e}")
    return source_map

def create_combined_csv() -> None:
    try:
        config = Config("config.json")
    except FileNotFoundError:
        print("エラー: 設定ファイル 'config.json' がカレントディレクトリに見つかりません。")
        return
    except Exception as e:
        print(f"エラー: config.json の読み込みに失敗しました: {e}")
        return
    
    # --- ファイルパスの決定 ---
    data_dir = config.get("data_dir", "data")
    source_data_dir = config.get("source_data_dir", "Source")
    
    # コマンドライン引数から工事番号を取得、なければconfigから取得
    if len(sys.argv) > 1:
        construction_no = sys.argv[1]
        print(f"コマンドライン引数から工事番号 '{construction_no}' を使用します。")
    else:
        construction_no = config.get("last_construction_number", "")
        if not construction_no:
            print("エラー: 工事番号が指定されていません。コマンドライン引数で渡すか、config.jsonの'last_construction_number'を設定してください。")
            return
        print(f"設定ファイルから工事番号 '{construction_no}' を使用します。")
    
    scan_csv_filename = f"{construction_no}.csv"
    source_csv_filename = f"{construction_no}s.csv"
    process_csv_filename = f"{construction_no}_processed.csv"
    result_csv_filename = f"{construction_no}result.csv"

    scan_csv_path = os.path.join(data_dir, scan_csv_filename)
    source_csv_path = os.path.join(source_data_dir, source_csv_filename)
    process_csv_path = os.path.join(data_dir, process_csv_filename)
    result_csv_path = os.path.join(data_dir, result_csv_filename) 
    
    print(f"スキャンデータCSV: {os.path.abspath(scan_csv_path)}")
    print(f"工程データCSV: {os.path.abspath(process_csv_path)}")
    print(f"発注伝票CSV: {os.path.abspath(source_csv_path)}")
    print(f"結果出力CSV: {os.path.abspath(result_csv_path)}")

    # --- カラム名の設定 ---
    order_no_col_name_cfg = config.get("source_csv_order_no_column", "発注伝票№")
    drawing_no_col_name_cfg = config.get("source_csv_drawing_no_column", "図番")
    parts_no_col_name_cfg = config.get("source_csv_parts_no_column", "部品№")

    # --- データの読み込み ---
    # CSVHandlerを使用して、新旧フォーマットを吸収しながら読み込む
    scan_data_handler = CSVHandler(scan_csv_path, config)
    scanned_data_list = scan_data_handler.load_csv()
    if not scanned_data_list:
        print(f"処理を中断します: スキャンデータ ({scan_csv_path}) が読み込めなかったか、データが空です。")
        return

    process_data_handler = CSVHandler(process_csv_path, config)
    process_data_list = process_data_handler.load_csv()
    # 工程データをバーコードをキーにした辞書に変換（後勝ちで最新情報を保持）
    process_data_map = {
        _normalize_id_string(row.get("barcode_info", "")): row
        for row in process_data_list if row.get("barcode_info")
    }

    source_data_map = load_source_data(source_csv_path,
                                       order_no_col_name_cfg,
                                       drawing_no_col_name_cfg,
                                       parts_no_col_name_cfg)
    if not source_data_map:
        print(f"処理を中断します: 発注伝票データ ({source_csv_path}) が読み込めなかったか、データが空です。")
        return

    # --- データの結合 ---
    results_data_list: List[Dict[str, str]] = []
    output_csv_header = ["barcode_info", "parts_no", "drawing_no", "location", "process_name", "supplier_name", "work_session_id", "worker_name"]

    for scanned_item in scanned_data_list:
        original_barcode_val = scanned_item.get("barcode_info", "")
        normalized_barcode_for_lookup = _normalize_id_string(original_barcode_val)
        
        source_item_info = source_data_map.get(normalized_barcode_for_lookup)
        process_item_info = process_data_map.get(normalized_barcode_for_lookup)

        combined_row = {
            "barcode_info": original_barcode_val,
            "parts_no": source_item_info.get("parts", "") if source_item_info else "",
            "drawing_no": source_item_info.get("drawing", "") if source_item_info else "",
            "location": scanned_item.get("location", ""),
            "process_name": process_item_info.get("process_name", "") if process_item_info else "",
            "supplier_name": process_item_info.get("supplier_name", "") if process_item_info else "",
            "work_session_id": process_item_info.get("work_session_id", "") if process_item_info else "",
            "worker_name": scanned_item.get("worker_name", "") # スキャンデータから作業者名を取得
        }
        results_data_list.append(combined_row)

    # --- ファイルへの書き込み ---
    if results_data_list:
        try:
            output_dir = os.path.dirname(result_csv_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with open(result_csv_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=output_csv_header)
                writer.writeheader()
                writer.writerows(results_data_list)

            found_match_count = sum(1 for row in results_data_list if row["parts_no"] or row["drawing_no"])
            no_match_count = len(results_data_list) - found_match_count

            print(f"\n処理完了。結果を {result_csv_path} に保存しました。")
            print(f" - 発注情報と紐づいたデータ: {found_match_count}件")
            print(f" - 発注情報が見つからなかったデータ: {no_match_count}件")
            print(f" - 出力データ総件数: {len(results_data_list)}件")
        except Exception as e:
            print(f"エラー: 結果ファイル ({result_csv_path}) の書き込み中にエラーが発生しました: {e}")
    else:
        print("処理対象のデータがなかったため、結果ファイルは作成されませんでした。")

if __name__ == "__main__":
    try:
        create_combined_csv()
    except Exception as e:
        print(f"致命的なエラー: {e}")
    print("結合CSV作成処理を終了します。")
    input("何かキーを押すと終了します...") # コンソールがすぐに閉じないように
