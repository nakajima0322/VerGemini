# G_ProcessCsvWriter.py
import csv
import os
from datetime import datetime

class G_ProcessCsvWriter:
    def __init__(self, config, construction_no, process_name, supplier_name):
        self.config = config
        self.data_dir = self.config.get("data_dir", "data")
        self.construction_no = construction_no
        self.process_name = process_name
        self.supplier_name = supplier_name
        self.worker_name = self.config.get("current_worker", "unknown") # configから現在の作業者名を取得
        
        # この入力機会（セッション）のタイムスタンプを一度だけ生成
        self.work_session_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # 出力ファイル名とヘッダーを定義
        self.output_filepath = os.path.join(self.data_dir, f"{self.construction_no}_processed.csv")
        self.header = [
            "barcode_info", 
            "construction_number", 
            "process_name",
            "supplier_name",
            "work_session_id",
            "worker_name" # ヘッダーに作業者名を追加
        ]

    def write(self, barcode_info, barcode_type):
        """スキャンされたバーコード情報をCSVに書き込む"""
        try:
            file_exists = os.path.exists(self.output_filepath)
            header_needs_update = False

            # ファイルが存在する場合、ヘッダーをチェックする
            if file_exists and os.path.getsize(self.output_filepath) > 0:
                with open(self.output_filepath, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    try:
                        existing_header = next(reader)
                        if "worker_name" not in existing_header:
                            header_needs_update = True
                    except StopIteration:
                        # ファイルは存在するが空の場合
                        file_exists = False

            # ヘッダーの更新が必要な場合、ファイルを新しい形式で書き直す
            if header_needs_update:
                print(f"情報: 古い形式のファイル '{self.output_filepath}' を新しい形式に更新します。")
                with open(self.output_filepath, 'r', newline='', encoding='utf-8') as f_read:
                    reader = csv.reader(f_read)
                    old_data = list(reader)
                
                with open(self.output_filepath, 'w', newline='', encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerow(self.header) # 新しいヘッダー
                    # 古いデータの各行に空の作業者列を追加して書き込む
                    for row in old_data[1:]: # ヘッダー行はスキップ
                        writer.writerow(row + [''])

            # データを追記モードで書き込む
            with open(self.output_filepath, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # ファイルが新規作成されたか、空だった場合はヘッダーを書き込む
                if not file_exists or (file_exists and os.path.getsize(self.output_filepath) == 0):
                    writer.writerow(self.header)
                
                writer.writerow([barcode_info, self.construction_no, self.process_name, self.supplier_name, self.work_session_id, self.worker_name])
        except Exception as e:
            print(f"CSVファイル '{self.output_filepath}' への書き込み中にエラーが発生しました: {e}")