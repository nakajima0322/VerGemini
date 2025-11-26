# G_ScanBCD_FixCSV.py

import csv
import os
import tkinter as tk
from tkinter import filedialog, ttk  # 追加

class CSVHandler:
    def __init__(self, csv_file, config):
        self.csv_file = csv_file
        self.config = config
        self.expected_length = config.get("expected_length", 10)

        # --- ファイルタイプに応じた設定を定義 ---
        if '_processed.csv' in os.path.basename(csv_file):
            self.file_type = 'process'
            self.new_header = ["barcode_info", "construction_number", "process_name", "supplier_name", "work_session_id", "worker_name"]
            self.old_header = ["barcode_info", "construction_number", "process_name", "supplier_name", "work_session_id"]
            self.primary_key_col = "barcode_info"
        else:
            self.file_type = 'location'
            self.new_header = ["barcode_info", "construction_number", "location", "barcode_type", "timestamp", "worker_name"]
            self.old_header = ["barcode_info", "construction_number", "location", "barcode_type", "timestamp"]
            self.primary_key_col = "barcode_info"
            self.timestamp_col = "timestamp"
        
        # 保存時に使用するヘッダーは常に新しい形式
        self.header_to_save = self.new_header

    def load_csv(self):
        """CSVファイルを読み込み、新旧フォーマットを吸収して統一された辞書のリストを返す。"""
        data = []
        try:
            with open(self.csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                try:
                    first_row = next(reader)
                except StopIteration:
                    return [] # 空ファイル

                # 1行目がヘッダーかどうかを判定
                if set(first_row) == set(self.new_header):
                    # 新しい形式のファイル
                    for row in reader:
                        data.append(dict(zip(self.new_header, row)))
                elif set(first_row) == set(self.old_header):
                    # 古い形式のファイル
                    print(f"情報: 古い形式のファイル '{os.path.basename(self.csv_file)}' を検出しました。保存時に新しい形式に更新します。")
                    # ヘッダー行のデータを辞書化
                    old_data_with_header = [first_row] + list(reader)
                    for row in old_data_with_header:
                        row_dict = dict(zip(self.old_header, row))
                        row_dict['worker_name'] = '' # worker_nameを補完
                        data.append(row_dict)
                else: # ヘッダーなしファイル (古い保管場所データ) or 不正なヘッダー
                    if self.file_type == 'location':
                        print(f"情報: ヘッダーのない古い保管場所データファイルを検出しました。保存時に新しい形式に更新します。 ('{os.path.basename(self.csv_file)}')")
                        all_rows = [first_row] + list(reader)
                        for row in all_rows:
                            if len(row) == len(self.old_header):
                                row_dict = dict(zip(self.old_header, row))
                                row_dict['worker_name'] = '' # worker_nameを補完
                                data.append(row_dict)
                    else: # 工程ファイルでヘッダーが不正な場合
                        print(f"⚠ 警告: ファイル '{self.csv_file}' のヘッダーが不正です。\n   期待されるヘッダー: {self.new_header} または {self.old_header}\n   実際のヘッダー: {first_row}")
                        return []

        except FileNotFoundError:
            print(f"⚠ ファイルが見つかりません: {self.csv_file}")
            return []
        except Exception as e:
            print(f"⚠ エラーが発生しました: {e}")
            return []
        return data

    def save_csv(self, data):
        """辞書のリストをCSVファイルに書き込む。常にヘッダー付きで保存。"""
        try:
            with open(self.csv_file, mode='w', newline='', encoding='utf-8') as file:
                if not data:
                    return
                
                # 常に新しいヘッダーで書き込む
                writer = csv.DictWriter(file, fieldnames=self.header_to_save)
                writer.writeheader()
                writer.writerows(data)
        except Exception as e:
            print(f"⚠ エラーが発生しました: {e}")

    def _find_invalid_rows(self, data):
        """不正な行を見つける。バーコード長のみをチェックするシンプルなロジックに。"""
        invalid_rows = []
        for row in data:
            # 列数はload_csvでチェック済み
            barcode_info = row.get(self.primary_key_col, "")
            
            # バーコード長チェック
            if len(barcode_info) != self.expected_length:
                print(f"⚠ バーコード長が異なります: {barcode_info} (期待値: {self.expected_length})")
                invalid_rows.append(row)
                continue
        return invalid_rows

    def find_duplicates_and_invalid_rows(self):
        """重複データと不正データを検出し、修正のためのGUIを表示するメインの処理。"""
        data = self.load_csv()
        if not data:
            print("✅ ファイルが空か、読み込めませんでした。処理を終了します。")
            return

        seen = {}
        duplicates = []
        invalid_rows = self._find_invalid_rows(data)

        for row in data:
            # 不正な行は重複チェックの対象外とする
            if row in invalid_rows:
                continue

            barcode_info = row.get(self.primary_key_col, "")
            if barcode_info in seen:
                # 重複が見つかった
                if self.file_type == 'location':
                    # タイムスタンプで比較
                    existing_timestamp = seen[barcode_info].get(self.timestamp_col, '0')
                    current_timestamp = row.get(self.timestamp_col, '0')
                    if current_timestamp > existing_timestamp:
                        duplicates.append(seen[barcode_info]) # 古い方を削除リストへ
                        seen[barcode_info] = row # 新しい方で上書き
                    else:
                        duplicates.append(row) # 現在の行が古いので削除リストへ
                else: # process
                    # 後勝ちなので、先に見つかった方を削除リストへ
                    duplicates.append(seen[barcode_info])
                    seen[barcode_info] = row # 新しい方で上書き
            else:
                # 初めて見るバーコード
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

        frame = ttk.Frame(root, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        # frame内でgridを使うために、列と行の伸縮設定を行う
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=self.header_to_save, show="headings")
        for col in self.header_to_save:
            tree.heading(col, text=col)

        for row in rows_to_remove:
            tree.insert("", tk.END, values=list(row.values()), tags="remove")
        tree.grid(row=0, column=0, sticky="nsew") # gridを使用
        tree.tag_configure("remove", background="lightcoral")

        def confirm_removal():
            selected_items = tree.selection()
            # 削除対象から除外する行（ユーザーが残すことを選択した行）を特定
            rows_to_keep_values = [tuple(tree.item(item)["values"]) for item in selected_items]
            rows_to_remove_final = [row for row in rows_to_remove if tuple(str(v) for v in row.values()) not in rows_to_keep_values]
            root.destroy()
            self.apply_removal(rows_to_remove_final)

        # ボタンを配置するためのフレーム
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, pady=(10, 0), sticky="e") # gridを使用
        ttk.Button(button_frame, text="選択した行を削除", command=confirm_removal).pack(side=tk.RIGHT, padx=5) # button_frame内ではpackでOK
        ttk.Button(button_frame, text="キャンセル", command=root.destroy).pack(side=tk.RIGHT)
        root.mainloop()

    def apply_removal(self, to_remove):
        data = self.load_csv()
        # to_remove は辞書のリストなので、比較のために元のデータも辞書にする必要があるが、
        # load_csvが辞書のリストを返すので、単純な比較でOK
        # ただし、行の順序を維持するために、元のデータから削除する方が安全
        to_remove_set = {tuple(d.items()) for d in to_remove}
        new_data = [row for row in data if tuple(row.items()) not in to_remove_set]

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
        handler.find_duplicates_and_invalid_rows()
    else:
        print("⚠ ファイルが選択されませんでした。")