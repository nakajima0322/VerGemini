# G_Launcher.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KHTツールランチャー")
        self.root.geometry("400x350") # 少し大きめに

        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- バーコードスキャン ---
        scan_button = ttk.Button(main_frame, text="バーコードスキャン実行", command=self._run_scan_bcd_main, width=30)
        scan_button.pack(pady=10)

        # --- 図面番号照合 ---
        location_viewer_button = ttk.Button(main_frame, text="保管場所照合ツール起動", command=self._run_location_viewer, width=30)
        location_viewer_button.pack(pady=10)

        # --- 部品情報表示 ---
        part_info_frame = ttk.LabelFrame(main_frame, text="部品情報表示ツール")
        part_info_frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(part_info_frame, text="工事番号 (任意):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.part_info_cn_entry = ttk.Entry(part_info_frame, width=15)
        self.part_info_cn_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Label(part_info_frame, text="バーコード (任意):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.part_info_bc_entry = ttk.Entry(part_info_frame, width=20)
        self.part_info_bc_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        part_info_button = ttk.Button(part_info_frame, text="部品情報表示ツール起動", command=self._run_part_info_viewer)
        part_info_button.grid(row=2, column=0, columnspan=2, pady=10)

        part_info_frame.columnconfigure(1, weight=1)

        # --- 結合CSV作成 ---
        combine_csv_button = ttk.Button(main_frame, text="結合CSV作成", command=self._run_create_combined_csv, width=30)
        combine_csv_button.pack(pady=10)

        # --- 終了ボタン ---
        exit_button = ttk.Button(main_frame, text="終了", command=self._on_closing, width=30)
        exit_button.pack(pady=15)

        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _check_file_exists(self, script_name):
        if not os.path.exists(script_name):
            messagebox.showerror("ファイルエラー", f"{script_name} が見つかりません。\nカレントディレクトリを確認してください。", parent=self.root)
            return False
        return True

    def _run_script(self, script_name, args=None):
        if not self._check_file_exists(script_name):
            return

        command = [sys.executable, script_name]
        if args:
            command.extend(args)
        
        try:
            print(f"実行中: {' '.join(command)}")
            subprocess.Popen(command)
        except Exception as e:
            messagebox.showerror("実行エラー", f"{script_name} の起動中にエラーが発生しました:\n{e}", parent=self.root)
            print(f"エラー: {script_name} 起動失敗 - {e}")

    def _run_scan_bcd_main(self):
        self._run_script("G_ScanBCD_main.py")

    def _run_location_viewer(self): # メソッド名も変更
        self._run_script("G_DrawingNumberViewer.py") # 起動するファイル名は G_DrawingNumberViewer.py のまま

    def _run_part_info_viewer(self):
        cn = self.part_info_cn_entry.get().strip()
        bc = self.part_info_bc_entry.get().strip()
        args = []
        if cn and bc:
            args = [cn, bc]
        elif cn: # 工事番号のみ指定の場合 (バーコードなしで起動)
            # G_PartInfoViewer.py は現状、引数2つを期待するか、引数なしを期待する
            # ここでは引数なしで起動する (もし工事番号のみ渡したい場合は G_PartInfoViewer.py の修正が必要)
            print("部品情報表示ツール: 工事番号のみの指定は現在サポートされていません。引数なしで起動します。")
            pass # args は空のまま
        elif bc: # バーコードのみ指定の場合
            print("部品情報表示ツール: バーコードのみの指定は現在サポートされていません。引数なしで起動します。")
            pass # args は空のまま

        self._run_script("G_PartInfoViewer.py", args if args else None)

    def _run_create_combined_csv(self):
        self._run_script("create_combined_csv.py")

    def _on_closing(self):
        print("KHTツールランチャーを終了します。")
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = LauncherApp(root)
    
    # ウィンドウを中央に表示
    root.update_idletasks()
    window_width = root.winfo_width()
    window_height = root.winfo_height()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f'{window_width}x{window_height}+{x}+{y}')
    
    root.mainloop()