# c:\temp\KHT_Python\VerGemini\G_PartInfoViewer.py
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import sys
import cv2 # OpenCVのインポート
import time # target_fps制御用
from G_config import Config # 既存のConfigクラスを利用
from G_ScanBCD_Analyzer import G_ScanBCD_Analyzer # バーコード解析用

class PartInfoViewer:
    def __init__(self, root, config, initial_construction_no=None, initial_barcode_value=None):
        self.root = root
        self.config = config
        self.root.title("部品情報表示ツール")

        # 設定値の取得
        self.source_data_dir = self.config.get("source_data_dir", "Source")
        self.order_no_col = self.config.get("source_csv_order_no_column", "発注伝票No.")
        self.drawing_no_col = self.config.get("source_csv_drawing_no_column", "図番")
        self.parts_no_col_name = self.config.get("source_csv_parts_no_column", "部品№")
        self.delivery_count_col_name = self.config.get("source_csv_delivery_count_column", "納入数")
        # 新しく表示する情報のカラム名を設定から取得 (なければデフォルト値)
        self.item_name_col_name = self.config.get("source_csv_item_name_column", "品名")
        self.supplier_col_name = self.config.get("source_csv_supplier_column", "仕入先")
        self.delivery_date_col_name = self.config.get("source_csv_delivery_date_column", "納期")
        self.arrangement_status_col_name = self.config.get("source_csv_arrangement_status_column", "手配状況")


        # カメラとスキャン関連の設定
        self.camera_index = self.config.get("camera_index", 0)
        self.camera_width = self.config.get("camera_width", 640)
        self.camera_height = self.config.get("camera_height", 480)
        self.barcode_type_to_scan = self.config.get("barcode_type", "CODE39")
        self.expected_barcode_length = self.config.get("expected_length", 10)
        self.target_fps = self.config.get("target_fps", 30)

        self.source_csv_path_var = tk.StringVar()
        self.parts_no_var = tk.StringVar()
        self.drawing_no_var = tk.StringVar()
        self.delivery_count_var = tk.StringVar()
        # 新しい情報用のStringVar
        self.item_name_var = tk.StringVar()
        self.supplier_var = tk.StringVar()
        self.delivery_date_var = tk.StringVar()
        self.arrangement_status_var = tk.StringVar()
        self.status_var = tk.StringVar()

        # バーコード解析器のインスタンス
        self.barcode_analyzer = G_ScanBCD_Analyzer(self.config) # Configを渡す

        # Columns to read from CSV for "same drawing search"
        self.csv_data_columns_for_same_drawing_search = (
            self.order_no_col, self.parts_no_col_name, self.drawing_no_col,
            self.delivery_count_col_name, self.item_name_col_name,
            self.supplier_col_name, self.delivery_date_col_name,
            self.arrangement_status_col_name
        )
        # Column name for the filename in the tree for "same drawing search"
        self.filename_col_name_for_tree = "ファイル名"
        # Columns to display in the "same drawing search" Treeview
        self.same_drawing_tree_display_columns = self.csv_data_columns_for_same_drawing_search + (self.filename_col_name_for_tree,)


        self._build_ui()

        # 前回使用した工事番号を読み込む
        if initial_construction_no:
            self.construction_no_entry.insert(0, initial_construction_no)
            self._update_source_csv_path_display(initial_construction_no)
        else:
            last_construction_no_from_config = self.config.get("last_construction_no_part_viewer",
                                                               self.config.get("default_construction_number", ""))
            if last_construction_no_from_config:
                self.construction_no_entry.insert(0, last_construction_no_from_config)
                self._update_source_csv_path_display(last_construction_no_from_config) # 初期表示
            else:
                # last_construction_no が空の場合、全検索モードを示唆する表示にする
                self.source_csv_path_var.set("工事番号未入力時は全s.csvファイルを検索")
            
        if initial_barcode_value:
            self.barcode_entry.insert(0, initial_barcode_value)

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        if initial_construction_no and initial_barcode_value:
            self.root.after(100, self._on_search) # 少し遅延させて自動検索
            
        self._center_and_right_align_window(self.root) # ウィンドウを右寄せ
        self.root.state("zoomed") # ウィンドウを最大化
        self.construction_no_entry.focus_set()

    def _center_and_right_align_window(self, window, window_width_offset=0, window_height_offset=0):
        """ウィンドウを画面の右端に寄せて表示する"""
        window.update_idletasks() # ウィンドウサイズを確定させる
        width = window.winfo_width() + window_width_offset
        height = window.winfo_height() + window_height_offset
        
        # 画面サイズを取得 (より正確にはtkinterのscreenwidth/heightを使う)
        screen_width = window.winfo_screenwidth() # プライマリスクリーンの幅
        # screen_height = window.winfo_screenheight() # プライマリスクリーンの高さ

        x = screen_width - width - 10 # 右端から10ピクセル内側
        y = 10  # 上端から10ピクセル（任意で調整可能）
        window.geometry(f'{width}x{height}+{x}+{y}')

    def _normalize_id_string(self, id_str: str) -> str:
        """ID文字列を正規化 (先頭ゼロ削除、オールゼロなら"0")"""
        if not id_str:
            return ""
        stripped_id = id_str.lstrip('0')
        if not stripped_id:
            return "0"
        return stripped_id

    def _select_all_on_focus(self, event):
        """フォーカス時にテキストを全選択する"""
        event.widget.after(10, lambda: event.widget.select_range(0, tk.END))
        event.widget.after(10, lambda: event.widget.icursor(tk.END))

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        # メインフレームの行と列のウェイト設定 (左右分割のため)
        main_frame.columnconfigure(0, weight=1) # 左側のフレーム用
        main_frame.columnconfigure(1, weight=2) # 右側のフレーム用 (少し広めに)
        self.root.rowconfigure(0, weight=1)

        # --- 入力セクション ---
        input_frame = ttk.LabelFrame(main_frame, text="検索条件")
        input_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="工事番号:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.construction_no_entry = ttk.Entry(input_frame, width=15)
        self.construction_no_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.construction_no_entry.bind("<FocusIn>", self._select_all_on_focus)
        # <Return>でCSVパス更新とフォーカス移動
        self.construction_no_entry.bind("<Return>", self._on_construction_no_entered)
        # FocusOutでもパス更新（手入力でフォーカスを外した場合）
        self.construction_no_entry.bind("<FocusOut>", lambda e: self._update_source_csv_path_display(self.construction_no_entry.get().strip()))



        ttk.Label(input_frame, text="バーコード値:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.barcode_entry = ttk.Entry(input_frame, width=30)
        self.barcode_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.barcode_entry.bind("<FocusIn>", self._select_all_on_focus)
        self.barcode_entry.bind("<Return>", lambda e: self._on_search())
        
        # 同一図番検索ボタンは自動実行のため削除
        # self.same_drawing_search_button = ttk.Button(input_frame, text="同一図番検索", command=self._search_same_drawing_no, state=tk.DISABLED)
        # self.same_drawing_search_button.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        # ボタンを配置するためのコンテナフレーム
        button_container_frame = ttk.Frame(input_frame)
        button_container_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        # button_container_frame の列構成を設定してボタンを中央に配置
        button_container_frame.columnconfigure(0, weight=1) # 左の空きスペース
        button_container_frame.columnconfigure(1, weight=0) # 検索実行ボタン用
        button_container_frame.columnconfigure(2, weight=0) # スキャンボタン用
        button_container_frame.columnconfigure(3, weight=1) # 右の空きスペース

        self.search_button = ttk.Button(button_container_frame, text="検索実行", command=self._on_search)
        self.search_button.grid(row=0, column=1, padx=5) # stickyなしで中央の列に配置
        
        self.scan_button = ttk.Button(button_container_frame, text="スキャン", command=self._start_barcode_scan_window)
        self.scan_button.grid(row=0, column=2, padx=5) # stickyなしで中央の列に配置

        # --- 表示セクション ---
        # 左側に配置
        display_frame = ttk.LabelFrame(main_frame, text="部品情報")
        display_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(1, weight=1) # 表示セクションの行が伸縮するように
        display_frame.columnconfigure(1, weight=1)

        ttk.Label(display_frame, text="対象CSV:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.source_csv_path_var, foreground="blue").grid(row=0, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.parts_no_col_name}:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.parts_no_var).grid(row=1, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.drawing_no_col}:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.drawing_no_var).grid(row=2, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.delivery_count_col_name}:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.delivery_count_var).grid(row=3, column=1, padx=5, pady=2, sticky=tk.EW)

        # 新しい情報の表示ラベルを追加
        ttk.Label(display_frame, text=f"{self.item_name_col_name}:").grid(row=4, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.item_name_var).grid(row=4, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.supplier_col_name}:").grid(row=5, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.supplier_var).grid(row=5, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.delivery_date_col_name}:").grid(row=6, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.delivery_date_var).grid(row=6, column=1, padx=5, pady=2, sticky=tk.EW)

        ttk.Label(display_frame, text=f"{self.arrangement_status_col_name}:").grid(row=7, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Label(display_frame, textvariable=self.arrangement_status_var).grid(row=7, column=1, padx=5, pady=2, sticky=tk.EW)




        # --- ステータス表示 ---
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E)) # columnspan=2 に変更
        self.status_var.set("準備完了")

        # --- 同一図番検索結果表示セクション ---
        # 右側に配置 (上部の検索条件エリアの高さも使うように rowspan=2)
        same_drawing_frame = ttk.LabelFrame(main_frame, text="同一図番の他の部品")
        same_drawing_frame.grid(row=0, column=1, rowspan=2, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S)) # row=0, column=1, rowspan=2 に変更
        same_drawing_frame.columnconfigure(0, weight=1)
        same_drawing_frame.rowconfigure(0, weight=1) # Treeviewが伸縮するように

        # 結果表示用Treeview
        # Use self.same_drawing_tree_display_columns which includes the filename column
        self.same_drawing_tree = ttk.Treeview(same_drawing_frame, columns=self.same_drawing_tree_display_columns, show="headings", height=5)
        for col_name in self.same_drawing_tree_display_columns:
            self.same_drawing_tree.heading(col_name, text=col_name)
            # Adjust column widths, giving the filename column a bit more space
            if col_name == self.filename_col_name_for_tree:
                self.same_drawing_tree.column(col_name, width=150, anchor=tk.W)
            else:
                self.same_drawing_tree.column(col_name, width=100, anchor=tk.W)

        self.same_drawing_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar_y = ttk.Scrollbar(same_drawing_frame, orient=tk.VERTICAL, command=self.same_drawing_tree.yview)
        self.same_drawing_tree.configure(yscrollcommand=tree_scrollbar_y.set)
        tree_scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def _on_construction_no_entered(self, event=None):
        """工事番号入力後（Enterキー押下時）の処理"""
        construction_no = self.construction_no_entry.get().strip()
        self._update_source_csv_path_display(construction_no)
        self.barcode_entry.focus_set()
        return "break" # イベントの伝播を止める

    def _update_source_csv_path_display(self, construction_no):
        cn_stripped = construction_no.strip()
        if cn_stripped:
            filename = f"{cn_stripped}s.csv"
            # full_path = os.path.join(self.source_data_dir, filename)
            # self.source_csv_path_var.set(os.path.abspath(full_path))
            # ファイル名のみを表示するように変更
            self.source_csv_path_var.set(filename)
        else:
            self.source_csv_path_var.set("工事番号未入力時は全s.csvファイルを検索")

    def _load_source_data_from_file(self, filepath: str) -> dict:
        """指定されたCSVファイルからソースデータを読み込む"""
        source_map = {}

        if not os.path.exists(filepath):
            # この関数は単一ファイル処理なので、呼び出し元でエラーをハンドルする
            # self.status_var.set(f"エラー: 発注伝票CSVファイルが見つかりません: {filepath}")
            # messagebox.showerror("ファイルエラー", f"発注伝票CSVファイルが見つかりません:\n{filepath}", parent=self.root)
            return None
        try:
            with open(filepath, mode='r', newline='', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                required_cols = [
                    self.order_no_col, self.drawing_no_col, self.parts_no_col_name, 
                    self.delivery_count_col_name, self.item_name_col_name, 
                    self.supplier_col_name, self.delivery_date_col_name, 
                    self.arrangement_status_col_name
                ]
                # 必須ではないが、存在すれば読み込むカラムもエラーチェック対象に含める
                # 存在しない場合は空文字として扱われるため、ここではエラーとしないカラムもある
                
                if not reader.fieldnames: # 空ファイルやヘッダーがない場合
                    # self.status_var.set(f"情報: CSVファイル ({filepath}) にヘッダーがありません。")
                    return None # 空の辞書ではなくNoneを返して区別

                missing_cols = [col for col in required_cols if col not in reader.fieldnames]
                if missing_cols:
                    # 見つからないカラム名をすべて表示する
                    msg = f"CSVファイル '{os.path.basename(filepath)}' に以下の必須カラム名が見つかりません:\n\n{', '.join(missing_cols)}\n\n設定ファイルやCSVファイルのヘッダーを確認してください。"
                    self.status_var.set(f"エラー: {msg}")
                    # messagebox でエラーをユーザーに通知
                    messagebox.showerror("CSVカラムエラー", msg, parent=self.root)
                    return None

                for row_data in reader:
                    order_no_from_csv = row_data.get(self.order_no_col, "").strip()
                    drawing_no = row_data.get(self.drawing_no_col, "").strip()
                    parts_no = row_data.get(self.parts_no_col_name, "").strip()
                    delivery_count = row_data.get(self.delivery_count_col_name, "0").strip()
                    # 新しい情報を読み込む
                    item_name = row_data.get(self.item_name_col_name, "").strip()
                    supplier = row_data.get(self.supplier_col_name, "").strip()
                    delivery_date = row_data.get(self.delivery_date_col_name, "").strip()
                    arrangement_status = row_data.get(self.arrangement_status_col_name, "").strip()

                    if order_no_from_csv:
                        normalized_order_no = self._normalize_id_string(order_no_from_csv)
                        source_map[normalized_order_no] = {
                            "drawing": drawing_no,
                            "parts": parts_no,
                            "delivery_count": delivery_count,
                            "item_name": item_name,
                            "supplier": supplier,
                            "delivery_date": delivery_date,
                            "arrangement_status": arrangement_status
                        }
            # if not source_map:
                # self.status_var.set(f"情報: 発注伝票CSV ({os.path.basename(filepath)}) は空か、有効なデータがありませんでした。")
            return source_map
        except Exception as e:
            msg = f"発注伝票CSV ({os.path.basename(filepath)}) の読み込み中にエラー: {e}"
            self.status_var.set(f"エラー: {msg}")
            # messagebox.showerror("CSV読み込みエラー", msg, parent=self.root) # 連続エラー表示を避けるため呼び出し元で制御
            return None

    def _clear_results(self):
        self.parts_no_var.set("")
        self.drawing_no_var.set("")
        self.delivery_count_var.set("")
        # 新しい情報表示もクリア
        self.item_name_var.set("")
        self.supplier_var.set("")
        self.delivery_date_var.set("")
        self.arrangement_status_var.set("")
        # self.same_drawing_search_button.config(state=tk.DISABLED) # ボタンを無効化 (ボタン削除のため不要)
        self.same_drawing_tree.delete(*self.same_drawing_tree.get_children()) # Treeviewをクリア

    def _on_search(self):
        self._clear_results()
        construction_no = self.construction_no_entry.get().strip()
        barcode_value = self.barcode_entry.get().strip()

        if not barcode_value:
            messagebox.showwarning("入力エラー", "バーコード値を入力してください。", parent=self.root)
            self.status_var.set("エラー: バーコード値が未入力です。")
            self.barcode_entry.focus_set()
            return

        normalized_barcode = self._normalize_id_string(barcode_value)
        found_item_in_any_file = False

        if construction_no: # 工事番号指定あり
            self.config.set("last_construction_no_part_viewer", construction_no) # 検索実行時に保存
            # _update_source_csv_path_display は入力時に更新されるので、ここではファイル名のみをセット
            self.source_csv_path_var.set(f"{construction_no}s.csv")
            target_filename = f"{construction_no}s.csv"
            target_filepath = os.path.join(self.source_data_dir, target_filename)

            if not os.path.exists(target_filepath):
                self.status_var.set(f"エラー: 指定されたCSVファイルが見つかりません: {target_filepath}")
                messagebox.showerror("ファイルエラー", f"指定されたCSVファイルが見つかりません:\n{target_filepath}", parent=self.root)
                return

            source_data_map = self._load_source_data_from_file(target_filepath)
            if source_data_map is None: # 読み込みエラーまたはカラムエラー
                # _load_source_data_from_file内でstatus_varは設定済みの場合がある
                if not self.status_var.get().startswith("エラー:"): # 未設定なら汎用エラー
                    self.status_var.set(f"エラー: CSVファイル {target_filename} の読み込みに失敗しました。")
                messagebox.showerror("CSV読込エラー", f"CSVファイル {target_filename} の読み込みに失敗しました。\n詳細はステータスバーを確認してください。", parent=self.root)
                return
            
            found_info = source_data_map.get(normalized_barcode)
            if found_info:
                self.parts_no_var.set(found_info.get("parts", "---"))
                self.drawing_no_var.set(found_info.get("drawing", "---"))
                self.delivery_count_var.set(found_info.get("delivery_count", "---"))
                # 新しい情報をセット
                self.item_name_var.set(found_info.get("item_name", "---"))
                self.supplier_var.set(found_info.get("supplier", "---"))
                self.delivery_date_var.set(found_info.get("delivery_date", "---"))
                self.arrangement_status_var.set(found_info.get("arrangement_status", "---"))
                self.source_csv_path_var.set(target_filename) # 検索したファイル名を表示
                self.status_var.set(f"バーコード '{barcode_value}' の情報が見つかりました。(ファイル: {target_filename})")
                print(f"ログ: バーコード '{barcode_value}' の情報がファイル '{target_filename}' で見つかりました。")
                print(f"ログ: 部品No: {self.parts_no_var.get()}, 図番: {self.drawing_no_var.get()}")
                # self.same_drawing_search_button.config(state=tk.NORMAL) # 同一図番検索ボタンを有効化 (ボタン削除のため不要)
                found_item_in_any_file = True

        else: # 工事番号指定なし (全検索)
            self.config.set("last_construction_no_part_viewer", "") # 全検索時は空を保存
            self.source_csv_path_var.set("全s.csvファイルを検索中...")
            self.status_var.set("全s.csvファイルを検索中...")
            self.root.update_idletasks() # UIを即時更新

            # Treeviewをクリア
            self.same_drawing_tree.delete(*self.same_drawing_tree.get_children())

            # 全ファイルから見つかったアイテムを収集するリスト (Treeview表示用)
            all_found_barcode_items_for_tree = []

            if not os.path.isdir(self.source_data_dir):
                self.status_var.set(f"エラー: Sourceディレクトリが見つかりません: {self.source_data_dir}")
                messagebox.showerror("ディレクトリエラー", f"Sourceディレクトリが見つかりません:\n{self.source_data_dir}", parent=self.root)
                return

            first_found_info_details = None # 最初に見つかった情報を保持する辞書 (情報とファイル名)

            for filename in sorted(os.listdir(self.source_data_dir)): # ソートして一貫性を
                if filename.endswith("s.csv"):
                    filepath = os.path.join(self.source_data_dir, filename)
                    self.status_var.set(f"全s.csvファイルを検索中: {filename}")
                    self.root.update_idletasks()

                    source_data_map = self._load_source_data_from_file(filepath)

                    if source_data_map is None:  # 読み込みエラーまたはカラムエラー
                        # _load_source_data_from_file内でstatus_varは設定済みの場合がある
                        # Treeviewにエラー行を追加
                        dummy_values = ["(読込エラー)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [filename]
                        all_found_barcode_items_for_tree.append(dummy_values)
                        continue
                    elif not source_data_map:  # ファイルは空
                        no_hit_values = ["(該当なし)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [filename]
                        all_found_barcode_items_for_tree.append(no_hit_values)
                        continue

                    current_file_found_info = source_data_map.get(normalized_barcode)  # バーコード検索
                    if current_file_found_info:  # このファイルでバーコードが見つかった
                        if not found_item_in_any_file:  # 最初に見つかった情報を保持
                            first_found_info_details = {"info": current_file_found_info, "filename": filename}
                            found_item_in_any_file = True

                        # TreeView に表示する情報を追加
                        # self.csv_data_columns_for_same_drawing_search の順序に従って値を収集
                        item_values_list = []
                        # 1. 発注伝票No. (configでのカラム名に対応するが、値は検索したバーコード値)
                        item_values_list.append(barcode_value) # 検索に使用したバーコード値を表示

                        # 2. 部品No.
                        item_values_list.append(current_file_found_info.get("parts", ""))

                        # 3. 図番
                        item_values_list.append(current_file_found_info.get("drawing", ""))

                        # 4. 納入数
                        item_values_list.append(current_file_found_info.get("delivery_count", ""))

                        # 5. 品名
                        item_values_list.append(current_file_found_info.get("item_name", ""))

                        # 6. 仕入先
                        item_values_list.append(current_file_found_info.get("supplier", ""))

                        # 7. 納期
                        item_values_list.append(current_file_found_info.get("delivery_date", ""))

                        # 8. 手配状況
                        item_values_list.append(current_file_found_info.get("arrangement_status", ""))
                        
                        item_values_from_csv = item_values_list
                        item_values_for_tree = item_values_from_csv + [filename]
                        all_found_barcode_items_for_tree.append(item_values_for_tree)
                    else:  # このファイルには該当バーコードがなかった場合
                        no_hit_values = ["(該当なし)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [filename]
                        all_found_barcode_items_for_tree.append(no_hit_values)

            # TreeView に全ファイルの結果を表示
            if all_found_barcode_items_for_tree:
                for item_vals in all_found_barcode_items_for_tree:
                    self.same_drawing_tree.insert("", tk.END, values=item_vals)

            if found_item_in_any_file and first_found_info_details:
                # 最初に見つかった情報をUIに表示
                info_to_display = first_found_info_details["info"]
                filename_displayed = first_found_info_details["filename"]
                self.parts_no_var.set(info_to_display.get("parts", "---"))
                self.drawing_no_var.set(info_to_display.get("drawing", "---"))
                self.delivery_count_var.set(info_to_display.get("delivery_count", "---"))
                self.item_name_var.set(info_to_display.get("item_name", "---"))
                self.supplier_var.set(info_to_display.get("supplier", "---"))
                self.delivery_date_var.set(info_to_display.get("delivery_date", "---"))
                self.arrangement_status_var.set(info_to_display.get("arrangement_status", "---"))
                self.source_csv_path_var.set(filename_displayed)
                self.status_var.set(f"バーコード '{barcode_value}' の情報が {filename_displayed} で見つかりました。(全s.csv検索)")
                print(f"ログ: バーコード '{barcode_value}' の情報がファイル '{filename_displayed}' で見つかりました (全s.csv検索)。")
                print(f"ログ: 部品No: {self.parts_no_var.get()}, 図番: {self.drawing_no_var.get()}")
                # self.same_drawing_search_button.config(state=tk.NORMAL) # (ボタン削除のため不要)
            elif not found_item_in_any_file:  # ループ後、結局どのファイルでも見つからなかった場合
                self.source_csv_path_var.set("工事番号未入力時は全s.csvファイルを検索")  # 検索後に表示を戻す
                print(f"ログ: バーコード '{barcode_value}' に該当する情報は見つかりませんでした (全s.csv検索)。")
                # Treeviewには読み込みエラーや該当なしのファイル情報が表示される
                self.status_var.set(f"バーコード '{barcode_value}' に該当する情報は見つかりませんでした。")
                messagebox.showinfo("検索結果", f"バーコード '{barcode_value}' (正規化後: '{normalized_barcode}') に該当する情報は見つかりませんでした。", parent=self.root)

        # バーコード検索後、メイン表示エリアに図番が表示されていれば、同一図番検索を実行
        if found_item_in_any_file and self.drawing_no_var.get() and self.drawing_no_var.get() != "---":
            self.status_var.set(f"バーコード検索完了。図番 '{self.drawing_no_var.get()}' の同一図番検索を実行します...")
            print(f"ログ: バーコード検索完了。図番 '{self.drawing_no_var.get()}' の同一図番検索を自動実行します。")
            self.root.update_idletasks()
            self._search_same_drawing_no() # 自動で同一図番検索を実行


    def _search_same_drawing_no(self):
        self.same_drawing_tree.delete(*self.same_drawing_tree.get_children()) # 結果をクリア
        current_drawing_no = self.drawing_no_var.get()
        construction_no_val = self.construction_no_entry.get().strip()

        if not current_drawing_no or current_drawing_no == "---":
            messagebox.showwarning("検索エラー", "検索対象の図番がありません。", parent=self.root)
            print("ログ: 同一図番検索エラー - 検索対象の図番がありません。")
            return

        files_to_search_paths = []
        search_scope_message = ""

        if construction_no_val:
            # 工事番号が指定されていれば、そのファイルのみを対象とする
            target_filename = f"{construction_no_val}s.csv"
            target_filepath = os.path.join(self.source_data_dir, target_filename)
            if os.path.exists(target_filepath):
                files_to_search_paths.append(target_filepath)
                search_scope_message = f"ファイル '{target_filename}'"
            else:
                messagebox.showerror("ファイルエラー", f"指定されたCSVファイルが見つかりません:\n{target_filepath}", parent=self.root)
                self.status_var.set(f"エラー: CSVファイル {target_filename} が見つかりません。")
                print(f"ログ: 同一図番検索エラー - 指定CSVファイル '{target_filename}' が見つかりません。")
                return
        else:
            # 工事番号が指定されていない場合は、Sourceディレクトリ内の全s.csvファイルを検索
            if not os.path.isdir(self.source_data_dir):
                self.status_var.set(f"エラー: Sourceディレクトリが見つかりません: {self.source_data_dir}")
                messagebox.showerror("ディレクトリエラー", f"Sourceディレクトリが見つかりません:\n{self.source_data_dir}", parent=self.root)
                return
                print(f"ログ: 同一図番検索エラー - Sourceディレクトリ '{self.source_data_dir}' が見つかりません。")

            for filename in sorted(os.listdir(self.source_data_dir)):
                if filename.endswith("s.csv"):
                    files_to_search_paths.append(os.path.join(self.source_data_dir, filename))
            
            if not files_to_search_paths:
                messagebox.showinfo("検索対象なし", f"Sourceディレクトリ '{self.source_data_dir}' に検索対象のs.csvファイルがありません。", parent=self.root)
                self.status_var.set("情報: 検索対象のs.csvファイルがありません。")
                print(f"ログ: 同一図番検索 - Sourceディレクトリ '{self.source_data_dir}' に検索対象のs.csvファイルがありません。")
                return
            search_scope_message = f"全s.csvファイル ({len(files_to_search_paths)}件対象)"

        print(f"ログ: 図番 '{current_drawing_no}' の同一図番検索を開始します。対象: {search_scope_message}")
        self.status_var.set(f"{search_scope_message} 内で図番 '{current_drawing_no}' を検索中...")
        self.root.update_idletasks()

        all_found_items_values = []
        processed_files_count = 0
        total_hits = 0 # 全ファイルでのヒット総数

        for target_filepath in files_to_search_paths:
            current_csv_filename = os.path.basename(target_filepath)
            if len(files_to_search_paths) > 1:
                processed_files_count += 1
                self.status_var.set(f"図番 '{current_drawing_no}' 検索中 ({processed_files_count}/{len(files_to_search_paths)}): {current_csv_filename}")
                self.root.update_idletasks()
            
            found_in_this_file_count = 0 # このファイルで見つかったアイテム数

            try:
                with open(target_filepath, mode='r', newline='', encoding='utf-8-sig') as file:
                    reader = csv.DictReader(file)
                    # ヘッダーチェックはCSVから読み込むカラムで行う (self.csv_data_columns_for_same_drawing_search を使用)
                    if not reader.fieldnames or not all(col in reader.fieldnames for col in self.csv_data_columns_for_same_drawing_search):
                        warning_msg = f"ファイル '{current_csv_filename}' のヘッダーが期待通りではありません (必要なカラム: {', '.join(self.csv_data_columns_for_same_drawing_search)})。このファイルはスキップします。"
                        print(f"警告: {warning_msg}")
                        if len(files_to_search_paths) == 1:
                             messagebox.showwarning("CSVヘッダー不備", warning_msg, parent=self.root)
                        # ヘッダー不備の場合も情報をリストに追加
                        # self.same_drawing_tree_display_columns は表示用カラムリスト (ファイル名列含む)
                        dummy_values = ["(ヘッダー不備)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [current_csv_filename]
                        all_found_items_values.append(dummy_values)
                        continue 

                    for row_data in reader:
                        drawing_no_in_row = row_data.get(self.drawing_no_col, "").strip()
                        if drawing_no_in_row == current_drawing_no:
                            item_values_from_csv = [row_data.get(col, "") for col in self.csv_data_columns_for_same_drawing_search]
                            item_values_for_tree = item_values_from_csv + [current_csv_filename] # ファイル名を追加
                            all_found_items_values.append(item_values_for_tree)
                            found_in_this_file_count += 1
                            total_hits +=1
            except Exception as e:
                error_msg = f"CSVファイル '{current_csv_filename}' の読み込み中にエラーが発生しました: {e}"
                print(f"エラー: {error_msg}")
                if len(files_to_search_paths) == 1:
                    messagebox.showerror("読み込みエラー", error_msg, parent=self.root)
                self.status_var.set(f"エラー: {current_csv_filename} 読込失敗。他ファイル検索継続...")
                # 読み込みエラーの場合も情報をリストに追加
                dummy_values = ["(読込エラー)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [current_csv_filename]
                all_found_items_values.append(dummy_values)
                continue

            if found_in_this_file_count == 0 and \
               not any(("(ヘッダー不備)" in str(val) or "(読込エラー)" in str(val)) and current_csv_filename in str(val) for val_list in all_found_items_values for val in val_list if isinstance(val, str)):
                # このファイルでヒットがなく、かつヘッダー不備や読み込みエラーでもない場合、「該当なし」行を追加
                no_hit_values = ["(該当なし)"] + ["---"] * (len(self.same_drawing_tree_display_columns) - 2) + [current_csv_filename]
                all_found_items_values.append(no_hit_values)

        if all_found_items_values:
            for item_vals in all_found_items_values:
                self.same_drawing_tree.insert("", tk.END, values=item_vals)
            if total_hits > 0:
                print(f"ログ: 図番 '{current_drawing_no}' で {total_hits} 件見つかりました。({search_scope_message})")
                self.status_var.set(f"図番 '{current_drawing_no}' で {total_hits} 件見つかりました。({search_scope_message})")
            else: # ヒットは0件だが、検索対象ファイルの情報は表示する場合
                print(f"ログ: 図番 '{current_drawing_no}' に該当する部品は {search_scope_message} 内に見つかりませんでした。")
                self.status_var.set(f"図番 '{current_drawing_no}' に該当する部品は {search_scope_message} 内に見つかりませんでした。検索対象ファイルの結果を表示します。")
        else:
            # files_to_search_paths が空だった場合など (通常は先にチェックされる)
            self.status_var.set(f"図番 '{current_drawing_no}' の検索対象ファイルがありませんでした。")
            print(f"ログ: 図番 '{current_drawing_no}' の検索対象ファイルがありませんでした。")
            messagebox.showinfo("検索結果", f"図番 '{current_drawing_no}' の検索対象ファイルがありませんでした。", parent=self.root)


    def _start_barcode_scan_window(self):
        self.status_var.set("バーコードスキャン準備中...")
        self.scan_window = tk.Toplevel(self.root)
        # self.scan_window.transient(self.root) # メインウィンドウの子ウィンドウとして設定 (任意)
        self.scan_window.title("バーコードスキャン")
        self.scan_window.resizable(False, False)
        # スキャンウィンドウの初期サイズを設定してから右寄せ
        self.scan_window.geometry(f"{self.camera_width}x{self.camera_height + 50}") # ボタン分少し高さを確保

        # カメラ映像表示用ラベル
        self.video_label = ttk.Label(self.scan_window)
        self.video_label.pack()

        # キャンセルボタン
        cancel_button = ttk.Button(self.scan_window, text="キャンセル", command=self._stop_barcode_scan)
        cancel_button.pack(pady=5)

        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            messagebox.showerror("カメラエラー", f"カメラ(インデックス: {self.camera_index})を開けませんでした。", parent=self.scan_window)
            self._stop_barcode_scan()
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        
        self.scan_window.protocol("WM_DELETE_WINDOW", self._stop_barcode_scan)
        self.is_scanning = True
        self._center_and_right_align_window(self.scan_window, window_width_offset=10, window_height_offset=10) # スキャンウィンドウも右寄せ
        self.status_var.set("バーコードスキャン中...")
        self._update_scan_feed()

    def _update_scan_feed(self):
        if not self.is_scanning or not hasattr(self, 'cap') or not self.cap.isOpened():
            return

        start_time = time.time()
        ret, frame = self.cap.read()

        if ret:
            barcodes, analyzed_frame = self.barcode_analyzer.analyze(frame.copy()) # frameをコピーして渡す

            for barcode in barcodes:
                barcode_info = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                if barcode_type == self.barcode_type_to_scan and len(barcode_info) == self.expected_barcode_length:
                    self._on_barcode_scanned(barcode_info)
                    return # スキャン成功したらループ終了

            # Tkinterで表示するために画像を変換
            img = cv2.cvtColor(analyzed_frame, cv2.COLOR_BGR2RGB)
            img_tk = tk.PhotoImage(data=cv2.imencode('.ppm', img)[1].tobytes()) # PPM経由
            self.video_label.imgtk = img_tk # 参照を保持
            self.video_label.configure(image=img_tk)

        # FPS制御
        elapsed_time = time.time() - start_time
        wait_time = (1.0 / self.target_fps) - elapsed_time
        if wait_time > 0:
            self.root.after(int(wait_time * 1000), self._update_scan_feed)
        else:
            self.root.after(1, self._update_scan_feed) # 最小遅延で再試行

    def _on_barcode_scanned(self, barcode_value):
        self.barcode_entry.delete(0, tk.END)
        self.barcode_entry.insert(0, barcode_value)
        self.status_var.set(f"バーコード '{barcode_value}' をスキャンしました。")
        self._stop_barcode_scan()
        self.root.after(100, self._on_search) # 自動検索

    def _stop_barcode_scan(self):
        self.is_scanning = False
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        if hasattr(self, 'scan_window') and self.scan_window.winfo_exists():
            self.scan_window.destroy()
        self.status_var.set("準備完了")

    def _on_closing(self):
        current_construction_no = self.construction_no_entry.get().strip()
        if current_construction_no: # 空でなければ保存
            self.config.set("last_construction_no_part_viewer", current_construction_no)
        self.config.save_config() # 明示的に保存
        print("部品情報表示ツールを終了します。") # 終了ログを出力
        self.root.destroy()

if __name__ == "__main__":
    initial_cn = None
    initial_bc = None

    if len(sys.argv) == 3: # G_PartInfoViewer.py <construction_no> <barcode_value>
        initial_cn = sys.argv[1]
        initial_bc = sys.argv[2]
        print(f"コマンドライン引数から工事番号: {initial_cn}, バーコード: {initial_bc} を受け取りました。")
    elif len(sys.argv) > 1:
        print("使用法: python G_PartInfoViewer.py [工事番号 バーコード値]")

        print("使用法: python G_PartInfoViewer.py [工事番号 バーコード値]")

    # 設定ファイルのロード
    app_root = tk.Tk() # messagebox用に先に作成
    try:
        config_instance = Config("config.json")
    except Exception as e:
        print(f"設定ファイル(config.json)の読み込みに失敗しました: {e}")
        messagebox.showerror("設定エラー", f"設定ファイル(config.json)の読み込みに失敗しました。\n{e}", parent=app_root)
        app_root.destroy()
        sys.exit(1) # エラー終了

    try:
        viewer = PartInfoViewer(app_root, config_instance, initial_construction_no=initial_cn, initial_barcode_value=initial_bc)
        app_root.mainloop()
    except Exception as e:
        print(f"G_PartInfoViewer の起動中にエラーが発生しました: {e}")
        messagebox.showerror("起動エラー", f"部品情報表示ツールの起動に失敗しました。\n{e}", parent=app_root)
        app_root.destroy()