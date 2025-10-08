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
        self.mapping_widgets = [] # マッピング用ウィジェットを保持

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
        self.tab_state = ttk.Frame(self.notebook, padding="10")

        self.notebook.add(self.tab_basic, text="基本設定")
        self.notebook.add(self.tab_folders, text="フォルダ設定")
        self.notebook.add(self.tab_csv, text="CSV列名設定")
        self.notebook.add(self.tab_display, text="動作・表示設定")
        self.notebook.add(self.tab_mapping, text="表示名マッピング") # タブ追加
        self.notebook.add(self.tab_state, text="状態(表示のみ)")

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=5)
        save_button = ttk.Button(button_frame, text="保存して閉じる", command=self.save_and_close)
        save_button.pack(side="right", padx=5)
        cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.root.destroy)
        cancel_button.pack(side="right")

        self.load_config()
        self.create_widgets()
        self.populate_data()
        
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f, object_pairs_hook=OrderedDict)
        except FileNotFoundError:
            messagebox.showerror("エラー", f"{self.config_path} が見つかりません。")
            self.root.destroy()
        except json.JSONDecodeError:
            messagebox.showerror("エラー", f"{self.config_path} は不正なJSON形式です。")
            self.root.destroy()

    def create_widgets(self):
        # --- 基本設定 ---
        self._add_entry(self.tab_basic, "camera_index", "カメラ番号")
        self._add_entry(self.tab_basic, "camera_width", "カメラ解像度 (幅)")
        self._add_entry(self.tab_basic, "camera_height", "カメラ解像度 (高さ)")
        self._add_entry(self.tab_basic, "target_fps", "ターゲットFPS")
        self._add_entry(self.tab_basic, "barcode_type", "バーコードタイプ")
        self._add_entry(self.tab_basic, "expected_length", "バーコード期待長")

        # --- フォルダ設定 ---
        self._add_entry(self.tab_folders, "data_dir", "データフォルダ名")
        self._add_entry(self.tab_folders, "log_dir", "ログフォルダ名")
        self._add_entry(self.tab_folders, "source_data_dir", "発注伝票フォルダ名")
        self._add_entry(self.tab_folders, "scan_log", "スキャンログファイル名")

        # --- CSV列名設定 ---
        csv_frame = ttk.LabelFrame(self.tab_csv, text="発注伝票CSVの列名", padding="10")
        csv_frame.pack(expand=True, fill="both")
        self._add_entry(csv_frame, "source_csv_order_no_column", "発注伝票№")
        self._add_entry(csv_frame, "source_csv_drawing_no_column", "図番")
        self._add_entry(csv_frame, "source_csv_parts_no_column", "部品№")
        self._add_entry(csv_frame, "source_csv_item_name_column", "品名")
        self._add_entry(csv_frame, "source_csv_delivery_date_column", "納期")
        self._add_entry(csv_frame, "source_csv_delivery_count_column", "納入数")
        self._add_entry(csv_frame, "source_csv_supplier_column", "仕入先")
        self._add_entry(csv_frame, "source_csv_arrangement_status_column", "手配")

        # --- 動作・表示設定 ---
        self._add_checkbutton(self.tab_display, "auto_stop", "自動停止を有効にする")
        self._add_checkbutton(self.tab_display, "overlay_enabled", "オーバーレイ表示を有効にする")
        self._add_entry(self.tab_display, "overlay_alpha", "オーバーレイ透明度 (0.0-1.0)")
        self._add_rgb_entry(self.tab_display, "overlay_color", "オーバーレイ色 (R, G, B)")
        self._add_entry(self.tab_display, "display_time", "結果表示時間 (ms)")
        self._add_entry(self.tab_display, "idle_timeout", "アイドルタイムアウト (秒)")
        self._add_entry(self.tab_display, "default_construction_number", "デフォルト工事番号")
        self._add_entry(self.tab_display, "default_location", "デフォルト保管場所")

        # --- 表示名マッピングタブ ---
        self._create_mapping_tab()

        # --- 状態(表示のみ) ---
        state_frame = ttk.LabelFrame(self.tab_state, text="前回終了時の状態 (編集不可)", padding="10")
        state_frame.pack(expand=True, fill="both")
        for key in self.config_data:
            if key.startswith("last_"):
                self._add_entry(state_frame, key, key, readonly=True)

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
        self.widgets[key] = {"type": "entry", "var": var}

    def _add_checkbutton(self, parent, key, label_text):
        frame = self._add_widget(parent, label_text)
        var = tk.BooleanVar()
        chk = ttk.Checkbutton(frame, variable=var)
        chk.pack(side='left')
        self.widgets[key] = {"type": "checkbutton", "var": var}

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
            "type": "rgb", 
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
        if not widget_info or widget_info["type"] != "rgb":
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
        header_frame.pack(fill='x')
        ttk.Label(header_frame, text="元々の名前", width=30, font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=5)
        ttk.Label(header_frame, text="表示名", font=("TkDefaultFont", 9, "bold")).pack(side="left", padx=5)

        self.mapping_canvas = tk.Canvas(self.tab_mapping)
        scrollbar = ttk.Scrollbar(self.tab_mapping, orient="vertical", command=self.mapping_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.mapping_canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.mapping_canvas.configure(scrollregion=self.mapping_canvas.bbox("all")))
        self.mapping_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.mapping_canvas.configure(yscrollcommand=scrollbar.set)

        self.mapping_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        add_button = ttk.Button(self.tab_mapping, text="マッピングを追加", command=self._add_mapping_row)
        add_button.pack(side="bottom", pady=5)

    def _add_mapping_row(self, key_text="", value_text=""):
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill='x', pady=2)

        key_var = tk.StringVar(value=key_text)
        value_var = tk.StringVar(value=value_text)

        key_entry = ttk.Entry(row_frame, textvariable=key_var, width=30)
        key_entry.pack(side="left", padx=5)
        value_entry = ttk.Entry(row_frame, textvariable=value_var, width=30)
        value_entry.pack(side="left", padx=5)

        delete_button = ttk.Button(row_frame, text="削除", command=lambda: self._delete_mapping_row(row_frame))
        delete_button.pack(side="left", padx=5)
        
        self.mapping_widgets.append((row_frame, key_var, value_var))

    def _delete_mapping_row(self, row_frame):
        for i, (frame, _, _) in enumerate(self.mapping_widgets):
            if frame == row_frame:
                self.mapping_widgets.pop(i)
                break
        row_frame.destroy()

    def populate_data(self):
        for key, value in self.config_data.items():
            if key in self.widgets:
                info = self.widgets[key]
                if info["type"] == "entry":
                    info["var"].set(str(value))
                elif info["type"] == "checkbutton":
                    info["var"].set(bool(value))
                elif info["type"] == "rgb":
                    for i in range(3):
                        info["vars"][i].set(str(value[i]))
        
        if "display_text_mapping" in self.config_data:
            for k, v in self.config_data["display_text_mapping"].items():
                self._add_mapping_row(k, v)

    def save_and_close(self):
        new_config = self.config_data.copy()
        for key, info in self.widgets.items():
            if key not in new_config:
                continue
            try:
                if info["type"] == "entry":
                    original_value = new_config[key]
                    if isinstance(original_value, bool):
                        val = info["var"].get().lower() in ("true", "1", "yes")
                    elif isinstance(original_value, int):
                        val = int(info["var"].get())
                    elif isinstance(original_value, float):
                        val = float(info["var"].get())
                    else:
                        val = info["var"].get()
                    new_config[key] = val
                elif info["type"] == "checkbutton":
                    new_config[key] = info["var"].get()
                elif info["type"] == "rgb":
                    new_config[key] = [self._parse_color_value(v.get()) for v in info["vars"]]
            except (ValueError, json.JSONDecodeError) as e:
                messagebox.showerror("入力エラー", f"設定 '{key}' の値が不正です。\n{e}")
                return

        # マッピングの保存
        mapping_dict = OrderedDict()
        for _, key_var, value_var in self.mapping_widgets:
            mapping_dict[key_var.get()] = value_var.get()
        new_config["display_text_mapping"] = mapping_dict

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
