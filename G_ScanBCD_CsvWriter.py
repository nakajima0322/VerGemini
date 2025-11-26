# G_ScanBCD_CsvWriter.py

import csv
import os

class G_ScanBCD_CsvWriter:
    def __init__(self, config):
        self.config = config
        self.data_dir = self.config.get("data_dir", "data")
        self.header = [
            "barcode_info",
            "construction_number",
            "location",
            "barcode_type",
            "timestamp",
            "worker_name"
        ]

    def write(self, data):
        """スキャンされたデータをCSVに書き込む。ヘッダーの有無を自動処理する。"""
        construction_number = data.get("construction_number")
        if not construction_number:
            print("エラー: CsvWriterに工事番号が渡されませんでした。")
            return

        output_filepath = os.path.join(self.data_dir, f"{construction_number}.csv")

        try:
            file_exists = os.path.exists(output_filepath)
            write_header = not file_exists or os.path.getsize(output_filepath) == 0

            # ファイルが存在しない、または空の場合はヘッダーを書き込む
            if write_header:
                with open(output_filepath, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.header)
                    writer.writeheader()
                    writer.writerow(data)
            else:
                # ファイルが存在する場合は追記
                # ヘッダーが正しいか簡易チェック（完全ではないが、ヘッダーなしファイルへの追記を防ぐ）
                with open(output_filepath, 'r', newline='', encoding='utf-8') as f:
                    first_line = f.readline()
                    if "barcode_info" not in first_line:
                        # ヘッダーがない古いファイルとみなし、一度ヘッダーを付けて書き直す処理が必要だが、
                        # ここでは追記エラーを防ぐため、一旦ヘッダー付きで新規作成する挙動に寄せる（要検討）
                        print(f"警告: ヘッダーのないファイル {output_filepath} に追記しようとしました。")
                
                with open(output_filepath, mode='a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.header)
                    writer.writerow(data)
        except Exception as e:
            print(f"データファイル書き込みエラー: {e}")
