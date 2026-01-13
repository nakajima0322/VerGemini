# G_Shared_CountWindow.py
import tkinter as tk
from tkinter import ttk
import time

class CountDisplayWindow:
    """
    スキャナのカウント情報をリアルタイムで表示するための別ウィンドウ。
    デバッグおよびモニタリングを目的とする。
    """
    def __init__(self, parent_scanner):
        self.parent_scanner = parent_scanner
        self.root = tk.Toplevel()
        self.root.title("カウントモニター (工程登録スキャン)")
        # ウィンドウが閉じられたときの処理
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # スタイル設定
        style = ttk.Style(self.root)
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("Count.TLabel", font=("Helvetica", 14, "bold"), foreground="blue")

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # 表示するカウント項目の定義
        self.count_vars = {
            "Scans (総スキャン数)": tk.StringVar(value="0"),
            "Success (成功数)": tk.StringVar(value="0"),
            "Failure (失敗数)": tk.StringVar(value="0"),
            "Duplicates (重複数)": tk.StringVar(value="0"),
            "Time left (残り時間)": tk.StringVar(value="0"),
        }

        # UIの作成
        for i, (label_text, var) in enumerate(self.count_vars.items()):
            ttk.Label(main_frame, text=f"{label_text}:", style="TLabel").grid(row=i, column=0, sticky="w", pady=4)
            ttk.Label(main_frame, textvariable=var, style="Count.TLabel").grid(row=i, column=1, sticky="w", padx=10)

        # ウィンドウ位置をスキャンウィンドウの右隣に設定
        self.root.update_idletasks()
        try:
            # 画面サイズを動的に取得して位置を計算
            screen_width = self.root.winfo_screenwidth()
            window_width = self.root.winfo_reqwidth()
            x_pos = screen_width - window_width - 10 # 画面の右端から10px内側に配置
            y_pos = 10 # 画面の上端から10px下に配置
            self.root.geometry(f"+{x_pos}+{y_pos}")
        except Exception:
            self.root.geometry("+800+100") # 失敗時のフォールバック

        self.update_counts()

    def update_counts(self):
        """親スキャナから最新のカウント情報を取得してUIを更新する"""
        if not self.root.winfo_exists():
            return

        # 親スキャナの属性から値を取得
        self.count_vars["Scans (総スキャン数)"].set(str(getattr(self.parent_scanner, 'scan_count', 0)))
        self.count_vars["Success (成功数)"].set(str(getattr(self.parent_scanner, 'success_count', 0)))
        self.count_vars["Failure (失敗数)"].set(str(getattr(self.parent_scanner, 'failure_count', 0)))
        self.count_vars["Duplicates (重複数)"].set(str(getattr(self.parent_scanner, 'duplicate_count', 0)))
        
        # 残り時間の計算をより安全な方法に変更
        idle_timeout = getattr(self.parent_scanner, 'idle_timeout', 0)
        last_scan_time = getattr(self.parent_scanner, 'last_scan_time', time.time())
        remaining_time = max(0, idle_timeout - (time.time() - last_scan_time))

        self.count_vars["Time left (残り時間)"].set(f"{int(remaining_time)}s")

        # 500ms後に再度このメソッドを呼び出す
        self.root.after(500, self.update_counts)

    def close(self):
        """ウィンドウを閉じる"""
        if self.root.winfo_exists():
            self.root.destroy()