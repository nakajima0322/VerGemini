# G_ScanBCD_FixCSV.py

import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk  # 追加

class CSVHandler:
    def __init__(self, csv_file, config):
        self.csv_file = csv_file
        self.config = config
        self.barcode_type = config.get("barcode_type", "CODE39")
        self.expected_length = config.get("expected_length", 10)
        self.expected_columns = ["barcode_info", "construction_number", "location", "barcode_type", "timestamp"]  # 修正

    def load_csv(self):
        try:
            with open(self.csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                data = list(reader)
        except FileNotFoundError:
            print(f"⚠ ファイルが見つかりません: {self.csv_file}")
            return []
        except Exception as e:
            print(f"⚠ エラーが発生しました: {e}")
            return []

        return data

    def save_csv(self, data):
        try:
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(data)
        except Exception as e:
            print(f"⚠ エラーが発生しました: {e}")

    def find_invalid_rows(self, data):
        invalid_rows = []
        for row in data:
            if len(row) != len(self.expected_columns):
                print(f"⚠ 不正な形式の行を検出しました: {row}")
                invalid_rows.append(row)
                continue

            barcode_info, construction_number, location, barcode_type, timestamp = row

            if barcode_type != self.barcode_type:
                print(f"⚠ 想定外のバーコード種類: {barcode_type} (行: {row})")
                invalid_rows.append(row)
                continue

            if len(barcode_info) != self.expected_length:
                print(f"⚠ バーコード長が異なります: {barcode_info} (期待値: {self.expected_length})")
                invalid_rows.append(row)
                continue

        return invalid_rows

    def find_duplicates(self):
        data = self.load_csv()
        if not data:
            return

        seen = {}
        duplicates = []
        invalid_rows = self.find_invalid_rows(data)

        for row in data:
            if len(row) != len(self.expected_columns):
                continue

            barcode_info, construction_number, location, barcode_type, timestamp = row

            if barcode_info in seen:
                existing_timestamp = seen[barcode_info][4]
                if timestamp > existing_timestamp:
                    duplicates.append(seen[barcode_info])
                    seen[barcode_info] = row
                else:
                    duplicates.append(row)
            else:
                seen[barcode_info] = row

        all_rows_to_remove = duplicates + invalid_rows

        if all_rows_to_remove:
            print(f"⚠ {len(all_rows_to_remove)} 件の削除対象データが見つかりました。")
            self.show_gui(seen, all_rows_to_remove)
        else:
            print("✅ 重複および不正データはありません。")

    def show_gui(self, unique_data, rows_to_remove):
        root = tk.Tk()
        root.title("削除対象データ確認")

        frame = ttk.Frame(root, padding=10)
        frame.grid()

        tree = ttk.Treeview(frame, columns=self.expected_columns, show="headings")
        for col in self.expected_columns:
            tree.heading(col, text=col)

        for row in rows_to_remove:
            tree.insert("", tk.END, values=row, tags="remove")
        tree.grid(row=0, column=0)
        tree.tag_configure("remove", background="lightcoral")

        def confirm_removal():
            selected_items = tree.selection()
            rows_to_keep = [tree.item(item)["values"] for item in selected_items]
            rows_to_remove_final = [row for row in rows_to_remove if row not in rows_to_keep]
            root.destroy()
            self.apply_removal(rows_to_remove_final)

        ttk.Button(frame, text="削除", command=confirm_removal).grid(row=1, column=0)
        ttk.Button(frame, text="キャンセル", command=root.destroy).grid(row=1, column=1)
        root.mainloop()

    def apply_removal(self, to_remove):
        data = self.load_csv()
        new_data = [row for row in data if row not in to_remove]

        if len(new_data) == len(data):
            print("✅ 削除するデータはありません。")
            return

        self.save_csv(new_data)
        print("✅ データを更新しました。")

if __name__ == "__main__":
    print("\n単体起動中...")
    from G_config import Config
    config = Config("config.json")

    # ファイル選択ダイアログを表示
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを表示しない
    root.attributes("-topmost", True)  # ダイアログを最前面に表示
    csv_file = filedialog.askopenfilename(
        title="対象のCSVファイルを選択してください",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if csv_file:
        handler = CSVHandler(csv_file, config)
        handler.find_duplicates()
    else:
        print("⚠ ファイルが選択されませんでした。")