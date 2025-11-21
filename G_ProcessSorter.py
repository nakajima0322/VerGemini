# G_ProcessSorter.py
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import subprocess
from G_config import Config

class ProcessSelector:
    """
    工事番号と追加工程を選択するUIを提供するクラス。
    G_ScanBCD_Location.py を参考に作成。
    """
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("工程選択")

        self.selected_process = None
        self.supplier_name = ""
        self.construction_number = self.config.get("last_construction_number", "")
        self.process_definitions = self.config.get("process_definitions", ["工程未定義"])

        self._build_ui()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # 工事番号
        cn_frame = ttk.Frame(main_frame)
        cn_frame.pack(pady=5, fill=tk.X)
        ttk.Label(cn_frame, text="工事番号:").pack(side=tk.LEFT, padx=5)
        self.cn_entry = ttk.Entry(cn_frame, width=20)
        self.cn_entry.insert(0, self.construction_number)
        self.cn_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # 納品業者入力
        supplier_frame = ttk.Frame(main_frame)
        supplier_frame.pack(pady=5, fill=tk.X)
        ttk.Label(supplier_frame, text="納品業者:").pack(side=tk.LEFT, padx=5)
        self.supplier_entry = ttk.Entry(supplier_frame, width=20)
        self.supplier_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # 工程選択
        process_frame = ttk.LabelFrame(main_frame, text="追加工程を選択してください", padding="10")
        process_frame.pack(pady=5, expand=True, fill=tk.BOTH)

        for process_name in self.process_definitions:
            btn = ttk.Button(process_frame, text=process_name, command=lambda p=process_name: self._on_select(p))
            btn.pack(pady=3, fill=tk.X)

    def _on_select(self, process_name):
        cn = self.cn_entry.get().strip()
        if not cn:
            messagebox.showwarning("入力エラー", "工事番号を入力してください。", parent=self.root)
            return

        supplier = self.supplier_entry.get().strip()
        if not supplier:
            messagebox.showwarning("入力エラー", "納品業者を入力してください。", parent=self.root)
            return
        
        self.selected_process = process_name
        self.construction_number = cn
        self.supplier_name = supplier
        self.config.set("last_construction_number", cn) # 次回起動時のために保存
        self.root.destroy()

    def get_selection(self):
        self.root.mainloop()
        # 納品業者も返すように変更
        return self.selected_process, self.construction_number, self.supplier_name

def main():
    """
    メイン処理。工程を選択させ、その情報を引数としてスキャナを起動する。
    G_ScanBCD_main.py を参考に作成。
    """
    try:
        config = Config("config.json")
    except Exception as e:
        messagebox.showerror("設定エラー", f"config.jsonの読み込みに失敗しました。\n{e}")
        return

    # 1. 工程選択UIの表示
    selector_root = tk.Tk()
    selector = ProcessSelector(selector_root, config)
    process, construction_no, supplier_name = selector.get_selection()

    if not all([process, construction_no, supplier_name]):
        print("工程、工事番号、納品業者のいずれかが選択されなかったため、処理を中断します。")
        return

    print(f"選択された工程: {process}, 工事番号: {construction_no}, 納品業者: {supplier_name}")

    # 2. 新しい工程スキャナ(G_ProcessScanner.py)を起動
    try:
        subprocess.Popen([sys.executable, "G_ProcessScanner.py", construction_no, process, supplier_name])
    except Exception as e:
        messagebox.showerror("起動エラー", f"G_ProcessScanner.py の起動に失敗しました:\n{e}")


if __name__ == "__main__":
    main()