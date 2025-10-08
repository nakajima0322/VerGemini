# G_WorkflowManager.py (新規作成)
import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import sys
from G_config import Config

class WorkflowManager:
	def __init__(self, root):
		self.root = root
		self.root.title("ワークフロー管理ツール")
		self.config = Config("config.json")

		# --- 設定値の読み込み ---
		self.data_dir = self.config.get("data_dir", "data")
		self.source_data_dir = self.config.get("source_data_dir", "Source")

		# --- メインフレーム ---
		main_frame = ttk.Frame(root, padding="20")
		main_frame.pack(expand=True, fill=tk.BOTH)
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

		check_button = ttk.Button(input_frame, text="状態確認", command=self.check_status)
		check_button.grid(row=0, column=2, padx=5, pady=5)
		self.cn_entry.bind("<Return>", lambda e: self.check_status())

		# --- ② 進捗ステータス 表示エリア ---
		status_frame = ttk.LabelFrame(main_frame, text="2. 進捗ステータス", padding="10")
		status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
		status_frame.columnconfigure(1, weight=1)

		self.scan_data_status = tk.StringVar(value="？")
		self.master_data_status = tk.StringVar(value="？")
		self.result_data_status = tk.StringVar(value="？")

		self._create_status_row(status_frame, 0, "スキャンデータ (.csv)", self.scan_data_status)
		self._create_status_row(status_frame, 1, "マスターデータ (s.csv)", self.master_data_status)
		self._create_status_row(status_frame, 2, "最終レポート (result.csv)", self.result_data_status)

		# --- ③ ワークフロー実行エリア ---
		action_frame = ttk.LabelFrame(main_frame, text="3. ワークフロー実行", padding="10")
		action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
		action_frame.columnconfigure(0, weight=1)
		action_frame.columnconfigure(1, weight=1)

		scan_button = ttk.Button(action_frame, text="スキャン開始", command=self._run_scan)
		scan_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

		combine_button = ttk.Button(action_frame, text="結合レポート作成", command=self._run_combine)
		combine_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

		# --- 初期状態の確認 ---
		self.root.after(100, self.check_status)

		# --- 終了処理 ---
		self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
		self.root.bind('<Escape>', lambda e: self._on_closing())
		self._restore_geometry()

	def _create_status_row(self, parent, row, label_text, var):
		"""ステータス表示の1行を作成するヘルパーメソッド"""
		label = ttk.Label(parent, text=label_text)
		label.grid(row=row, column=0, sticky="w", padx=5, pady=2)
		
		status_label = ttk.Label(parent, textvariable=var, font=("", 10, "bold"))
		status_label.grid(row=row, column=1, sticky="w", padx=5, pady=2)

	def check_status(self):
		"""指定された工事番号の各ファイルの存在を確認し、UIを更新する"""
		construction_no = self.cn_entry.get().strip()
		if not construction_no:
			self.scan_data_status.set("---")
			self.master_data_status.set("---")
			self.result_data_status.set("---")
			return

		# 1. スキャンデータ
		scan_file = os.path.join(self.data_dir, f"{construction_no}.csv")
		if os.path.exists(scan_file):
			self.scan_data_status.set("✅ 存在します")
		else:
			self.scan_data_status.set("❌ 存在しません")

		# 2. マスターデータ
		master_file = os.path.join(self.source_data_dir, f"{construction_no}s.csv")
		if os.path.exists(master_file):
			self.master_data_status.set("✅ 存在します")
		else:
			self.master_data_status.set("❌ 存在しません")

		# 3. 最終レポート
		result_file = os.path.join(self.data_dir, f"{construction_no}result.csv")
		if os.path.exists(result_file):
			self.result_data_status.set("✅ 存在します")
		else:
			self.result_data_status.set("❌ 存在しません")

	def _run_script(self, script_name, on_exit_callback=None):
		"""スクリプトを別プロセスで実行する"""
		if not os.path.exists(script_name):
			messagebox.showerror("ファイルエラー", f"{script_name} が見つかりません。", parent=self.root)
			return
		try:
			process = subprocess.Popen([sys.executable, script_name])
			if on_exit_callback:
				# プロセスの終了をポーリングで監視
				self._check_process_exit(process, on_exit_callback)
		except Exception as e:
			messagebox.showerror("実行エラー", f"{script_name} の起動に失敗しました:\n{e}", parent=self.root)

	def _check_process_exit(self, process, callback):
		"""プロセスの終了を監視し、終了後にコールバックを呼ぶ"""
		if process.poll() is not None: # プロセスが終了した
			callback()
		else: # まだ実行中
			self.root.after(1000, lambda: self._check_process_exit(process, callback))

	def _run_scan(self):
		"""スキャンプロセスを開始する"""
		# スキャン前に選択中の工事番号をconfigに保存
		cn = self.cn_entry.get().strip()
		if cn:
			self.config.set("last_construction_number_scanner", cn)
			self.config.save_config()
		
		# スキャン終了後にステータスを再確認するようにコールバックを設定
		self._run_script("G_ScanBCD_main.py", on_exit_callback=self.check_status)

	def _run_combine(self):
		"""結合レポート作成プロセスを開始する"""
		cn = self.cn_entry.get().strip()
		if not cn:
			messagebox.showwarning("入力エラー", "工事番号を指定してください。", parent=self.root)
			return

		# create_combined_csv.py は last_construction_number を参照するため、設定を更新
		self.config.set("last_construction_number", cn)
		self.config.save_config()
		
		# 実行後にステータスを再確認するようにコールバックを設定
		self._run_script("create_combined_csv.py", on_exit_callback=self.check_status)

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
