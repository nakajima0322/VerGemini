import csv
import os
from typing import List, Dict, Any # AnyをDictに変更検討
from G_config import Config  # G_config.py が同じディレクトリかPYTHONPATHにある前提

def _normalize_id_string(id_str: str) -> str:
    """
    ID文字列を正規化します。
    1. 先頭のゼロを削除します。
    2. 削除の結果が空文字列になった場合（元が "0", "00" など全てゼロだった場合）、"0" を返します。
    3. それ以外の場合は、先頭ゼロを削除した文字列を返します。
    4. 入力が空文字列の場合は、空文字列を返します。
    """
    if not id_str:
        return ""
    stripped_id = id_str.lstrip('0')
    if not stripped_id:  # 元が "0", "00", "000" など
        return "0"
    return stripped_id

def load_scan_data(filepath: str) -> List[Dict[str, str]]:

    """
    スキャンデータCSV (例: 3804.csv) を読み込み、
    各要素が {"barcode": バーコード値, "location": 保管場所の値} の辞書であるリストを返します。
    想定されるCSVの列: 0番目がバーコード情報、2番目が保管場所情報。
    """
    scanned_items: List[Dict[str, str]] = []
    if not os.path.exists(filepath):
        print(f"エラー: スキャンデータファイルが見つかりません: {filepath}")
        return scanned_items
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            # G_ScanBCD_Scanner.py の出力にはヘッダーがない想定
            for row_number, row in enumerate(reader, 1):
                if row and len(row) > 0:
                    barcode_value = row[0].strip() # バーコードは0列目
                    location_value = ""  # デフォルトは空文字
                    if len(row) >= 3:  # 保管場所情報が期待される3列目 (インデックス2) にあるか
                        location_value = row[2].strip()
                    else:
                        print(f"情報: スキャンデータファイル ({filepath}) の {row_number}行目に保管場所情報がありません (列数: {len(row)})。保管場所は空として扱います。")

                    if barcode_value:  # 空のバーコードは無視
                        scanned_items.append({"barcode": barcode_value, "location": location_value})
                    else:
                        print(f"情報: スキャンデータファイル ({filepath}) の {row_number}行目に空のバーコード値がありました。スキップします。")
        if not scanned_items:
            print(f"情報: スキャンデータファイル ({filepath}) は空か、有効なデータがありませんでした。")
    except Exception as e:
        print(f"エラー: スキャンデータファイル ({filepath}) の読み込み中にエラー: {e}")
    return scanned_items

def load_source_data(
    filepath: str,
    order_col_name: str,
    drawing_col_name: str,
    parts_col_name: str,
    delivery_col_name_in_source: str
) -> Dict[str, Dict[str, str]]:
    """
    発注伝票CSV (例: 3804s.csv) を読み込み、正規化された発注伝票No.をキーとする辞書を返す。
    値の辞書には、図番, 部品№, 納入数が含まれる。
    """
    source_map = {}
    if not os.path.exists(filepath):
        print(f"エラー: 発注伝票CSVファイルが見つかりません: {filepath}")
        return source_map
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8-sig') as file: # utf-8-sig でBOM対応
            reader = csv.DictReader(file)
            
            required_cols_in_source = [order_col_name, drawing_col_name, parts_col_name, delivery_col_name_in_source]
            missing_cols = [col for col in required_cols_in_source if col not in reader.fieldnames]
            if missing_cols:
                print(f"エラー: 発注伝票CSVに必要なカラム名が見つかりません: {', '.join(missing_cols)}")
                print(f"    期待されるカラム名: {order_col_name}, {drawing_col_name}, {parts_col_name}, {delivery_col_name_in_source}")
                print(f"    CSVファイルのヘッダー: {reader.fieldnames}")
                return source_map

            for row_number, row_data in enumerate(reader, 2): # ヘッダー行の次からなので2から開始
                order_no_from_csv = row_data.get(order_col_name, "").strip()
                drawing_no = row_data.get(drawing_col_name, "").strip()
                parts_no = row_data.get(parts_col_name, "").strip()
                delivery_count = row_data.get(delivery_col_name_in_source, "0").strip()

                if order_no_from_csv:
                    normalized_order_no = _normalize_id_string(order_no_from_csv)
                    # 同じ正規化キーが複数ある場合、後勝ちになる。
                    # もし集計などが必要なら、ここのロジック変更が必要。
                    if normalized_order_no in source_map:
                        print(f"情報: 発注伝票CSV ({filepath}) の {row_number}行目: 発注伝票№ '{order_no_from_csv}' (正規化後 '{normalized_order_no}') が重複しています。以前のデータが上書きされます。")
                    
                    source_map[normalized_order_no] = {
                        "drawing": drawing_no,
                        "parts": parts_no,
                        "delivery_count": delivery_count
                    }
            if not source_map:
                print(f"情報: 発注伝票CSV ({filepath}) は空か、有効なデータがありませんでした。")
    except Exception as e:
        print(f"エラー: 発注伝票CSV ({filepath}) の読み込み中にエラー: {e}")
    return source_map

def create_combined_csv() -> None:
    # 設定ファイルのロード
    try:
        config = Config("config.json") # config.jsonがカレントディレクトリにある想定
    except FileNotFoundError:
        print(f"エラー: 設定ファイル 'config.json' がカレントディレクトリに見つかりません。")
        return
    except Exception as e:
        print(f"エラー: config.json の読み込みに失敗しました: {e}")
        return

    data_dir = config.get("data_dir", "data")
    source_data_dir = config.get("source_data_dir", "Source")

     # ファイル名はconfigから取得するか、引数で渡すことを検討 (今回は固定のまま)
    # G_ScanBCD_main.py や G_DrawingNumberViewer.py との連携を考えると、
    # 工事番号に基づいて動的にファイル名が決まる方が望ましい
    construction_no = config.get("last_construction_number", "3804") # 例として前回値を使用
    scan_csv_filename = f"{construction_no}.csv"
    source_csv_filename = f"{construction_no}s.csv" # 発注伝票CSVの命名規則に合わせる
    result_csv_filename = f"{construction_no}result.csv"

    scan_csv_path = os.path.join(data_dir, scan_csv_filename) # dataディレクトリ内の工事番号.csv
    source_csv_path = os.path.join(source_data_dir, source_csv_filename)
    result_csv_path = os.path.join(data_dir, result_csv_filename) 
    
    print(f"スキャンデータCSV: {os.path.abspath(scan_csv_path)}")
    print(f"発注伝票CSV: {os.path.abspath(source_csv_path)}")
    print(f"結果出力CSV: {os.path.abspath(result_csv_path)}")

    order_no_col_name_cfg = config.get("source_csv_order_no_column", "発注伝票№")
    drawing_no_col_name_cfg = config.get("source_csv_drawing_no_column", "図番")
    parts_no_col_name_cfg = config.get("source_csv_parts_no_column", "部品№")
    delivery_count_col_name_src = "納入数" # ソースCSVのヘッダー名として固定

    scanned_data_list = load_scan_data(scan_csv_path)
    if not scanned_data_list:
        print(f"処理を中断します: スキャンデータ ({scan_csv_path}) が読み込めなかったか、データが空です。")
        return

    source_data_map = load_source_data(source_csv_path,
                                       order_no_col_name_cfg,
                                       drawing_no_col_name_cfg,
                                       parts_no_col_name_cfg,
                                       delivery_count_col_name_src)
    if not source_data_map:
        print(f"処理を中断します: 発注伝票データ ({source_csv_path}) が読み込めなかったか、データが空です。")
        return

    results_data_list: List[List[str]] = []
    output_csv_header = ["バーコード値", "部品№", "図番№", "納入数", "保管場所"] # ヘッダーに「保管場所」を追加
    results_data_list.append(output_csv_header)

    for scanned_item in scanned_data_list:
        original_barcode_val = scanned_item["barcode"]
        location_val = scanned_item["location"]

        normalized_barcode_for_lookup = _normalize_id_string(original_barcode_val)

        source_item_info = source_data_map.get(normalized_barcode_for_lookup)

        if source_item_info:
            results_data_list.append([
                original_barcode_val,
                source_item_info["parts"],
                source_item_info["drawing"],
                source_item_info["delivery_count"],
                location_val # 保管場所を追加
            ])
        else:
            results_data_list.append([
                original_barcode_val,
                "", # 部品№なし
                "", # 図番なし
                "", # 納入数なし
                location_val # 保管場所を追加
            ])
            # print(f"情報: バーコード '{original_barcode_val}' (正規化後: '{normalized_barcode_for_lookup}') に対応する発注情報が見つかりません。")

    data_rows_count = len(results_data_list) - 1 # ヘッダー除く
    if data_rows_count > 0:
        try:
            output_dir = os.path.dirname(result_csv_path)
            if output_dir and not os.path.exists(output_dir): # output_dirが空文字列でないことを確認
                os.makedirs(output_dir)
            
            with open(result_csv_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(results_data_list)

            # 発注情報と紐づいたデータ（部品№, 図番, 納入数のいずれかがあるもの）
            found_match_count = sum(1 for row in results_data_list[1:] if row[1] or row[2] or row[3])
            no_match_count = data_rows_count - found_match_count

            print(f"\n処理完了。結果を {result_csv_path} に保存しました。")
            print(f" - 発注情報と紐づいたデータ: {found_match_count}件")
            print(f" - 発注情報が見つからなかったデータ: {no_match_count}件")
            print(f" - スキャンデータ総件数: {len(scanned_data_list)}件")
            print(f" - 出力データ総件数 (ヘッダー除く): {data_rows_count}件")
        except Exception as e:
            print(f"エラー: 結果ファイル ({result_csv_path}) の書き込み中にエラーが発生しました: {e}")
    else:
        print("処理対象のデータがなかったため、結果ファイルは作成されませんでした。")

if __name__ == "__main__":
    create_combined_csv()
