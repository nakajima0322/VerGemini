# G_ScanBCD_CsvWriter.py

import csv

class G_ScanBCD_CsvWriter:
    def __init__(self, config):
        self.config = config

    def write(self, data):
        # データをCSVファイルに出力
        try:
            with open(self.config.get("csv_file", "0000.csv"), mode='a', newline='', encoding='utf-8') as data_file:
                data_writer = csv.writer(data_file)
                data_writer.writerow(data.values())
        except Exception as e:
            print(f"データファイル書き込みエラー: {e}")
