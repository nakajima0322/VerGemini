# G_ScanBCD_Results.py
import tkinter as tk

class ResultDisplay:
	def __init__(self):
		pass

	def show_results(self, scan_count, location, construction_number):
		"""Displays the scan results in a dialog."""
		# ダイアログウィンドウを作成
		root = tk.Tk()
		root.title("スキャン結果")

		# ウィジェットの作成
		construction_label_title = tk.Label(root, text="工事番号:", font=("Helvetica", 16))
		construction_label_title.pack(pady=5)
		construction_label = tk.Label(root, text=f"{construction_number}", font=("Helvetica", 20))
		construction_label.pack(pady=10)

		location_label_title = tk.Label(root, text="選択項目:", font=("Helvetica", 16))
		location_label_title.pack(pady=5)
		location_label = tk.Label(root, text=f"{location}", font=("Helvetica", 20, "bold"))
		location_label.pack(pady=10)

		scan_count_label_title = tk.Label(root, text="スキャンしたバーコードの数:", font=("Helvetica", 16))
		scan_count_label_title.pack(pady=5)
		scan_count_label = tk.Label(root, text=f"{scan_count}", font=("Helvetica", 20))
		scan_count_label.pack(pady=10)

		close_button = tk.Button(root, text="閉じる", command=root.destroy, font=("Helvetica", 14))
		close_button.pack(pady=10)

		# ウィンドウのサイズを自動調整
		root.update_idletasks()  # ウィジェットのサイズを計算
		extra_width = 50  # 幅方向に余裕を追加
		extra_height = 20  # 高さ方向に余裕を追加
		window_width = root.winfo_reqwidth() + extra_width
		window_height = root.winfo_reqheight() + extra_height

		# ウィンドウの位置を画面の右寄せで表示
		screen_width = root.winfo_screenwidth()
		# screen_height = root.winfo_screenheight() # 未使用のため削除
		x = screen_width - window_width - 10  # 右端から10ピクセル内側
		y = 10  # 上端から10ピクセル下
		root.geometry(f"{window_width}x{window_height}+{x}+{y}")

		# ダイアログを表示
		root.mainloop()
