# G_ScanBCD_Location.py
# 場所情報の選択画面を表示するクラス
import tkinter as tk
from tkinter import messagebox

class LocationSelector:
    # 要求される設定値のキー
    REQUIRED_KEYS = {
        "display_text_mapping",
        "default_construction_number",
        "default_location",
        "csv_file",
        "scan_log",
        "barcode_type",
        "expected_length"
    }

    def __init__(self, config):
        self.config = config

        self.location =             self.config.get("default_location")
        self.construction_number =  self.config.get("default_construction_number")
        self.csv_file =             self.config.get("csv_file")
        self.scan_log =             self.config.get("scan_log")
        self.barcode_type =         self.config.get("barcode_type")
        self.expected_length =      self.config.get("expected_length")
        self.display_text_mapping = self.config.get("display_text_mapping") 

        missing_keys=[]
        for key in self.REQUIRED_KEYS:
            if self.config.get(key) is None:
                  missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"設定ファイルに以下のキーが存在しません: {', '.join(missing_keys)}")

    def _validate_construction_number(self, input_value):
        """工事番号のバリデーションを行う"""
        if input_value.strip() == "":
            return "unknown"
        elif input_value.isdigit() and len(input_value) == 4:
            return input_value
        else:
            messagebox.showerror("エラー", "工事番号は4桁の数字で入力してください")
            return None

    def _select_location_by_button(self, location, construction_entry, root):
        """ボタンで場所を選択する処理"""
        self.location = location
        input_value = construction_entry.get()
        self.construction_number = self._validate_construction_number(input_value)
        if self.construction_number:
            root.destroy()

    def _submit_location_by_entry(self, location_entry, construction_entry, root):
        """テキストボックスで場所を入力する処理"""
        input_location = location_entry.get().strip()
        if input_location:
            self.location = input_location
            input_value = construction_entry.get()
            self.construction_number = self._validate_construction_number(input_value)
            if self.construction_number:
                root.destroy()
        else:
            messagebox.showerror("エラー", "場所を入力してください")

    def get_location(self):
        root = tk.Tk()
        root.title("場所情報の選択")

        # ウィジェットの作成
        # 工事番号入力欄
        tk.Label(root, text="工事番号（4桁の数字・確認用）", font=("Arial", 10)).pack(pady=(10,2))
        construction_entry = tk.Entry(root, font=("Arial", 10), justify="center", width=10)
        construction_entry.insert(0, self.construction_number)  # 初期値を設定
        construction_entry.pack()

        # フォーカス時に全選択するイベントハンドラ
        def select_all_on_focus(event):
            event.widget.select_range(0, tk.END)  # 全選択
            event.widget.icursor(tk.END)  # カーソルを末尾に移動

        # フォーカス時に全選択するイベントをバインド
        construction_entry.bind("<FocusIn>", select_all_on_focus)

        # 場所選択の説明
        tk.Label(root, text="場所を選択してください", font=("Arial", 10)).pack(padx=10)

        locations = list(self.display_text_mapping.keys())

        # ボタンで選択する方法
        location_buttons = []  # ボタンを格納するリスト
        for loc in locations:
            button = tk.Button(root, text=loc, font=("Arial", 10), command=lambda l=loc: self._select_location_by_button(l, construction_entry, root), width=10)
            button.pack(pady=2)
            location_buttons.append(button)  # ボタンをリストに追加

        # テキストボックスで入力する方法
        tk.Label(root, text="または、直接入力してください", font=("Arial", 10)).pack(pady=(10,2))
        location_entry = tk.Entry(root, font=("Arial", 10), justify="center", width=20)
        location_entry.insert(0, self.location)  # 初期値を設定
        location_entry.pack(pady=5)

        # フォーカス時に全選択するイベントをバインド
        location_entry.bind("<FocusIn>", select_all_on_focus)

        submit_button = tk.Button(root, text="入力を確定", font=("Arial", 10), command=lambda: self._submit_location_by_entry(location_entry, construction_entry, root))
        submit_button.pack(pady=5)

        # 設定情報の表示
        csv_file = self.config.get("csv_file", "data.csv")
        scan_log = self.config.get("scan_log", "scanned_barcodes.csv")
        barcode_type = self.config.get("barcode_type", "CODE39")
        expected_length = self.config.get("expected_length", 10)

        info_text = f"DATA: \tScanBCD.dat\nLOG: \t{scan_log}\nTYPE: \t{barcode_type}\nDIGIT: \t{expected_length} 桁"
        tk.Label(root, text="\n【設定情報】", font=("Arial", 10), fg="gray").pack()
        tk.Label(root, text=info_text, font=("Arial", 10), fg="gray", justify="left").pack(padx=10)

        # ウィンドウのサイズを自動調整
        root.update_idletasks()  # ウィジェットのサイズを計算
        extra_width = 50  # 幅方向に余裕を追加
        extra_height = 20  # 高さ方向に余裕を追加
        root.minsize(root.winfo_reqwidth() + extra_width, root.winfo_reqheight() + extra_height)  # 必要な最小サイズを設定

        # ウィンドウの位置を画面の右端に設定
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = root.winfo_reqwidth() + extra_width
        window_height = root.winfo_reqheight() + extra_height
        x = screen_width - window_width - 10  # 右端から10ピクセル内側
        y = 10  # 上端から10ピクセル下
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # 工事番号入力欄にフォーカスを設定
        construction_entry.focus_set()

        # リターンキーが押されたときの処理
        def on_return_key(event):
            focused_widget = root.focus_get()
            if focused_widget == construction_entry:
                # 工事番号入力欄がフォーカスされている場合
                if location_buttons:
                    location_buttons[0].focus_set()
            elif focused_widget in location_buttons:
                # ボタンがフォーカスされている場合
                self.location = focused_widget.cget("text")
                self._select_location_by_button(self.location, construction_entry, root)
            elif focused_widget == location_entry:
                # テキストボックスがフォーカスされている場合
                self.location = location_entry.get().strip()
                self._submit_location_by_entry(location_entry, construction_entry, root)

        # リターンキーのイベントをバインド
        root.bind("<Return>", on_return_key)

        # フォーカス可能なウィジェットのリスト
        focusable_widgets = location_buttons + [location_entry]
        
        # 現在のフォーカス位置を追跡
        current_focus_index = 0

        # 上矢印キーが押されたときの処理
        def on_up_arrow(event):
            nonlocal current_focus_index
            current_focus_index -= 1
            if current_focus_index < 0:
                current_focus_index = len(focusable_widgets) - 1
            focusable_widgets[current_focus_index].focus_set()

        # 下矢印キーが押されたときの処理
        def on_down_arrow(event):
            nonlocal current_focus_index
            current_focus_index += 1
            if current_focus_index >= len(focusable_widgets):
                current_focus_index = 0
            focusable_widgets[current_focus_index].focus_set()

        # 上矢印キーと下矢印キーのイベントをバインド
        root.bind("<Up>", on_up_arrow)
        root.bind("<Down>", on_down_arrow)

        root.mainloop()
        return self.location, self.construction_number

if __name__ == "__main__":
    print("\n単体起動中...")
    from G_config import Config
    config = Config("config.json")
    selector = LocationSelector(config)
    try:
        location, construction_number = selector.get_location()
        print(f"\nLocation: {location},\nConstruction Number: {construction_number}\n")
    except KeyboardInterrupt:
        print("\nプログラムが中断されました。")
