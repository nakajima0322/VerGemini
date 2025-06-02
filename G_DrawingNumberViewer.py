# G_DrawingNumberViewer.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
from G_config import Config # 既存のConfigクラスを利用

class DrawingNumberViewer:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("図面番号照合ツール")

        # 設定値の取得
        self.data_dir = self.config.get("data_dir", "data")
        self.source_data_dir = self.config.get("source_data_dir", "Source")
        self.default_source_csv_filename = self.config.get("default_source_csv_filename", "")
        self.order_no_col = self.config.get("source_csv_order_no_column", "発注伝票No.")
        self.drawing_no_col = self.config.get("source_csv_drawing_no_column", "図面番号")
        self.parts_no_col_name = self.config.get("source_csv_parts_no_column", "部品№") # configから部品№カラム名取得
        self.no_barcode_type_str = self.config.get("no_barcode_type", "NO_BARCODE") # バーコードなし部品のタイプ
        self.manual_drawing_barcode_type_str = self.config.get("manual_entry_drawing_barcode_type", "MANUAL_DRAWING") # 図番手動登録タイプ

        # 図番からのキー抽出設定 (config.json から読み込み)
        # ユーザー設定は1始まり、内部処理用に0始まりに変換
        self.key_extract_start_0based = self.config.get("drawing_key_extraction_start_user", 8) - 1
        self.key_extract_length = self.config.get("drawing_key_extraction_length", 4)

        # フィルター開始値のデフォルト値と前回値の読み込み
        self.default_filter_start_val = self.config.get("default_filter_start_value", 0)
        # self.expected_length = self.config.get("expected_length", 10) # 0除去比較のため不要に

        # 前回保存された発注伝票CSVパスを読み込む
        last_source_csv = self.config.get("last_source_csv_path", "")
        self.source_csv_path = tk.StringVar()
        if last_source_csv:
            self.source_csv_path.set(last_source_csv)
        elif self.default_source_csv_filename and os.path.isdir(self.source_data_dir): # source_data_dirが存在する場合のみ結合
             self.source_csv_path.set(os.path.join(self.source_data_dir, self.default_source_csv_filename))


        # --- GUI要素の作成 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 工事番号入力
        ttk.Label(main_frame, text="工事番号:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.construction_no_entry = ttk.Entry(main_frame, width=20)
        self.construction_no_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        # 前回保存された工事番号を読み込む (なければconfigのデフォルト、それもなければ空)
        last_construction_no = self.config.get("last_construction_number", self.config.get("default_construction_number", ""))
        if last_construction_no:
            self.construction_no_entry.insert(0, last_construction_no)


        # 発注伝票CSV選択
        ttk.Label(main_frame, text="発注伝票CSV:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.source_csv_entry = ttk.Entry(main_frame, textvariable=self.source_csv_path, width=40)
        self.source_csv_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(main_frame, text="参照...", command=self.browse_source_csv)
        self.browse_button.grid(row=1, column=2, padx=5, pady=5)

        # 図番キーフィルター
        filter_frame = ttk.LabelFrame(main_frame, text="部品№フィルター")
        filter_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(filter_frame, text="フィルター値 (例: 1 → #100, 10 → #1000, 空/0: 全表示):").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(filter_frame, text="#").grid(row=0, column=1, padx=(5,0), pady=2, sticky=tk.E) # "#"をEntryの左に
        self.filter_start_entry = ttk.Entry(filter_frame, width=4, justify=tk.RIGHT) # 幅を4に、テキストを右寄せ
        self.filter_start_entry.grid(row=0, column=2, padx=(0,0), pady=2, sticky=tk.W)
        ttk.Label(filter_frame, text="00").grid(row=0, column=3, padx=(0,5), pady=2, sticky=tk.W) # "00"をEntryの右に
        last_filter_start = self.config.get("last_filter_start_value", str(self.default_filter_start_val))
        self.filter_start_entry.insert(0, last_filter_start)

        ttk.Label(filter_frame, text="保管場所フィルター:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.location_filter_combo = ttk.Combobox(filter_frame, state="readonly", width=25)
        self.location_filter_combo.grid(row=1, column=1, columnspan=3, padx=5, pady=2, sticky=tk.EW)
        self.location_filter_combo['values'] = ["すべての場所"]
        last_location_filter = self.config.get("last_location_filter_viewer", "すべての場所")
        self.location_filter_combo.set(last_location_filter)
        # フィルター入力要素を左に寄せるため、右側に伸縮する空カラムを追加
        filter_frame.columnconfigure(4, weight=1)

        # 照合実行ボタン
        self.match_button = ttk.Button(main_frame, text="照合実行", command=self.perform_matching)
        self.match_button.grid(row=3, column=0, columnspan=3, pady=10)

        # 結果表示用Treeview
        columns = ("scanned_barcode", "order_no", "parts_no", "drawing_no", "sort_key_display", "status", "location")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
        self.tree.heading("scanned_barcode", text="スキャンバーコード")
        self.tree.heading("order_no", text=self.order_no_col) # 設定ファイルからカラム名を取得
        self.tree.heading("parts_no", text=self.parts_no_col_name) # 部品№のヘッダー
        self.tree.heading("drawing_no", text=self.drawing_no_col) # 設定ファイルからカラム名を取得
        self.tree.heading("sort_key_display", text="ソートキー")
        self.tree.heading("status", text="状態")
        self.tree.heading("location", text="保管場所")

        self.tree.column("scanned_barcode", width=150)
        self.tree.column("order_no", width=150)
        self.tree.column("parts_no", width=120) # 部品№の列幅
        self.tree.column("drawing_no", width=150)
        self.tree.column("sort_key_display", width=80, anchor=tk.CENTER)
        self.tree.column("status", width=100)
        self.tree.column("location", width=100)

        # 色変えのためのタグ設定は削除

        self.tree.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

        # スクロールバー
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=4, column=3, sticky=(tk.N, tk.S))

        # 表示データ数ラベル
        self.data_count_label = ttk.Label(main_frame, text="表示データ数: 0 件")
        self.data_count_label.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky=tk.E)

        # ウィンドウリサイズ設定
        main_frame.columnconfigure(1, weight=1) # Entryウィジェットがリサイズされるように
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1) # Treeviewの行がリサイズされるように (grid row変更のため)

        # ウィンドウクローズ時の処理をバインド
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初期フォーカス設定とEnterキーによるナビゲーション
        self._setup_keyboard_navigation()

        # 初期フォーカスを工事番号入力欄に設定
        self.construction_no_entry.focus_set()

    def on_closing(self):
        """ウィンドウが閉じられるときに呼び出される処理"""
        current_construction_no = self.construction_no_entry.get()
        current_source_csv_path = self.source_csv_path.get()
        current_filter_start = self.filter_start_entry.get()
        current_location_filter = self.location_filter_combo.get()

        self.config.set("last_construction_number", current_construction_no)
        self.config.set("last_source_csv_path", current_source_csv_path)
        self.config.set("last_filter_start_value", current_filter_start if current_filter_start.isdigit() else str(self.default_filter_start_val))
        self.config.set("last_location_filter_viewer", current_location_filter)
        self.config.save_config()
        self.root.destroy()

    def _select_all_on_focus(self, event):
        """フォーカス時にテキストを全選択する"""
        # 遅延実行しないと、macOSなどで全選択が正しく動作しない場合があるためafterを使用
        event.widget.after(10, lambda: event.widget.select_range(0, tk.END))
        event.widget.after(10, lambda: event.widget.icursor(tk.END))

    def _setup_keyboard_navigation(self):
        """キーボードナビゲーション（フォーカス時の全選択、Enterキーでの移動/実行）を設定する"""
        # フォーカス時に全選択
        self.construction_no_entry.bind("<FocusIn>", self._select_all_on_focus)
        self.source_csv_entry.bind("<FocusIn>", self._select_all_on_focus)
        self.filter_start_entry.bind("<FocusIn>", self._select_all_on_focus)

        # Enterキーでのフォーカス移動とアクション
        self.construction_no_entry.bind("<Return>", lambda event: self.source_csv_entry.focus_set())
        self.source_csv_entry.bind("<Return>", lambda event: self.filter_start_entry.focus_set())
        self.filter_start_entry.bind("<Return>", lambda event: self.perform_matching())
        self.browse_button.bind("<Return>", lambda event: self.browse_button.invoke()) # Enterでボタン実行

    def browse_source_csv(self):
        initial_dir = self.source_data_dir
        if not os.path.isdir(initial_dir):
            initial_dir = os.getcwd() # デフォルトフォルダがなければカレントディレクトリ

        filepath = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="発注伝票CSVファイルを選択",
            filetypes=(("CSVファイル", "*.csv"), ("すべてのファイル", "*.*"))
        )
        if filepath:
            self.source_csv_path.set(filepath)

    def load_scanned_data(self, construction_no):
        """指定された工事番号のスキャンデータCSVを読み込む"""
        # scanned_data_map = {barcode: location}
        scanned_data_map = {}
        # G_ScanBCD_Scanner.pyではヘッダーなしでbarcode_infoが0列目に書き込まれる想定
        # "barcode_info", "construction_number", "location", "barcode_type", "timestamp"
        scan_data_filename = os.path.join(self.data_dir, f"{construction_no}.csv")

        if not os.path.exists(scan_data_filename):
            messagebox.showwarning("警告", f"スキャンデータファイルが見つかりません:\n{scan_data_filename}")
            return {} # 空の辞書を返す
        try:
            with open(scan_data_filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and len(row) >= 4: # barcode_info, _, location, barcode_type があるか
                        barcode = row[0].strip()
                        location = row[2].strip()
                        if barcode: # バーコードが空でなければ
                            # 同じバーコードが複数回スキャンされた場合、最後に読み込まれた場所が採用される
                            scanned_data_map[barcode] = {"location": location, "type": row[3].strip()}
            return scanned_data_map
        except Exception as e:
            messagebox.showerror("エラー", f"スキャンデータファイルの読み込み中にエラーが発生しました:\n{e}")
            return {} # 空の辞書を返す

    def load_source_data(self, filepath):
        """発注伝票CSVファイルを読み込む"""
        # source_map = {発注伝票No: {"drawing_no": 図面番号, "parts_no": 部品番号}}
        source_map = {}
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("警告", f"発注伝票CSVファイルが指定されていないか、見つかりません:\n{filepath}")
            return None
        try:
            with open(filepath, mode='r', newline='', encoding='utf-8-sig') as file: # utf-8-sigでBOM対応
                reader = csv.DictReader(file)
                # 部品№カラムも必須チェックに含める（ただし、データ自体はなくても良い）
                required_cols = [self.order_no_col, self.drawing_no_col, self.parts_no_col_name]
                missing_cols = [col for col in required_cols if col not in reader.fieldnames]
                if missing_cols:
                    messagebox.showerror("エラー",
                        f"発注伝票CSVに必要なカラム名が見つかりません:\n{', '.join(missing_cols)}")
                    return None

                for row in reader:
                    order_no_from_csv = row.get(self.order_no_col, "").strip() # 前後の空白も除去
                    drawing_no = row.get(self.drawing_no_col)
                    parts_no = row.get(self.parts_no_col_name, "") # 部品№がなくてもエラーにしない
                    if order_no_from_csv: # 発注伝票番号がある場合のみ
                        # CSVから読み込んだ発注伝票番号の先頭の0を除去してキーとする
                        normalized_order_no = order_no_from_csv.lstrip('0')
                        source_map[normalized_order_no] = {"drawing_no": drawing_no, "parts_no": parts_no}
            return source_map
        except Exception as e:
            messagebox.showerror("エラー", f"発注伝票CSVファイルの読み込み中にエラーが発生しました:\n{e}")
            return None

    def perform_matching(self):
        # 結果表示ツリーをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.data_count_label.config(text="表示データ数: 0 件") # データ数表示もリセット

        construction_no = self.construction_no_entry.get().strip()
        if not construction_no:
            messagebox.showwarning("入力エラー", "工事番号を入力してください。")
            return

        scanned_data_map = self.load_scanned_data(construction_no)
        if not scanned_data_map:
            # load_scanned_data内でエラーメッセージ表示済み
            return # scanned_data_map が空なら処理終了
        
        # 保管場所フィルターの選択肢を更新
        unique_locations = sorted(list(set(info["location"] for info in scanned_data_map.values() if info.get("location"))))
        current_selected_location = self.location_filter_combo.get()
        self.location_filter_combo['values'] = ["すべての場所"] + unique_locations
        if current_selected_location in self.location_filter_combo['values']:
            self.location_filter_combo.set(current_selected_location)
        else:
            self.location_filter_combo.set("すべての場所") # 以前の値が無効ならデフォルトに

        selected_location_filter = self.location_filter_combo.get()

        source_data_map = self.load_source_data(self.source_csv_path.get())
        if source_data_map is None:
            # load_source_data内でエラーメッセージ表示済み
            return

        # フィルター値の取得と解釈
        filter_input_str = self.filter_start_entry.get().strip() # 前後の空白を除去
        
        apply_parts_no_filter = False
        parts_no_filter_value = ""

        if not filter_input_str or filter_input_str == "0" or filter_input_str == "0000":
            # No filter, apply_parts_no_filter remains False
            pass
        else:
            try:
                filter_base_input = int(filter_input_str)
                if filter_base_input <= 0:
                    # 0は上記のifで処理されるため、ここに来る場合は実質的に filter_base_input > 0 のはずだが念のため
                    # ただし、ユーザーが "-1" などを入力した場合を考慮
                    messagebox.showwarning("入力エラー", "フィルター値は1以上の整数で入力してください。\n空または0で全表示。")
                    return

                # ユーザー入力を基にフィルター値を生成 (例: 1 -> "#100", 10 -> "#1000")
                parts_no_filter_value = f"#{filter_base_input}00"
                apply_parts_no_filter = True
            except ValueError:
                messagebox.showwarning("入力エラー", "フィルター値は数字で入力してください (例: 1)。\n空または0で全表示。")
                return

        all_results_before_filter = [] # リストの初期化
        for bc, scanned_location_info in scanned_data_map.items():
            scanned_location = scanned_location_info.get("location", "---")
            scanned_type = scanned_location_info.get("type", "")

            normalized_scanned_bc = bc.lstrip('0')
            source_info = source_data_map.get(normalized_scanned_bc)
            location_to_display = scanned_location if scanned_location else "---"

            key_segment_for_display = "---"
            drawing_no_to_display = "---"
            parts_no_to_display = "---"

            drawing_no_from_source = None # ループ内で drawing_no_from_source を初期化

            if source_info: # 発注伝票情報 (source_info) がある場合
                drawing_no_from_source = source_info.get("drawing_no")
                parts_no_to_display = source_info.get("parts_no", "---")
                drawing_no_to_display = drawing_no_from_source if drawing_no_from_source else "---"

                # 図番があり、文字列型で、ソートキー抽出に必要な長さがある場合
                if drawing_no_from_source and isinstance(drawing_no_from_source, str) and \
                   len(drawing_no_from_source) >= (self.key_extract_start_0based + self.key_extract_length):
                    try:
                        # 設定に基づいてソートキー部分を文字列として抽出
                        extracted_str = drawing_no_from_source[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length]
                        key_segment_for_display = extracted_str
                    except Exception: # 何らかの理由で抽出に失敗した場合 (通常は起こりにくい)
                        key_segment_for_display = "---"

            # Determine display status
            status_to_display = "該当なし" # デフォルト
            if source_info: # If linked to source data, it's initially OK
                status_to_display = "OK"

            # Override for special types, this order matters
            if scanned_type == self.no_barcode_type_str: # バーコードなし（システムID）
                status_to_display = "該当なし (バーコードなし)"
            elif scanned_type == "MANUAL": # 新しい "MANUAL" タイプをチェック
                status_to_display = "手動登録 (図番)"
            elif scanned_type == self.manual_drawing_barcode_type_str and self.manual_drawing_barcode_type_str != "MANUAL":
                # configからの従来のタイプを処理 (もし "MANUAL" と異なる場合)
                status_to_display = "手動登録 (図番)"

            all_results_before_filter.append((bc, normalized_scanned_bc, parts_no_to_display, drawing_no_to_display, key_segment_for_display, status_to_display, location_to_display))

        # 実際に表示する結果リスト (フィルター後)
        results_to_display = []
        for item_data in all_results_before_filter:
            status = item_data[5] # status は6番目の要素
            item_location = item_data[6] # location は7番目の要素
            passes_filter = False

            # まず場所フィルターをチェック
            if selected_location_filter == "すべての場所" or item_location == selected_location_filter:
                if status == "OK": # "OK" の場合のみ部品№フィルターを適用
                    if apply_parts_no_filter:
                        parts_no_val = item_data[2] # 部品№は3番目の要素
                        if parts_no_val == parts_no_filter_value: # 完全一致で比較
                            passes_filter = True
                    else: # 部品№フィルター無効 (全表示)
                        passes_filter = True
                    
                    if passes_filter:
                        results_to_display.append(item_data)
                elif status.startswith("該当なし") or status == "手動登録 (図番)": # 「該当なし」系と「手動登録」は場所フィルター後、部品№フィルターに関わらず表示
                    passes_filter = True
                    results_to_display.append(item_data)

        if not results_to_display:
            messagebox.showinfo("情報", "照合可能なスキャンデータがありませんでした。")
            return

        def sort_key_func(item):
            drawing_no_str = item[3] # 図番は4番目の要素
            if drawing_no_str and isinstance(drawing_no_str, str) and \
               len(drawing_no_str) >= (self.key_extract_start_0based + self.key_extract_length):
                try:
                    sort_val_str = drawing_no_str[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length]
                    return int(sort_val_str)
                except ValueError:
                    return float('inf')
            return float('inf')

        sorted_results = sorted(results_to_display, key=sort_key_func)

        for res in sorted_results:
            self.tree.insert("", tk.END, values=res)
        self.data_count_label.config(text=f"表示データ数: {len(sorted_results)} 件")

if __name__ == "__main__":
    # 設定ファイルのロード
    # G_ScanBCD_main.py と同様の config.json を想定
    config_instance = Config("config.json")

    app_root = tk.Tk()
    viewer = DrawingNumberViewer(app_root, config_instance)
    app_root.mainloop()
