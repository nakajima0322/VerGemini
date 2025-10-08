# G_ConfigEditor.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import shutil
from collections import OrderedDict


class ConfigEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("設定ファイルエディタ")
        self.config_path = "config.json"
        self.widgets = {}
        self.config_definition = []
        self.mapping_widgets = [] # マッピング用ウィジェットを保持
        self.window_geometry_widgets = {} # ウィンドウジオメトリ用ウィジェットを保持

        # 設定対象のツールクラス名をリストで定義
        self.target_tool_classes = [
            "DrawingNumberViewer", # G_DrawingNumberViewer.py
            "PartInfoViewer",      # G_PartInfoViewer.py
            "WorkflowManager"     # G_WorkflowManager.py
        ]

        # プリセットの定義
        self.presets = OrderedDict([
            ("VGA 640x480", "640x480"),
            ("SVGA 800x600", "800x600"),
            ("XGA 1024x768", "1024x768")
        ])

        # スタイルを管理するインスタンス
        self.style = ttk.Style()

        # UI更新中の再帰呼び出しを防ぐためのフラグ
        self._is_programmatically_updating = False

        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(expand=True, fill="both")

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both", pady=5)

        # タブを作成
        self.tab_basic = ttk.Frame(self.notebook, padding="10")
        self.tab_folders = ttk.Frame(self.notebook, padding="10")
        self.tab_csv = ttk.Frame(self.notebook, padding="10")
        self.tab_display = ttk.Frame(self.notebook, padding="10")
        self.tab_mapping = ttk.Frame(self.notebook, padding="10") # マッピング用タブ
        self.tab_window = ttk.Frame(self.notebook, padding="10") # ウィンドウ設定用タブ
        self.tab_state = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.tab_basic, text="基本設定")
        self.notebook.add(self.tab_folders, text="フォルダ設定")
        self.notebook.add(self.tab_csv, text="CSV列名設定")
        self.notebook.add(self.tab_display, text="動作・表示設定")
        self.notebook.add(self.tab_mapping, text="表示名マッピング") # タブ追加
        self.notebook.add(self.tab_window, text="ウィンドウ設定")
        self.notebook.add(self.tab_state, text="状態(表示のみ)")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=5)
        save_button = ttk.Button(button_frame, text="保存して閉じる", command=self.save_and_close)
        save_button.pack(side="right", padx=5)
        cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.root.destroy)
        cancel_button.pack(side="right")

        self.load_config()
        self._define_config_structure()
        self.create_widgets()
        self.populate_data()
        
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.root.bind('<Escape>', lambda e: self.root.destroy())

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f, object_pairs_hook=OrderedDict)
        except FileNotFoundError:
            messagebox.showinfo("情報", f"{self.config_path} が見つかりませんでした。\nデフォルト設定で起動します。\n保存すると新しい設定ファイルが作成されます。")
            self.config_data = self._get_default_config()
        except json.JSONDecodeError:
            messagebox.showerror("エラー", f"{self.config_path} は不正なJSON形式です。")
            self.root.destroy()

    def _get_default_config(self):
        """デフォルトの設定値を OrderedDict として返す"""
        # この内容は config.json の基本構造と一致させる
        default_conf = OrderedDict([
            ("___ACTIVE_SETTINGS___", "--- 現在有効な設定 ---"),
            ("auto_stop", True),
            ("barcode_type", "CODE39"),
            ("camera_height", 480),
            ("camera_index", 0),
            ("camera_width", 640),
            ("data_dir", "data"),
            ("default_construction_number", "0000"),
            ("default_location", "unknown"),
            ("default_source_csv_filename", "order_list.csv"),
            ("display_lines", 4),
            ("display_text_mapping", OrderedDict([
                ("カブト1F", "Kabuto 1F"),
                ("カブト2F", "Kabuto 2F"),
                ("コンテナ", "Container"),
                ("棚", "Shelf"),
                ("棚（箱）", "Shelf (Box)")
            ])),
            ("display_time", 300),
            ("expected_length", 10),
            ("font_scale", 0.5),
            ("idle_timeout", 300),
            ("log_dir", "log"),
            ("manual_entry_drawing_barcode_type", "MANUAL"),
            ("overlay_alpha", 0.8),
            ("overlay_color", [0, 0, 0]),
            ("overlay_enabled", True),
            ("scan_log", "ScanBCD.log"),
            ("source_data_dir", "Source"),
            ("source_csv_arrangement_status_column", "手配"),
            ("source_csv_delivery_count_column", "納入数"),
            ("source_csv_delivery_date_column", "納期"),
            ("source_csv_drawing_no_column", "図番"),
            ("source_csv_item_name_column", "品名"),
            ("source_csv_order_no_column", "発注伝票№"),
            ("source_csv_parts_no_column", "部品№"),
            ("source_csv_supplier_column", "仕入先"),
            ("target_fps", 30),
            ("___STATE_AND_HISTORY___", "--- 前回終了時の状態（自動更新） ---"),
            ("last_construction_no_part_viewer", ""),
            ("last_construction_number", ""),
            ("last_construction_number_scanner", ""),
            ("last_filter_start_value", "0"),
            ("last_location_filter_viewer", "すべての場所"),
            ("last_source_csv_path", ""),
            ("___WINDOW_GEOMETRIES___", "--- ウィンドウの位置とサイズ（自動更新） ---"),
            ("window_geometries", OrderedDict()),
            ("___UNUSED_OR_DEPRECATED___", "--- 未使用または旧式の項目 ---")
        ])
        return default_conf

    def _define_config_structure(self):
        """設定項目の構造を定義します。"""
        self.config_definition = [
            # (key, label, type, tab, options)
            ("camera_index", "カメラ番号", "entry", self.tab_basic, {"type": int}),
            ("camera_width", "カメラ解像度 (幅)", "entry", self.tab_basic, {"type": int}),
            ("camera_height", "カメラ解像度 (高さ)", "entry", self.tab_basic, {"type": int}),
            ("target_fps", "ターゲットFPS", "entry", self.tab_basic, {"type": int}),
            ("barcode_type", "バーコードタイプ", "entry", self.tab_basic, {"type": str}),
            ("expected_length", "バーコード期待長", "entry", self.tab_basic, {"type": int}),

            ("data_dir", "データフォルダ名", "entry", self.tab_folders, {"type": str}),
            ("log_dir", "ログフォルダ名", "entry", self.tab_folders, {"type": str}),
            ("source_data_dir", "発注伝票フォルダ名", "entry", self.tab_folders, {"type": str}),
            ("scan_log", "スキャンログファイル名", "entry", self.tab_folders, {"type": str}),

            ("source_csv_order_no_column", "発注伝票№", "entry", self.tab_csv, {"type": str}),
            ("source_csv_drawing_no_column", "図番", "entry", self.tab_csv, {"type": str}),
            ("source_csv_parts_no_column", "部品№", "entry", self.tab_csv, {"type": str}),
            ("source_csv_item_name_column", "品名", "entry", self.tab_csv, {"type": str}),
            ("source_csv_delivery_date_column", "納期", "entry", self.tab_csv, {"type": str}),
            ("source_csv_delivery_count_column", "納入数", "entry", self.tab_csv, {"type": str}),
            ("source_csv_supplier_column", "仕入先", "entry", self.tab_csv, {"type": str}),
            ("source_csv_arrangement_status_column", "手配", "entry", self.tab_csv, {"type": str}),

            ("auto_stop", "自動停止を有効にする", "checkbutton", self.tab_display, {}),
            ("overlay_enabled", "オーバーレイ表示を有効にする", "checkbutton", self.tab_display, {}),
            ("overlay_alpha", "オーバーレイ透明度 (0.0-1.0)", "entry", self.tab_display, {"type": float}),
            ("overlay_color", "オーバーレイ色 (R, G, B)", "rgb", self.tab_display, {}),
            ("display_time", "結果表示時間 (ms)", "entry", self.tab_display, {"type": int}),
            ("idle_timeout", "アイドルタイムアウト (秒)", "entry", self.tab_display, {"type": int}),
            ("default_construction_number", "デフォルト工事番号", "entry", self.tab_display, {"type": str}),
            ("default_location", "デフォルト保管場所", "entry", self.tab_display, {"type": str}),
        ]

    def create_widgets(self):
        # 設定定義に基づいてウィジェットを動的に作成
        for key, label, widget_type, tab, options in self.config_definition:
            parent = tab
            # CSV設定は専用のフレームに入れる
            if tab == self.tab_csv and not hasattr(self, 'csv_frame'):
                self.csv_frame = ttk.LabelFrame(self.tab_csv, text="発注伝票CSVの列名", padding="10")
                self.csv_frame.pack(expand=True, fill="both")
                parent = self.csv_frame
            elif tab == self.tab_csv:
                parent = self.csv_frame

            if widget_type == "entry":
                self._add_entry(parent, key, label)
            elif widget_type == "checkbutton":
                self._add_checkbutton(parent, key, label)
            elif widget_type == "rgb":
                self._add_rgb_entry(parent, key, label)

        # --- 表示名マッピングタブ ---
        self._create_mapping_tab()

        # --- ウィンドウ設定タブ ---
        self._create_window_geometry_tab()

        # --- 状態(表示のみ) ---
        self.state_frame = ttk.LabelFrame(self.tab_state, text="前回終了時の状態 (編集不可)", padding="10")
        self.state_frame.pack(expand=True, fill="both")
        for key in self.config_data:
            if key.startswith("last_"):
                self._add_entry(self.state_frame, key, key, readonly=True)

    def _add_widget(self, parent, label_text, width=25):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        label = ttk.Label(frame, text=label_text, width=width)
        label.pack(side='left', anchor='w')
        return frame

    def _add_entry(self, parent, key, label_text, readonly=False):
        frame = self._add_widget(parent, label_text)
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var)
        if readonly:
            entry.config(state="readonly")
        entry.pack(side='left', expand=True, fill='x')
        self.widgets[key] = {"widget_type": "entry", "var": var}

    def _add_checkbutton(self, parent, key, label_text):
        frame = self._add_widget(parent, label_text)
        var = tk.BooleanVar()
        chk = ttk.Checkbutton(frame, variable=var)
        chk.pack(side='left')
        self.widgets[key] = {"widget_type": "checkbutton", "var": var}

    def _add_rgb_entry(self, parent, key, label_text):
        # Main frame for the whole widget
        main_frame = self._add_widget(parent, label_text)
        
        vars_str = [tk.StringVar() for _ in range(3)]
        vars_int = [tk.IntVar() for _ in range(3)]

        # Color preview swatch
        color_preview = tk.Label(main_frame, text="    ", bg="#000000", relief="sunken", borderwidth=2)
        color_preview.pack(side="left", padx=5, anchor='n') # Anchor to north

        # Frame for the RGB controls
        rgb_frame = ttk.Frame(main_frame)
        rgb_frame.pack(side="left", fill="x", expand=True)

        for i, color in enumerate(["R", "G", "B"]):
            row_frame = ttk.Frame(rgb_frame)
            row_frame.pack(fill='x')
            
            ttk.Label(row_frame, text=color, width=2).pack(side="left")
            
            entry = ttk.Entry(row_frame, textvariable=vars_str[i], width=5)
            entry.pack(side="left", padx=5)

            # Slider -> Entry update
            def slider_callback(value, str_var=vars_str[i]):
                str_var.set(str(int(float(value))))

            slider = ttk.Scale(
                row_frame,
                from_=0,
                to=255,
                orient="horizontal",
                variable=vars_int[i],
                command=slider_callback
            )
            slider.pack(side="left", fill="x", expand=True)

        # Entry -> Slider & Preview update (via trace)
        def on_entry_change(*args, k=key):
            self._update_color_preview(k)

        for var in vars_str:
            var.trace_add("write", on_entry_change)

        self.widgets[key] = {
            "widget_type": "rgb", 
            "vars": vars_str, # Keep original name for compatibility
            "int_vars": vars_int,
            "preview": color_preview
        }

    def _parse_color_value(self, s_val):
        """ 入力値を10進数または16進数として解釈する """ 
        s_val = s_val.strip()
        if not s_val:
            return 0
        try:
            # まず10進数として解釈を試みる
            return int(s_val)
        except ValueError:
            # 失敗した場合、16進数として解釈を試みる
            return int(s_val, 16)

    def _update_color_preview(self, key):
        """RGBエントリーの色のプレビューを更新する"""
        widget_info = self.widgets.get(key)
        if not widget_info or widget_info["widget_type"] != "rgb":
            return

        try:
            # Parse values from Entry's StringVar
            r = self._parse_color_value(widget_info["vars"][0].get())
            g = self._parse_color_value(widget_info["vars"][1].get())
            b = self._parse_color_value(widget_info["vars"][2].get())

            # Clamp values to 0-255
            r = max(0, min(r, 255))
            g = max(0, min(g, 255))
            b = max(0, min(b, 255))

            # Update the Sliders' IntVar
            if widget_info["int_vars"][0].get() != r:
                widget_info["int_vars"][0].set(r)
            if widget_info["int_vars"][1].get() != g:
                widget_info["int_vars"][1].set(g)
            if widget_info["int_vars"][2].get() != b:
                widget_info["int_vars"][2].set(b)

            # Update the color preview swatch
            color_hex = f"#{r:02x}{g:02x}{b:02x}"
            widget_info["preview"].config(bg=color_hex)
        except (ValueError, tk.TclError):
            # 解釈できない値が入力された場合は、プレビューをグレーに設定
            widget_info["preview"].config(bg="#808080")

    def _create_mapping_tab(self):
        header_frame = ttk.Frame(self.tab_mapping)
        header_frame.pack(fill='x', padx=5, pady=(0, 2))
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=1)
        header_frame.columnconfigure(2, weight=0)
        ttk.Label(header_frame, text="元々の名前", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header_frame, text="表示名", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, sticky="w")

        # スクロール可能な領域のコンテナ
        container = ttk.Frame(self.tab_mapping)
        container.pack(fill="both", expand=True)
        
        self.mapping_canvas = tk.Canvas(self.tab_mapping)
        scrollbar = ttk.Scrollbar(self.tab_mapping, orient="vertical", command=self.mapping_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.mapping_canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.mapping_canvas.configure(scrollregion=self.mapping_canvas.bbox("all")))
        self.mapping_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.mapping_canvas.configure(yscrollcommand=scrollbar.set)

        # scrollable_frameの列設定
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.columnconfigure(1, weight=1)
        self.scrollable_frame.columnconfigure(2, weight=0)

        self.mapping_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        add_button = ttk.Button(self.tab_mapping, text="マッピングを追加", command=self._add_mapping_row)
        add_button.pack(side="bottom", pady=5)

    def _add_mapping_row(self, key_text="", value_text="", row_index=None):
        if row_index is None:
            row_index = len(self.mapping_widgets)

        key_var = tk.StringVar(value=key_text)
        value_var = tk.StringVar(value=value_text)

        key_entry = ttk.Entry(self.scrollable_frame, textvariable=key_var)
        key_entry.grid(row=row_index, column=0, padx=(5,2), pady=2, sticky="ew")
        value_entry = ttk.Entry(self.scrollable_frame, textvariable=value_var)
        value_entry.grid(row=row_index, column=1, padx=2, pady=2, sticky="ew")

        # 削除ボタン用のフレーム
        delete_button = ttk.Button(self.scrollable_frame, text="削除", command=lambda k=key_var: self._delete_mapping_row(k))
        delete_button.grid(row=row_index, column=2, padx=(2,5), pady=2)
        
        self.mapping_widgets.append((key_var, value_var, delete_button, key_entry, value_entry))

    def _create_window_geometry_tab(self):
        """ウィンドウジオメトリ設定用のタブUIを作成する"""
        self.window_geometry_frame = ttk.Frame(self.tab_window)
        self.window_geometry_frame.pack(fill='x', pady=5)
        # 親フレームに列設定を適用
        self.window_geometry_frame.columnconfigure(0, weight=3) # ツール名
        self.window_geometry_frame.columnconfigure(1, weight=2) # サイズプリセット
        self.window_geometry_frame.columnconfigure(2, weight=1) # 幅補正
        self.window_geometry_frame.columnconfigure(3, weight=1) # 高さ補正
        self.window_geometry_frame.columnconfigure(4, weight=2) # 位置プリセット
        self.window_geometry_frame.columnconfigure(5, weight=1) # X補正
        self.window_geometry_frame.columnconfigure(6, weight=1) # Y補正
        self.window_geometry_frame.columnconfigure(7, weight=0) # プレビューボタン

        # ヘッダーを親フレームの0行目に配置
        ttk.Label(self.window_geometry_frame, text="ツール名", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, padx=5, sticky="w")
        ttk.Label(self.window_geometry_frame, text="プリセット", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        ttk.Label(self.window_geometry_frame, text="X補正", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=2, padx=5, sticky="w")
        ttk.Label(self.window_geometry_frame, text="Y補正", font=("TkDefaultFont", 9, "bold")).grid(row=0, column=3, padx=5, sticky="w")

        info_label = ttk.Label(self.tab_window, text="注意: 各ツールの終了時に現在のウィンドウ位置で自動更新されます。", foreground="gray", wraplength=500)
        info_label.pack(side="bottom", pady=10)

    def _add_window_geometry_row(self, row_index, tool_name, geometry_string):
        """ウィンドウジオメトリ設定の1行をUIに追加する"""
        row_frame = self.window_geometry_frame # 親フレームを直接使用

        # 変数
        preset_var = tk.StringVar(value="SVGA 800x600") # デフォルトをSVGAに
        width_offset_var = tk.StringVar(value="0")
        height_offset_var = tk.StringVar(value="0")
        offset_x_var = tk.StringVar(value="0")
        offset_y_var = tk.StringVar(value="0")
        pos_preset_var = tk.StringVar(value="中央") # デフォルトを設定

        # ウィジェット
        # 1行目: サイズ関連
        ttk.Label(row_frame, text=tool_name).grid(row=row_index, column=0, padx=5, pady=2, sticky="w")
        preset_combo = ttk.Combobox(row_frame, textvariable=preset_var, values=list(self.presets.keys()), state="readonly", style="TCombobox", width=13)
        self.style.map(f"{tool_name}.TCombobox", fieldbackground=[("readonly", "white")])
        preset_combo.configure(style=f"{tool_name}.TCombobox")
        preset_combo.grid(row=row_index, column=1, padx=5, pady=2, sticky="ew")
        width_offset_spinbox = ttk.Spinbox(row_frame, from_=-10000, to=10000, increment=1, textvariable=width_offset_var, width=5)
        width_offset_spinbox.grid(row=row_index, column=2, padx=5, pady=2, sticky="ew")
        height_offset_spinbox = ttk.Spinbox(row_frame, from_=-10000, to=10000, increment=1, textvariable=height_offset_var, width=5)
        height_offset_spinbox.grid(row=row_index, column=3, padx=5, pady=2, sticky="ew")

        # 2行目: 位置関連
        pos_preset_options = ["中央", "右上", "左上"]
        pos_preset_combo = ttk.Combobox(row_frame, textvariable=pos_preset_var, values=pos_preset_options, state="readonly", style="TCombobox",width=5)
        pos_preset_combo.grid(row=row_index + 1, column=1, padx=5, pady=2, sticky="ew")
        offset_x_spinbox = ttk.Spinbox(row_frame, from_=-10000, to=10000, increment=1, textvariable=offset_x_var, width=5)
        offset_x_spinbox.grid(row=row_index + 1, column=2, padx=5, pady=2, sticky="ew")
        offset_y_spinbox = ttk.Spinbox(row_frame, from_=-10000, to=10000, increment=1, textvariable=offset_y_var, width=5)
        offset_y_spinbox.grid(row=row_index + 1, column=3, padx=5, pady=2, sticky="ew")

        def update_spinbox_ranges(*args):
            """ウィンドウサイズに基づいてSpinboxの入力範囲を更新する"""
            try:
                size_preset_name = preset_var.get()
                pos_preset_name = pos_preset_var.get()
                size_str = self.presets.get(size_preset_name)
                if not size_str:
                    return
                base_w, base_h = map(int, size_str.split('x'))
                w_offset = int(width_offset_var.get() or 0)
                h_offset = int(height_offset_var.get() or 0)
                w = base_w + w_offset
                h = base_h + h_offset

                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()

                # 位置プリセットに基づいて基準座標を決定
                if pos_preset_name == "中央":
                    base_x = (screen_w - w) // 2
                    base_y = (screen_h - h) // 2
                elif pos_preset_name == "右上":
                    base_x = screen_w - w - 10
                    base_y = 10
                elif pos_preset_name == "左上":
                    base_x = 10
                    base_y = 10
                
                # 基準座標からのオフセット（補正値）の許容範囲を計算
                min_x_offset = -base_x
                max_x_offset = screen_w - (base_x + w)
                min_y_offset = -base_y
                max_y_offset = screen_h - (base_y + h)

                offset_x_spinbox.config(from_=min_x_offset, to=max_x_offset)
                offset_y_spinbox.config(from_=min_y_offset, to=max_y_offset)
            except (ValueError, KeyError, tk.TclError):
                pass # 入力途中やエラー時は何もしない

        def on_pos_preset_change(event):
            """位置プリセットが選択されたときの処理。補正値を更新し、入力可/不可を切り替える"""
            # プリセット選択時は、補正値を0にリセットする
            offset_x_var.set("0")
            offset_y_var.set("0")
            # スピンボックスの範囲も更新する
            update_spinbox_ranges()

        # プレビューボタン
        preview_button = ttk.Button(row_frame, text="プレビュー", command=lambda tn=tool_name: self._preview_window(tn))
        preview_button.grid(row=row_index + 1, column=0, padx=5, pady=2, sticky="w")

        # イベントハンドラ
        def on_preset_change(event):
            preset_name = preset_var.get()
            size_str = self.presets.get(preset_name)
            if size_str:
                # サイズ補正値のみをリセットし、位置補正値は変更しない
                width_offset_var.set("0")
                height_offset_var.set("0")
            # on_size_changeが呼ばれるので、ここでは不要
            # update_spinbox_ranges()

        def on_size_change(*args):
            """入力値が変更された際にプリセット表示を更新する"""
            if self._is_programmatically_updating:
                return

            is_size_custom = False
            try:
                w_offset = int(width_offset_var.get())
                h_offset = int(height_offset_var.get())

                if w_offset != 0 or h_offset != 0:
                    is_size_custom = True

            except ValueError:
                is_size_custom = True # 入力途中などで整数に変換できない場合はカスタム
            finally:
                self._is_programmatically_updating = False

            # サイズプリセットの文字色を変更
            self.style.configure(f"{tool_name}.TCombobox", foreground="red" if is_size_custom else "black")
            update_spinbox_ranges()

        preset_combo.bind("<<ComboboxSelected>>", on_preset_change)
        pos_preset_combo.bind("<<ComboboxSelected>>", on_pos_preset_change)
        width_offset_var.trace_add("write", on_size_change)
        height_offset_var.trace_add("write", on_size_change)
        offset_x_var.trace_add("write", on_size_change) # 補正値変更時もカスタムにする
        offset_y_var.trace_add("write", on_size_change) # 補正値変更時もカスタムにする

        # ウィジェットと変数を保存
        self.window_geometry_widgets[tool_name] = {
            "preset": preset_var,
            "width_offset": width_offset_var,
            "pos_preset": pos_preset_var,
            "height_offset": height_offset_var,
            "offset_x": offset_x_var, "offset_y": offset_y_var
        }

    def _find_running_process(self, tool_class_name):
        """一時ファイルから指定されたツールクラス名の実行中プロセス情報を探す"""
        # 機能削除のため、常にNoneを返す
        return None


    def _preview_window(self, tool_name):
        """指定されたツールの現在の設定値でプレビューウィンドウを表示する"""
        widgets = self.window_geometry_widgets.get(tool_name)
        if not widgets:
            return

        try:
            preset = widgets["preset"].get()
            pos_preset = widgets["pos_preset"].get()
            size_str = self.presets.get(preset)
            if not size_str:
                messagebox.showerror("エラー", f"プリセット '{preset}' のサイズが定義されていません。", parent=self.root)
                return
            
            base_w, base_h = map(int, size_str.split('x'))
            w_offset = int(widgets["width_offset"].get() or 0)
            h_offset = int(widgets["height_offset"].get() or 0)
            w = base_w + w_offset
            h = base_h + h_offset
            offset_x = int(widgets["offset_x"].get())
            offset_y = int(widgets["offset_y"].get())
        except ValueError:
            messagebox.showerror("入力エラー", "幅, 高さ, 補正値は整数で入力してください。", parent=self.root)
            return

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 位置プリセットに基づいて基準座標を決定
        if pos_preset == "中央":
            base_x = (screen_width - w) // 2
            base_y = (screen_height - h) // 2
        elif pos_preset == "右上":
            base_x = screen_width - w - 10
            base_y = 10
        elif pos_preset == "左上":
            base_x = 10
            base_y = 10
        else: # フォールバック
            base_x = (screen_width - w) // 2
            base_y = (screen_height - h) // 2
        # 基準座標に補正値を加算
        x = base_x + offset_x
        y = base_y + offset_y
        new_geometry = f"{w}x{h}+{x}+{y}"

        # プレビューウィンドウを作成
        preview_win = tk.Toplevel(self.root)
        preview_win.title(f"{tool_name} プレビュー")
        preview_win.configure(bg="white") # 背景を白にして空であることを分かりやすくする
        preview_win.geometry(new_geometry)

    def _get_pos_preset_from_offsets(self, tool_name):
        """現在のオフセット値から対応する位置プリセット名を返す"""
        # この逆引きロジックは不要になったため、常に空を返す
        return ""

    def _delete_mapping_row(self, key_var_to_delete):
        """指定されたキー変数を持つマッピング行を削除し、UIを再描画する"""
        # 削除対象のウィジェットを特定
        for i, (k_var, v_var, btn, key_entry, val_entry) in enumerate(self.mapping_widgets):
            if k_var == key_var_to_delete:
                # ウィジェットを破棄
                key_entry.destroy()
                val_entry.destroy()
                btn.destroy()
                # リストから削除
                self.mapping_widgets.pop(i)
                break

    def populate_data(self):
        for key, value in self.config_data.items():
            if key in self.widgets:
                info = self.widgets[key]
                if info["widget_type"] == "entry":
                    info["var"].set(str(value))
                elif info["widget_type"] == "checkbutton":
                    info["var"].set(bool(value))
                elif info["widget_type"] == "rgb":
                    for i in range(3):
                        info["vars"][i].set(str(value[i] if value and len(value) > i else 0))
        
        if "display_text_mapping" in self.config_data:
            for i, (k, v) in enumerate(self.config_data["display_text_mapping"].items()):
                self._add_mapping_row(k, v, row_index=i)

        # ウィンドウジオメトリのデータを読み込む
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_geometries = self.config_data.get("window_geometries", {})

        # 定義されたツールリストに基づいてUIを生成
        for i, tool_name in enumerate(self.target_tool_classes):
            # ヘッダーが0行目なので、設定行は1行目から開始
            # 1ツールあたり2行使うので、インデックスを2倍する
            default_geometry = "800x600+0+0" # 中央配置のデフォルト
            geometry_string = window_geometries.get(tool_name, default_geometry)
            self._add_window_geometry_row(i * 2 + 1, tool_name, geometry_string)
            widgets = self.window_geometry_widgets[tool_name]
            try:
                size, x_str, y_str = geometry_string.split('+')
                w_str, h_str = size.split('x')
                w, h, x, y = int(w_str), int(h_str), int(x_str), int(y_str)

                # ジオメトリからプリセットと補正値を逆算
                current_size_str = f"{w}x{h}"
                matched_preset = False
                is_size_custom = False
                for preset_name, preset_size_str in self.presets.items():
                    if preset_size_str == current_size_str:
                        widgets["preset"].set(preset_name)
                        widgets["width_offset"].set("0")
                        widgets["height_offset"].set("0")
                        matched_preset = True
                        break
                
                if not matched_preset:
                    # 一致するプリセットがない場合、SVGAを基準に補正値を計算
                    base_w, base_h = map(int, self.presets["SVGA 800x600"].split('x'))
                    widgets["preset"].set("SVGA 800x600")
                    widgets["width_offset"].set(str(w - base_w))
                    widgets["height_offset"].set(str(h - base_h))
                    is_size_custom = True

                # 絶対座標(x, y)に最も近い位置プリセットとその基準座標(base_x, base_y)を見つける
                positions = {
                    "中央": ((screen_width - w) // 2, (screen_height - h) // 2),
                    "右上": (screen_width - w - 10, 10),
                    "左上": (10, 10)
                }
                
                closest_pos_preset = "中央"
                min_dist = float('inf')

                for name, (base_x, base_y) in positions.items():
                    dist = (x - base_x)**2 + (y - base_y)**2
                    if dist < min_dist:
                        min_dist = dist
                        closest_pos_preset = name
                
                # 最も近いプリセットを基準とした補正値を計算して設定
                final_base_x, final_base_y = positions[closest_pos_preset]
                final_offset_x = x - final_base_x
                final_offset_y = y - final_base_y

                widgets["pos_preset"].set(closest_pos_preset)
                widgets["offset_x"].set(str(final_offset_x))
                widgets["offset_y"].set(str(final_offset_y))

                # 色を設定
                self.style.configure(f"{tool_name}.TCombobox", foreground="red" if is_size_custom else "black")

            except (ValueError, IndexError):
                # パース失敗時はデフォルト値のまま
                print(f"警告: ツール '{tool_name}' のジオメトリ文字列 '{geometry_string}' を解析できませんでした。")

    def save_and_close(self):
        new_config = self.config_data.copy()
        
        for key, label, widget_type, tab, options in self.config_definition:
            try:
                info = self.widgets[key]
                if widget_type == "entry":
                    target_type = options.get("type", str)
                    val_str = info["var"].get()
                    if target_type is bool:
                        val = val_str.lower() in ("true", "1", "yes")
                    elif target_type in (int, float, str):
                        val = target_type(val_str)
                    new_config[key] = val # valが未定義になる可能性はない
                elif widget_type == "checkbutton":
                    new_config[key] = info["var"].get()
                elif widget_type == "rgb":
                    new_config[key] = [self._parse_color_value(v.get()) for v in info["vars"]]

            except (ValueError, KeyError) as e:
                messagebox.showerror("入力エラー", f"設定 '{key}' の値が不正です。\n{e}")
                return

        # マッピングの保存
        mapping_dict = OrderedDict()
        for key_var, value_var, _, _, _ in self.mapping_widgets:
            mapping_dict[key_var.get()] = value_var.get()
        new_config["display_text_mapping"] = mapping_dict

        # ウィンドウジオメトリの保存
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 'window_geometries'キーがなければ作成
        if "window_geometries" not in new_config:
            new_config["window_geometries"] = OrderedDict()

        for tool_name, widgets in self.window_geometry_widgets.items():
            try:
                preset_name = widgets["preset"].get()
                pos_preset_name = widgets["pos_preset"].get()
                size_str = self.presets.get(preset_name)
                if not size_str:
                    raise ValueError(f"プリセット '{preset_name}' が見つかりません。")
                
                base_w, base_h = map(int, size_str.split('x'))
                w_offset = int(widgets["width_offset"].get() or 0)
                h_offset = int(widgets["height_offset"].get() or 0)
                w = base_w + w_offset
                h = base_h + h_offset
                offset_x = int(widgets["offset_x"].get())
                offset_y = int(widgets["offset_y"].get())

                # 位置プリセットに基づいて基準座標を決定し、補正値を加算
                if pos_preset_name == "中央":
                    base_x = (screen_width - w) // 2
                    base_y = (screen_height - h) // 2
                elif pos_preset_name == "右上":
                    base_x = screen_width - w - 10
                    base_y = 10
                elif pos_preset_name == "左上":
                    base_x = 10
                    base_y = 10
                x = base_x + offset_x
                y = base_y + offset_y

                new_geometry = f"{w}x{h}+{x}+{y}"
                new_config["window_geometries"][tool_name] = new_geometry
            except (ValueError, KeyError) as e:
                messagebox.showerror("入力エラー", f"ツール '{tool_name}' の設定値が不正です。\n{e}")
                return


        # バックアップと保存
        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, self.config_path + ".bak")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("成功", "設定を保存しました。")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定ファイルの保存に失敗しました。\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigEditorApp(root)
    root.mainloop()
