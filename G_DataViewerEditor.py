# G_DataViewerEditor.py
import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
import shutil
from G_config import Config

class DataViewerEditor:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("データビューア/エディタ")
        self.data_dir = self.config.get("data_dir", "data")
        self.current_filepath = None
        self.header = []

        # --- UI構築 ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # --- ファイル選択フレーム ---
        file_frame = ttk.LabelFrame(main_frame, text="1. 編集対象の選択", padding="10")
        file_frame.grid(row=0, column=0, sticky="ew", pady=5)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="工事番号:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.cn_entry = ttk.Entry(file_frame, width=15)
        self.cn_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.cn_entry.insert(0, self.config.get("last_construction_number", ""))

        self.file_type_var = tk.StringVar(value="processed")
        ttk.Radiobutton(file_frame, text="工程データ (_processed.csv)", variable=self.file_type_var, value="processed").grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Radiobutton(file_frame, text="場所データ (.csv)", variable=self.file_type_var, value="location").grid(row=2, column=0, columnspan=2, sticky="w", padx=5)

        load_button = ttk.Button(file_frame, text="読み込み", command=self.load_data)
        load_button.grid(row=1, column=2, rowspan=2, padx=10)

        # --- データ表示フレーム ---
        data_frame = ttk.LabelFrame(main_frame, text="2. データ内容", padding="10")
        data_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(data_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        vsb = ttk.Scrollbar(data_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(data_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.bind("<Double-1>", self.on_double_click)

        # --- 操作ボタンフレーム ---
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, sticky="ew", pady=10)

        self.save_button = ttk.Button(action_frame, text="保存", command=self.save_data, state=tk.DISABLED)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        self.delete_button = ttk.Button(action_frame, text="選択行を削除", command=self.delete_selected_row, state=tk.DISABLED)
        self.delete_button.pack(side=tk.RIGHT)

    def load_data(self):
        cn = self.cn_entry.get().strip()
        if not cn:
            messagebox.showerror("エラー", "工事番号を入力してください。")
            return

        file_type = self.file_type_var.get()
        filename = f"{cn}_processed.csv" if file_type == "processed" else f"{cn}.csv"
        self.current_filepath = os.path.join(self.data_dir, filename)

        if not os.path.exists(self.current_filepath):
            messagebox.showerror("エラー", f"ファイルが見つかりません:\n{self.current_filepath}")
            return

        self.tree.delete(*self.tree.get_children())

        try:
            with open(self.current_filepath, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                self.header = next(reader)
                self.tree["columns"] = self.header
                for col in self.header:
                    self.tree.heading(col, text=col)
                    self.tree.column(col, width=120)
                
                for i, row in enumerate(reader):
                    self.tree.insert("", "end", iid=i, values=row)
            
            self.save_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)

        except Exception as e:
            messagebox.showerror("読み込みエラー", f"ファイルの読み込み中にエラーが発生しました:\n{e}")

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        column = self.tree.identify_column(event.x)
        col_index = int(column.replace('#', '')) - 1

        x, y, width, height = self.tree.bbox(item_id, column)

        entry_var = tk.StringVar()
        entry = ttk.Entry(self.tree, textvariable=entry_var)
        entry.place(x=x, y=y, width=width, height=height)

        current_values = self.tree.item(item_id, "values")
        entry_var.set(current_values[col_index])
        entry.focus_set()

        def on_focus_out(event):
            new_values = list(self.tree.item(item_id, "values"))
            new_values[col_index] = entry_var.get()
            self.tree.item(item_id, values=new_values)
            entry.destroy()

        entry.bind("<FocusOut>", on_focus_out)
        entry.bind("<Return>", on_focus_out)

    def delete_selected_row(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "削除する行を選択してください。")
            return
        
        if messagebox.askyesno("確認", f"{len(selected_items)}行を削除しますか？"):
            for item in selected_items:
                self.tree.delete(item)

    def save_data(self):
        if not self.current_filepath:
            return

        if not messagebox.askyesno("確認", f"変更をファイルに保存しますか？\n{self.current_filepath}\n\n(元のファイルは .bak としてバックアップされます)"):
            return

        try:
            # バックアップ作成
            shutil.copy2(self.current_filepath, self.current_filepath + ".bak")

            with open(self.current_filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.header)
                for item_id in self.tree.get_children():
                    row = self.tree.item(item_id, "values")
                    writer.writerow(row)
            
            messagebox.showinfo("成功", "ファイルの保存が完了しました。")

        except Exception as e:
            messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました:\n{e}")

if __name__ == "__main__":
    try:
        config = Config("config.json")
        root = tk.Tk()
        app = DataViewerEditor(root, config)
        
        # ウィンドウを中央に表示
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (root.winfo_width() // 2)
        y = (screen_height // 2) - (root.winfo_height() // 2)
        root.geometry(f'+{x}+{y}')

        root.mainloop()
    except Exception as e:
        messagebox.showerror("起動エラー", f"データビューア/エディタの起動に失敗しました:\n{e}")