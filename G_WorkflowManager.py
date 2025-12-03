# G_WorkflowManager.py (新規作成)
import tkinter as tk
from tkinter import ttk
import os
import csv
from G_config import Config


class WorkflowManager:
    def __init__(self, root):
        self.root = root
        self.root.title("ワークフロー管理ツール")
        # ウィンドウサイズを少し大きくする
        self.root.geometry("800x600")

        self.config = Config("config.json")

        # --- 設定値の読み込み ---
        self.data_dir = self.config.get("data_dir", "data")
        self.source_data_dir = self.config.get("source_data_dir", "Source")

        # --- メインフレーム ---
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)

        # --- ① 工事番号 指定エリア ---
        input_frame = ttk.LabelFrame(main_frame, text="1. 工事番号の指定", padding="10")
        input_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="工事番号:").grid(row=0, column=0, padx=5, pady=5)
        self.cn_entry = ttk.Entry(input_frame, width=20)
        self.cn_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # 前回スキャナで使った工事番号をデフォルト表示
        self.cn_entry.insert(0, self.config.get("last_construction_number_scanner", ""))

        check_button = ttk.Button(
            input_frame, text="状態確認", command=self.check_status
        )
        check_button.grid(row=0, column=2, padx=5, pady=5)
        self.cn_entry.bind("<Return>", lambda e: self.check_status())

        # --- ② 進捗詳細表示エリア (Notebook) ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=10)

        # --- 調達状況タブ ---
        self.procurement_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.procurement_tab, text="① 調達状況 (未納品リスト)")
        self.procurement_tab.columnconfigure(0, weight=1)
        self.procurement_tab.rowconfigure(1, weight=1)

        proc_summary_frame = ttk.Frame(self.procurement_tab)
        proc_summary_frame.grid(row=0, column=0, sticky="ew", pady=5)
        self.procurement_summary_var = tk.StringVar(
            value="工事番号を入力して「状態確認」を押してください。"
        )
        ttk.Label(proc_summary_frame, textvariable=self.procurement_summary_var).pack(
            anchor="w"
        )

        proc_cols = ("図番", "品名", "仕入先", "納期", "発注数")
        self.procurement_tree = ttk.Treeview(
            self.procurement_tab, columns=proc_cols, show="headings"
        )
        for col in proc_cols:
            self.procurement_tree.heading(col, text=col)
            self.procurement_tree.column(col, width=120)
        self.procurement_tree.grid(row=1, column=0, sticky="nsew")
        proc_scroll = ttk.Scrollbar(
            self.procurement_tab, orient="vertical", command=self.procurement_tree.yview
        )
        self.procurement_tree.configure(yscrollcommand=proc_scroll.set)
        proc_scroll.grid(row=1, column=1, sticky="ns")

        # --- 工程仕掛状況タブ ---
        self.wip_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.wip_tab, text="② 工程仕掛状況")
        self.wip_tab.columnconfigure(0, weight=1)
        self.wip_tab.rowconfigure(1, weight=1)

        wip_summary_frame = ttk.Frame(self.wip_tab)
        wip_summary_frame.grid(row=0, column=0, sticky="ew", pady=5)
        self.wip_summary_var = tk.StringVar(
            value="工事番号を入力して「状態確認」を押してください。"
        )
        ttk.Label(wip_summary_frame, textvariable=self.wip_summary_var).pack(anchor="w")

        wip_cols = ("図番", "品名", "工程名", "納品業者", "作業セッションID")
        self.wip_tree = ttk.Treeview(self.wip_tab, columns=wip_cols, show="headings")
        for col in wip_cols:
            self.wip_tree.heading(col, text=col)
            self.wip_tree.column(col, width=120)
        self.wip_tree.grid(row=1, column=0, sticky="nsew")
        wip_scroll = ttk.Scrollbar(
            self.wip_tab, orient="vertical", command=self.wip_tree.yview
        )
        self.wip_tree.configure(yscrollcommand=wip_scroll.set)
        wip_scroll.grid(row=1, column=1, sticky="ns")

        # --- リサイズ設定 ---
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # --- 初期状態の確認 ---
        self.root.after(100, self.check_status)

        # --- 終了処理 ---
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind("<Escape>", lambda e: self._on_closing())
        self._restore_geometry()

    def _normalize_id(self, id_str):
        return id_str.lstrip("0") if id_str else ""

    def check_status(self):
        """指定された工事番号の各ファイルの存在を確認し、UIを更新する"""
        # Clear previous results
        self.procurement_tree.delete(*self.procurement_tree.get_children())
        self.wip_tree.delete(*self.wip_tree.get_children())
        self.procurement_summary_var.set("確認中...")
        self.wip_summary_var.set("確認中...")
        self.root.update_idletasks()

        construction_no = self.cn_entry.get().strip()
        if not construction_no:
            self.procurement_summary_var.set("工事番号を入力してください。")
            self.wip_summary_var.set("工事番号を入力してください。")
            return

        # --- ① 調達状況の確認 ---
        self._check_procurement_status(construction_no)

        # --- ② 工程仕掛状況の確認 ---
        self._check_wip_status(construction_no)

    def _read_csv_to_dict(self, filepath, key_column):
        """CSVを読み込み、指定列をキーとする辞書を返す"""
        data_dict = {}
        if not os.path.exists(filepath):
            return data_dict, f"ファイルが見つかりません: {os.path.basename(filepath)}"
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._normalize_id(row.get(key_column, ""))
                    if key:
                        if key not in data_dict:
                            data_dict[key] = []
                        data_dict[key].append(row)
            return data_dict, None
        except Exception as e:
            return {}, f"ファイル読込エラー: {e}"

    def _check_procurement_status(self, cn):
        master_file = os.path.join(self.source_data_dir, f"{cn}s.csv")
        scan_file = os.path.join(self.data_dir, f"{cn}.csv")

        order_col = self.config.get("source_csv_order_no_column", "発注伝票№")
        drawing_col = self.config.get("source_csv_drawing_no_column", "図番")
        item_name_col = self.config.get("source_csv_item_name_column", "品名")
        supplier_col = self.config.get("source_csv_supplier_column", "仕入先")
        delivery_date_col = self.config.get("source_csv_delivery_date_column", "納期")
        order_count_col = self.config.get(
            "source_csv_order_count_column", "発注数"
        )  # 仮。発注数カラムが必要

        master_data, err = self._read_csv_to_dict(master_file, order_col)
        if err:
            self.procurement_summary_var.set(f"エラー: {err}")
            return

        scan_data, err = self._read_csv_to_dict(scan_file, "barcode_info")
        if err:
            self.procurement_summary_var.set(
                f"警告: {err} (未納品リストは表示されます)"
            )

        total_parts = len(master_data)
        delivered_count = 0
        undelivered_items = []

        for order_no, items in master_data.items():
            if order_no in scan_data:
                delivered_count += 1
            else:
                for item in items:
                    undelivered_items.append(item)

        for item in undelivered_items:
            self.procurement_tree.insert(
                "",
                "end",
                values=(
                    item.get(drawing_col, ""),
                    item.get(item_name_col, ""),
                    item.get(supplier_col, ""),
                    item.get(delivery_date_col, ""),
                    item.get(order_count_col, "N/A"),
                ),
            )

        summary = f"総部品点数: {total_parts} | 納品済み: {delivered_count} | 未納品: {len(undelivered_items)}"
        self.procurement_summary_var.set(summary)

    def _check_wip_status(self, cn):
        processed_file = os.path.join(self.data_dir, f"{cn}_processed.csv")
        scan_file = os.path.join(self.data_dir, f"{cn}.csv")
        master_file = os.path.join(self.source_data_dir, f"{cn}s.csv")

        order_col = self.config.get("source_csv_order_no_column", "発注伝票№")
        drawing_col = self.config.get("source_csv_drawing_no_column", "図番")
        item_name_col = self.config.get("source_csv_item_name_column", "品名")

        processed_data, err = self._read_csv_to_dict(processed_file, "barcode_info")
        if err:
            self.wip_summary_var.set(f"エラー: {err}")
            return

        scan_data, _ = self._read_csv_to_dict(scan_file, "barcode_info")
        master_data, _ = self._read_csv_to_dict(master_file, order_col)

        total_processed = len(processed_data)
        wip_count = 0

        for barcode, items in processed_data.items():
            if barcode not in scan_data:
                wip_count += 1
                master_info = master_data.get(barcode, [{}])[0]
                for item in items:
                    self.wip_tree.insert(
                        "",
                        "end",
                        values=(
                            master_info.get(drawing_col, "不明"),
                            master_info.get(item_name_col, "不明"),
                            item.get("process_name", ""),
                            item.get("supplier_name", ""),
                            item.get("work_session_id", ""),
                        ),
                    )

        summary = f"工程投入点数: {total_processed} | 工程完了点数: {total_processed - wip_count} | 仕掛中: {wip_count}"
        self.wip_summary_var.set(summary)

    def _on_closing(self):
        """ウィンドウ終了時の処理"""
        self._save_geometry()
        self.config.save_config()
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


if __name__ == "__main__":
    root = tk.Tk()
    app = WorkflowManager(root)
    root.mainloop()
