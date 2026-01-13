# G_ScanBCD_Results.py
import tkinter as tk

class ResultDisplay:
	def __init__(self):
		pass

	def show_results(self, scan_count, context_value, construction_number, supplier, context_label="項目", font_size=14, verification_result=None, success_count=0, duplicate_count=0, failure_count=0):
		"""Displays the scan results in a dialog."""
		# ダイアログウィンドウを作成
		root = tk.Tk()
		root.title("スキャン結果")

		main_frame = tk.Frame(root, padx=20, pady=15)
		main_frame.pack(expand=True, fill=tk.BOTH)
		main_frame.columnconfigure(1, weight=1) # 値の列を伸縮させる

		# --- 各行のウィジェットをgridで配置 ---
		row_index = 0
		label_font = ("Helvetica", font_size)
		value_font = ("Helvetica", font_size, "bold")
		value_font_large = ("Helvetica", int(font_size * 1.2), "bold")

		# 工事番号
		tk.Label(main_frame, text="工事番号:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
		tk.Label(main_frame, text=f"{construction_number}", font=value_font).grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
		row_index += 1

		# 場所または工程
		tk.Label(main_frame, text=f"{context_label}:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
		tk.Label(main_frame, text=f"{context_value}", font=value_font).grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
		row_index += 1

		# 納品業者
		tk.Label(main_frame, text="納品業者:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
		tk.Label(main_frame, text=f"{supplier if supplier else '未指定'}", font=value_font).grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
		row_index += 1

		# スキャン数
		tk.Label(main_frame, text="スキャン数:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
		tk.Label(main_frame, text=f"{scan_count} 件", font=value_font_large).grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
		row_index += 1

		# --- スキャン内訳 ---
		tk.Label(main_frame, text="  (成功):", font=label_font).grid(row=row_index, column=0, sticky="w", pady=2, padx=(20, 0))
		tk.Label(main_frame, text=f"{success_count} 件", font=value_font).grid(row=row_index, column=1, sticky="w", padx=10, pady=2)
		row_index += 1

		if duplicate_count > 0:
			tk.Label(main_frame, text="  (重複削除):", font=label_font, fg="#CC8800").grid(row=row_index, column=0, sticky="w", pady=2, padx=(20, 0))
			tk.Label(main_frame, text=f"{duplicate_count} 件", font=value_font, fg="#CC8800").grid(row=row_index, column=1, sticky="w", padx=10, pady=2)
			row_index += 1

		if failure_count > 0:
			tk.Label(main_frame, text="  (データ異常):", font=label_font, fg="red").grid(row=row_index, column=0, sticky="w", pady=2, padx=(20, 0))
			tk.Label(main_frame, text=f"{failure_count} 件", font=value_font, fg="red").grid(row=row_index, column=1, sticky="w", padx=10, pady=2)
			row_index += 1

		# --- 照合結果の表示 ---
		if verification_result and verification_result.get("source_loaded"):
			match = verification_result["match_count"]
			total_source = verification_result["total_source_count"]
			mismatch = verification_result["mismatch_count"]
			
			# 照合OK数
			tk.Label(main_frame, text="図面照合OK:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
			tk.Label(main_frame, text=f"{match} / {total_source} 件", font=value_font).grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
			row_index += 1
			
			# 照合NGがあれば赤字で表示
			if mismatch > 0:
				tk.Label(main_frame, text="照合不明(NG):", font=label_font, fg="red").grid(row=row_index, column=0, sticky="w", pady=4)
				tk.Label(main_frame, text=f"{mismatch} 件", font=value_font, fg="red").grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
				row_index += 1
		elif verification_result and not verification_result.get("source_loaded"):
			tk.Label(main_frame, text="図面データ:", font=label_font).grid(row=row_index, column=0, sticky="w", pady=4)
			tk.Label(main_frame, text="なし (照合不可)", font=value_font, fg="gray").grid(row=row_index, column=1, sticky="w", padx=10, pady=4)
			row_index += 1

		# 閉じるボタン
		close_button = tk.Button(main_frame, text="閉じる (Esc)", command=root.destroy, font=("Helvetica", 12))
		close_button.grid(row=row_index, column=0, columnspan=2, pady=(20, 0))

		# ESCキーでウィンドウを閉じる
		root.bind("<Escape>", lambda e: root.destroy())

		# ウィンドウの位置を画面の右寄せで表示
		root.update_idletasks()
		window_width = root.winfo_reqwidth()
		window_height = root.winfo_reqheight()
		screen_width = root.winfo_screenwidth()
		x = screen_width - window_width - 10  # 右端から10ピクセル内側
		y = 10  # 上端から10ピクセル下
		root.geometry(f"{window_width}x{window_height}+{x}+{y}")

		# ダイアログを表示
		# 最前面に表示し、フォーカスを強制する
		root.attributes("-topmost", True)
		root.focus_force()
		
		root.mainloop()
