# G_Launcher.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tool Launcher")
        # self.root.geometry("400x400") # 固定サイズ指定を削除し、自動調整に任せる

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        btn_width = 35
        btn_pady = 5

        # --- メインワークフロー カテゴリ ---
        workflow_frame = ttk.LabelFrame(main_frame, text="メインワークフロー", padding="10")
        workflow_frame.pack(fill=tk.X, padx=10, pady=5)

        scan_button = ttk.Button(workflow_frame, text="バーコードスキャン実行", command=self._run_scan_bcd_main, width=btn_width)
        scan_button.pack(pady=btn_pady)

        location_viewer_button = ttk.Button(workflow_frame, text="保管場所照合ツール起動", command=self._run_location_viewer, width=btn_width)
        location_viewer_button.pack(pady=btn_pady)

        part_info_button = ttk.Button(workflow_frame, text="部品情報表示ツール起動", command=self._run_part_info_viewer, width=btn_width)
        part_info_button.pack(pady=btn_pady)

        combine_csv_button = ttk.Button(workflow_frame, text="結合CSV作成", command=self._run_create_combined_csv, width=btn_width)
        combine_csv_button.pack(pady=btn_pady)

        # --- 管理・設定 カテゴリ ---
        admin_frame = ttk.LabelFrame(main_frame, text="管理・設定", padding="10")
        admin_frame.pack(fill=tk.X, padx=10, pady=5)

        workflow_button = ttk.Button(admin_frame, text="ワークフロー管理ツール起動", command=self._run_workflow_manager, width=btn_width)
        workflow_button.pack(pady=btn_pady)
        config_editor_button = ttk.Button(admin_frame, text="設定編集", command=self._run_config_editor, width=btn_width)
        config_editor_button.pack(pady=btn_pady)

        # --- 終了ボタン ---
        exit_button = ttk.Button(main_frame, text="終了", command=self._on_closing, width=btn_width)
        exit_button.pack(side="bottom", pady=10)

        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind('<Escape>', lambda e: self._on_closing())

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
        self._run_script("G_PartInfoViewer.py", None)

    def _run_create_combined_csv(self):
        self._run_script("create_combined_csv.py")

    def _run_config_editor(self):
        self._run_script("G_ConfigEditor.py")

    def _run_workflow_manager(self):
        self._run_script("G_WorkflowManager.py")

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