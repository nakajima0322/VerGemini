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
        self.root.title("保管場所照合ツール")

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

        # 読み込んだ全データを保持するインスタンス変数
        self.prepared_data = []


        # --- GUI要素の作成 ---
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 工事番号入力
        ttk.Label(main_frame, text="工事番号:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.construction_no_entry = ttk.Entry(main_frame, width=20)
        self.construction_no_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        last_construction_no = self.config.get("last_construction_number", self.config.get("default_construction_number", ""))
        if last_construction_no:
            self.construction_no_entry.insert(0, last_construction_no)
        
        # 工事番号入力後のイベントをバインド
        self.construction_no_entry.bind("<FocusOut>", self.on_construction_no_changed)

        # 発注伝票CSV選択
        ttk.Label(main_frame, text="発注伝票CSV:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.source_csv_entry = ttk.Entry(main_frame, textvariable=self.source_csv_path, width=40)
        self.source_csv_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(main_frame, text="参照...", command=self.browse_source_csv)
        self.browse_button.grid(row=1, column=2, padx=5, pady=5)

        # フィルター条件フレーム
        filter_frame = ttk.LabelFrame(main_frame, text="フィルター条件")
        filter_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky=tk.EW)

        # 部品№フィルター (複数入力対応)
        ttk.Label(filter_frame, text="部品№ (カンマ区切り可 例: 1,10 → #100,#1000 / 空,0: 全表示):").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.filter_start_entry = ttk.Entry(filter_frame, width=20) # 幅を調整
        self.filter_start_entry.grid(row=0, column=1, columnspan=2, padx=(0,5), pady=2, sticky=tk.EW) # columnspan調整
        last_filter_start = self.config.get("last_filter_start_value", str(self.default_filter_start_val))
        self.filter_start_entry.insert(0, last_filter_start)

        # 保管場所フィルター (Listboxに変更、複数選択対応)
        ttk.Label(filter_frame, text="保管場所 (複数選択可):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.location_filter_listbox = tk.Listbox(filter_frame, selectmode=tk.EXTENDED, exportselection=False, height=4)
        self.location_filter_listbox_scrollbar = ttk.Scrollbar(filter_frame, orient=tk.VERTICAL, command=self.location_filter_listbox.yview)
        self.location_filter_listbox.configure(yscrollcommand=self.location_filter_listbox_scrollbar.set)
        self.location_filter_listbox.grid(row=1, column=1, columnspan=2, padx=(0,0), pady=2, sticky=tk.EW)
        self.location_filter_listbox_scrollbar.grid(row=1, column=3, padx=(0,5), pady=2, sticky=(tk.N, tk.S))
        self.location_filter_listbox.bind("<<ListboxSelect>>", lambda e: self._apply_filters_and_display())

        filter_frame.columnconfigure(1, weight=1) # フィルター入力欄が伸縮するように

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

        # Treeviewのタグ設定（色分け用）
        self.tree.tag_configure("ok", foreground="black")
        self.tree.tag_configure("not_found", foreground="gray")
        self.tree.tag_configure("manual", foreground="blue")

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
        self.root.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1) # Treeviewの行がリサイズされるように

        # ウィンドウクローズ時の処理をバインド
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Escape>', lambda e: self.on_closing())

        # 初期フォーカス設定とEnterキーによるナビゲーション
        self._setup_keyboard_navigation()

        # 初期フォーカスを工事番号入力欄に設定
        self.construction_no_entry.focus_set()
        
        # 起動時に保管場所リストを更新
        self.root.after(100, self.update_location_filter_options)

        # ウィンドウジオメトリの復元
        self._restore_geometry()

    def on_closing(self):
        """ウィンドウが閉じられるときに呼び出される処理"""
        current_construction_no = self.construction_no_entry.get()
        current_source_csv_path = self.source_csv_path.get()
        current_filter_start = self.filter_start_entry.get()

        selected_location_indices = self.location_filter_listbox.curselection()
        selected_locations = [self.location_filter_listbox.get(i) for i in selected_location_indices]
        current_location_filter_str = ",".join(selected_locations) # カンマ区切りで保存

        self._save_geometry()
        self.config.set("last_construction_number", current_construction_no)
        self.config.set("last_source_csv_path", current_source_csv_path)
        self.config.set("last_filter_start_value", current_filter_start if current_filter_start else str(self.default_filter_start_val))
        self.config.set("last_location_filter_viewer", current_location_filter_str)
        self.config.save_config()
        print("保管場所照合ツールを終了します。")
        self.root.destroy()

    def _save_geometry(self):
        """現在のウィンドウジオメトリをconfigに保存する"""
        geometries = self.config.get("window_geometries", {})
        geometries[self.__class__.__name__] = self.root.winfo_geometry()
        self.config.set("window_geometries", geometries)

    def _restore_geometry(self):
        """configからウィンドウジオメトリを復元する"""
        geometries = self.config.get("window_geometries", {})
        geometry = geometries.get(self.__class__.__name__)
        if geometry:
            self.root.geometry(geometry)


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
        self.filter_start_entry.bind("<FocusIn>", self._select_all_on_focus) # Listboxは対象外

        # Enterキーでのフォーカス移動とアクション
        self.construction_no_entry.bind("<Return>", self.on_construction_no_changed)
        self.source_csv_entry.bind("<Return>", lambda event: self.filter_start_entry.focus_set())
        self.filter_start_entry.bind("<Return>", lambda event: self._apply_filters_and_display())
        self.browse_button.bind("<Return>", lambda event: self.browse_button.invoke()) # Enterでボタン実行

    def on_construction_no_changed(self, event=None):
        """工事番号が変更されたときに呼ばれる"""
        self.update_location_filter_options()
        self.source_csv_entry.focus_set() # 次の入力欄へフォーカスを移動

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

    def update_location_filter_options(self):
        """工事番号に基づいてスキャンデータを読み込み、保管場所フィルターの選択肢を更新する"""
        construction_no = self.construction_no_entry.get().strip()
        if not construction_no:
            return # 工事番号がなければ何もしない
        
        scanned_data_map = self.load_scanned_data(construction_no)
        if not scanned_data_map:
            return

        self.location_filter_listbox.delete(0, tk.END) # クリア
        unique_locations = sorted(list(set(info["location"] for info in scanned_data_map.values() if info.get("location"))))
        self.location_filter_listbox.insert(tk.END, "すべての場所")
        for loc in unique_locations:
            self.location_filter_listbox.insert(tk.END, loc)

        # 前回選択した保管場所を復元
        last_location_filters_str = self.config.get("last_location_filter_viewer", "")
        if last_location_filters_str:
            last_locations = last_location_filters_str.split(',')
            for i, item_in_listbox in enumerate(self.location_filter_listbox.get(0, tk.END)):
                if item_in_listbox in last_locations:
                    self.location_filter_listbox.selection_set(i)
        elif self.location_filter_listbox.size() > 0:
            self.location_filter_listbox.selection_set(0)

    def _get_sort_key(self, drawing_no_str):
        """図番文字列からソート用のキー（数値）を抽出する"""
        def sort_key_func(item):
            drawing_no_str = item[3] # 図番は4番目の要素
            if drawing_no_str and isinstance(drawing_no_str, str) and \
               len(drawing_no_str) >= (self.key_extract_start_0based + self.key_extract_length):
                try:
                    sort_val_str = drawing_no_str[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length]                    
                    return int(sort_val_str) # 数値としてソート
                except ValueError:
                    return float('inf')
            return float('inf')
        return sort_key_func

    def _get_status_and_tag(self, source_info, scanned_type):
        """ソース情報とスキャンタイプから表示用のステータスとTreeviewタグを決定する"""
        if scanned_type == self.no_barcode_type_str:
            return "該当なし (バーコードなし)", "not_found"
        if scanned_type == "MANUAL" or scanned_type == self.manual_drawing_barcode_type_str:
            return "手動登録 (図番)", "manual"
        if source_info:
            return "OK", "ok"
        return "該当なし", "not_found"

    def _prepare_data_for_display(self, scanned_data_map, source_data_map):
        """スキャンデータとソースデータを結合し、表示用のデータリストを作成する"""
        all_results = []
        for bc, scanned_info in scanned_data_map.items():
            normalized_bc = bc.lstrip('0')
            source_info = source_data_map.get(normalized_bc)

            status, tag = self._get_status_and_tag(source_info, scanned_info.get("type", ""))
            
            drawing_no = source_info.get("drawing_no") if source_info else "---"
            parts_no = source_info.get("parts_no", "---") if source_info else "---"
            location = scanned_info.get("location", "---")

            sort_key_display = "---"
            if isinstance(drawing_no, str) and len(drawing_no) >= (self.key_extract_start_0based + self.key_extract_length):
                sort_key_display = drawing_no[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length]

            all_results.append({
                "values": (bc, normalized_bc, parts_no, drawing_no, sort_key_display, status, location),
                "tag": tag
            })
        return all_results

    def _filter_results(self, all_results):
        """フィルター条件に基づいて表示するデータを絞り込む"""
        # 部品№フィルター値の取得
        filter_input_str = self.filter_start_entry.get().strip()
        apply_parts_no_filter = False
        parts_no_filter_values = []
        if filter_input_str and filter_input_str != "0":
            raw_filter_inputs = [val.strip() for val in filter_input_str.split(',')]
            for val_str in raw_filter_inputs:
                if not val_str:
                    continue
                try:
                    parts_no_filter_values.append(f"#{int(val_str)}00")
                except ValueError:
                    messagebox.showwarning("入力エラー", f"部品№フィルターの '{val_str}' は数字で入力してください。")
                    return None # エラーを示す
            if parts_no_filter_values:
                apply_parts_no_filter = True

        # 保管場所フィルター値の取得
        selected_indices = self.location_filter_listbox.curselection()
        selected_locations = [self.location_filter_listbox.get(i) for i in selected_indices]
        all_locations_selected = not selected_indices or "すべての場所" in selected_locations

        # フィルタリング実行
        filtered_list = []
        for item in all_results:
            status = item["values"][5]
            location = item["values"][6]
            parts_no = item["values"][2]

            # 1. 保管場所フィルター
            if not all_locations_selected and location not in selected_locations:
                continue

            # 2. 部品№フィルター
            if status in ("OK", "手動登録 (図番)"):
                if apply_parts_no_filter:
                    if parts_no in parts_no_filter_values:
                        filtered_list.append(item)
                else:
                    filtered_list.append(item)
            elif status.startswith("該当なし"):
                filtered_list.append(item)
        
        return filtered_list

    def _apply_filters_and_display(self):
        """メモリ上のデータにフィルターを適用し、Treeviewを更新する"""
        # 結果表示ツリーをクリア
        self.tree.delete(*self.tree.get_children())
        self.data_count_label.config(text="表示データ数: 0 件")

        # ソート
        def sort_key_func(item):
            drawing_no_str = item["values"][3]
            if isinstance(drawing_no_str, str) and len(drawing_no_str) >= (self.key_extract_start_0based + self.key_extract_length):
                try:
                    return int(drawing_no_str[self.key_extract_start_0based : self.key_extract_start_0based + self.key_extract_length])
                except ValueError:
                    return float('inf')
            return float('inf')
        
        if not self.prepared_data:
            # まだデータが読み込まれていない場合は何もしない
            return

        # フィルタリング
        results_to_display = self._filter_results(self.prepared_data)

        if results_to_display is None: # フィルターでエラーが発生した場合
            return

        if not results_to_display:
            # フィルター結果が0件の場合、メッセージは表示せず、表示をクリアするだけ
            return

        # ソート
        sorted_results = sorted(results_to_display, key=sort_key_func)

        # Treeviewへの表示
        for res in sorted_results:
            self.tree.insert("", tk.END, values=res["values"], tags=(res["tag"],))
        self.data_count_label.config(text=f"表示データ数: {len(sorted_results)} 件")

    def perform_matching(self):
        """ファイルからデータを読み込み、メモリに保持して、最初の表示を行う"""
        construction_no = self.construction_no_entry.get().strip()
        if not construction_no:
            messagebox.showwarning("入力エラー", "工事番号を入力してください。")
            return

        scanned_data_map = self.load_scanned_data(construction_no)
        if not scanned_data_map:
            return
        source_data_map = self.load_source_data(self.source_csv_path.get())
        if source_data_map is None:
            return

        self.prepared_data = self._prepare_data_for_display(scanned_data_map, source_data_map)
        self._apply_filters_and_display()

if __name__ == "__main__":
    try:
        # 設定ファイルのロード
        config_instance = Config("config.json")

        app_root = tk.Tk()
        viewer = DrawingNumberViewer(app_root, config_instance)
        app_root.mainloop()
    except Exception as e:
        print(f"G_DrawingNumberViewer の起動中にエラーが発生しました: {e}")
        messagebox.showerror("起動エラー", f"図面番号照合ツールの起動に失敗しました。\n{e}")
