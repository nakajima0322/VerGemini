# c:\temp\KHT_Python\VerGemini\G_ManualEntryDialog.py
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os

class ManualEntryDialog(tk.Toplevel):
    def __init__(self, parent, config, location, construction_number):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.location = location
        self.construction_number = construction_number
        
        # G_DrawingNumberViewer で使用されている発注伝票CSVのパスを取得
        self.source_csv_path_str = self.config.get("last_source_csv_path", "")


        self.title("図番による手動登録")
        self.geometry("700x450") # 少し広めに
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.result = None # 選択された部品情報

        # 設定値の取得
        self.order_no_col = self.config.get("source_csv_order_no_column", "発注伝票No.")
        self.drawing_no_col = self.config.get("source_csv_drawing_no_column", "図番")
        self.parts_no_col_name = self.config.get("source_csv_parts_no_column", "部品№")
        self.key_extract_start_0based = self.config.get("drawing_key_extraction_start_user", 8) - 1
        self.key_extract_length = self.config.get("drawing_key_extraction_length", 4)
        self.expected_length = self.config.get("expected_length", 10) # barcode_infoを0埋めするための期待長

        self._build_ui()
        self.source_data_list = self._load_source_data_internal() # 全データをリストとして最初に読み込む

        # モーダルにする
        self.grab_set()
        self.wait_window()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # 発注伝票CSVパス表示
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(pady=2, fill=tk.X)
        ttk.Label(path_frame, text="使用する発注伝票CSV:").pack(side=tk.LEFT, padx=5)
        self.csv_path_label = ttk.Label(path_frame, text=self.source_csv_path_str if self.source_csv_path_str else "未設定", foreground="blue")
        self.csv_path_label.pack(side=tk.LEFT, padx=5)


        # ソートキー入力
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=5, fill=tk.X)
        ttk.Label(input_frame, text=f"図番ソートキー ({self.key_extract_length}桁の数字):").pack(side=tk.LEFT, padx=5)
        self.sort_key_entry = ttk.Entry(input_frame, width=10)
        self.sort_key_entry.pack(side=tk.LEFT, padx=5)
        self.search_button = ttk.Button(input_frame, text="検索", command=self._on_search)
        self.search_button.pack(side=tk.LEFT, padx=5)
        self.sort_key_entry.bind("<Return>", lambda event: self._on_search())


        # 結果表示用Treeview
        columns = ("order_no", "drawing_no", "parts_no")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=10)
        self.tree.heading("order_no", text=self.order_no_col)
        self.tree.heading("drawing_no", text=self.drawing_no_col)
        self.tree.heading("parts_no", text=self.parts_no_col_name)

        self.tree.column("order_no", width=150, anchor=tk.W)
        self.tree.column("drawing_no", width=250, anchor=tk.W)
        self.tree.column("parts_no", width=150, anchor=tk.W)
        
        # スクロールバー
        tree_scrollbar_y = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scrollbar_x = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scrollbar_y.set, xscrollcommand=tree_scrollbar_x.set)

        self.tree.pack(pady=5, expand=True, fill=tk.BOTH, side=tk.LEFT)
        tree_scrollbar_y.pack(side=tk.LEFT, fill=tk.Y)
        tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X, before=self.tree) # Treeviewの下に配置

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_confirm_wrapper)


        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10, fill=tk.X, side=tk.BOTTOM) # 下部に配置
        self.confirm_button = ttk.Button(button_frame, text="確定", command=self._on_confirm, state=tk.DISABLED)
        self.confirm_button.pack(side=tk.RIGHT, padx=5)
        self.cancel_button = ttk.Button(button_frame, text="キャンセル", command=self._on_cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        self.sort_key_entry.focus_set()

    def _load_source_data_internal(self):
        """発注伝票CSVファイルを内部的に読み込む"""
        source_list = []
        filepath = self.source_csv_path_str
        if not filepath or not os.path.exists(filepath):
            messagebox.showerror("エラー", f"発注伝票CSVファイルが見つかりません:\n{filepath}\n\n図面番号照合ツールで一度正しいCSVファイルを開いてから再度お試しください。", parent=self)
            return []
        try:
            with open(filepath, mode='r', newline='', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                required_cols = [self.order_no_col, self.drawing_no_col, self.parts_no_col_name]
                missing_cols = [col for col in required_cols if col not in reader.fieldnames]
                if missing_cols:
                    messagebox.showerror("エラー",
                        f"発注伝票CSVに必要なカラム名が見つかりません:\n{', '.join(missing_cols)}", parent=self)
                    return []

                for row_data in reader:
                    order_no = row_data.get(self.order_no_col, "").strip()
                    drawing_no = row_data.get(self.drawing_no_col, "").strip()
                    parts_no = row_data.get(self.parts_no_col_name, "").strip()
                    if order_no and drawing_no:
                        source_list.append({
                            "order_no": order_no,
                            "drawing_no": drawing_no,
                            "parts_no": parts_no
                        })
            return source_list
        except Exception as e:
            messagebox.showerror("エラー", f"発注伝票CSVファイルの読み込み中にエラーが発生しました:\n{e}", parent=self)
            return []

    def _on_search(self):
        self.tree.delete(*self.tree.get_children())
        self.confirm_button.config(state=tk.DISABLED)

        search_key_input = self.sort_key_entry.get().strip()
        if not search_key_input.isdigit() or len(search_key_input) != self.key_extract_length:
            messagebox.showwarning("入力エラー", f"{self.key_extract_length}桁の数字でソートキーを入力してください。", parent=self)
            return

        if not self.source_data_list:
            # _load_source_data_internal でエラーメッセージ表示済みのはず
            return

        found_items = []
        for item_data in self.source_data_list:
            drawing_no_str = item_data.get("drawing_no")
            if drawing_no_str and isinstance(drawing_no_str, str) and \
               len(drawing_no_str) >= (self.key_extract_start_0based + self.key_extract_length):
                try:
                    extracted_key = drawing_no_str[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length]
                    if extracted_key == search_key_input:
                        found_items.append(item_data)
                except Exception:
                    continue

        if not found_items:
            messagebox.showinfo("検索結果", "該当する部品は見つかりませんでした。", parent=self)
            return

        for item in found_items:
            self.tree.insert("", tk.END, values=(item["order_no"], item["drawing_no"], item["parts_no"]))

        if len(found_items) == 1:
            first_item_id = self.tree.get_children()[0]
            self.tree.selection_set(first_item_id)
            self.tree.focus(first_item_id)
            self.confirm_button.config(state=tk.NORMAL)
        elif len(found_items) > 1:
            messagebox.showinfo("複数該当", "複数の部品が該当しました。リストから選択してください。", parent=self)

    def _on_tree_select(self, event):
        if self.tree.selection():
            self.confirm_button.config(state=tk.NORMAL)
        else:
            self.confirm_button.config(state=tk.DISABLED)

    def _on_confirm_wrapper(self, event=None):
        self._on_confirm()

    def _on_confirm(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("選択エラー", "部品を選択してください。", parent=self)
            return

        selected_item_id = selected_items[0]
        item_values = self.tree.item(selected_item_id, "values")

        order_no_raw = item_values[0]
        # barcode_info (発注伝票No.) を期待長まで先行ゼロでパディング
        padded_order_no = order_no_raw.zfill(self.expected_length)

        self.result = {
            "barcode_info": padded_order_no, # 0埋めされた発注伝票No.を使用
            "drawing_no": item_values[1],
            "parts_no": item_values[2],
            "barcode_type": "MANUAL" # バーコード種別をMANUALに設定
            # location, construction_number, timestamp は呼び出し元で付与
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def get_result(self):
        # self.parent.wait_window(self) # ダイアログの待機は __init__ 内の self.wait_window() で行われるため不要
        return self.result

if __name__ == "__main__":
    from G_config import Config # G_config.py が同じディレクトリかPYTHONPATHにある前提

    # 1. Configインスタンスの作成
    #    config.jsonがカレントディレクトリにあることを想定
    config_instance = Config("config.json")

    # 2. Tkinterのルートウィンドウ作成 (ダイアログの親として必要)
    #    ルートウィンドウ自体は表示しない
    root = tk.Tk()
    root.withdraw()

    # 3. テスト用のダミーデータ
    test_location = "テスト場所"
    test_construction_number = "9999"

    print("G_ManualEntryDialog を単体起動します...")
    print(f"テスト Location: {test_location}, テスト 工事番号: {test_construction_number}")
    print(f"使用する発注伝票CSV (config.jsonより): {config_instance.get('last_source_csv_path', '未設定')}")
    print("ダイアログを閉じるまで、この後の処理は待機します。")

    # 4. ManualEntryDialogのインスタンス作成と表示
    #    ダイアログの__init__内で grab_set() と wait_window() が呼ばれるため、モーダルとして動作
    dialog = ManualEntryDialog(root, config_instance, test_location, test_construction_number)

    # 5. 結果の取得と表示 (dialog.result に格納されている)
    selected_result = dialog.result
    print("\nダイアログの結果:", selected_result if selected_result else "何も選択されませんでした。")

    # 6. ルートウィンドウの破棄
    root.destroy()