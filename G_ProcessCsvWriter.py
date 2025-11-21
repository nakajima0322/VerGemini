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
        
        # この入力機会（セッション）のタイムスタンプを一度だけ生成
        self.work_session_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # 出力ファイル名とヘッダーを定義
        self.output_filepath = os.path.join(self.data_dir, f"{self.construction_no}_processed.csv")
        self.header = [
            "barcode_info", 
            "construction_number", 
            "process_name",
            "supplier_name",
            "work_session_id"
        ]

    def write(self, barcode_info, barcode_type):
        """スキャンされたバーコード情報をCSVに書き込む"""
        file_exists = os.path.exists(self.output_filepath)
        
        try:
            with open(self.output_filepath, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists or os.path.getsize(self.output_filepath) == 0:
                    writer.writerow(self.header)
                
                writer.writerow([barcode_info, self.construction_no, self.process_name, self.supplier_name, self.work_session_id])
        except Exception as e:
            print(f"CSVファイル '{self.output_filepath}' への書き込み中にエラーが発生しました: {e}")