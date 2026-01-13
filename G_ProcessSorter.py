# G_ProcessSorter.py
import tkinter as tk
import os  # osモジュールをインポート
import sys  # sysをインポート
import subprocess  # 多重起動チェックのために追加
from tkinter import ttk, messagebox
from G_config import Config
from G_ProcessScanner import ProcessScanner  # スキャナークラスを直接インポート
from G_ScanBCD_FixCSV import CSVHandler  # データ修正ツールをインポート
from G_ScanBCD_Results import ResultDisplay  # 結果表示クラスをインポート


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
        self.supplier_list = sorted(
            self.config.get("supplier_list", [])
        )  # ソートして読み込む
        self.process_definitions = self.config.get(
            "process_definitions", ["工程未定義"]
        )
        
        # 読み込み時にソートを適用（完品を先頭に）
        self._sort_process_definitions()

        self._build_ui()

        # --- ESCキーと閉じるボタンでのキャンセル処理 ---
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.bind("<Escape>", lambda e: self._on_cancel())

    def _sort_process_definitions(self):
        """工程リストをソートする（完品を先頭、他は昇順）"""
        sorted_processes = sorted(self.process_definitions)
        if "完品" in sorted_processes:
            sorted_processes.remove("完品")
            sorted_processes.insert(0, "完品")
        self.process_definitions = sorted_processes

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- 入力フレーム ---
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=5, fill=tk.X, expand=True)
        input_frame.columnconfigure(1, weight=1)

        # 1. 工事番号
        ttk.Label(input_frame, text="工事番号:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.cn_entry = ttk.Entry(input_frame)
        self.cn_entry.insert(0, self.construction_number)
        self.cn_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 2. 納品業者 (Comboboxに変更)
        ttk.Label(input_frame, text="納品業者:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.supplier_combo = ttk.Combobox(input_frame, values=self.supplier_list)
        self.supplier_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 3. 追加工程 (Comboboxに変更)
        ttk.Label(input_frame, text="追加工程:").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.process_combo = ttk.Combobox(input_frame, values=self.process_definitions)
        self.process_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # 4. スキャン開始ボタン
        start_button = ttk.Button(
            main_frame,
            text="スキャン開始",
            command=self._on_start_scan,
            style="Accent.TButton",
        )
        start_button.pack(pady=15, fill=tk.X)
        self.root.bind("<Return>", lambda e: self._on_start_scan())

    def _on_start_scan(self):
        cn = self.cn_entry.get().strip()
        if not cn:
            messagebox.showwarning(
                "入力エラー", "工事番号を入力してください。", parent=self.root
            )
            return

        supplier = self.supplier_combo.get().strip()
        if not supplier:
            messagebox.showwarning(
                "入力エラー", "納品業者を入力してください。", parent=self.root
            )
            return

        process_name = self.process_combo.get().strip()
        if not process_name:
            messagebox.showwarning(
                "入力エラー", "追加工程を選択してください。", parent=self.root
            )
            return

        self.selected_process = process_name
        self.construction_number = cn
        self.supplier_name = supplier

        # --- 設定の保存ロジック ---
        self.config.set("last_construction_number", cn)

        # 新しい納品業者をリストに追加して保存 (大文字・小文字を区別せずにチェック)
        if supplier and supplier not in self.supplier_list:
            print(f"情報: 新しい納品業者 '{supplier}' を設定ファイルに追加します。")
            self.supplier_list.append(supplier)
            self.config.set("supplier_list", sorted(self.supplier_list))

        # 新しい工程をリストに追加して保存
        if process_name and process_name not in self.process_definitions:
            print(f"情報: 新しい工程 '{process_name}' を設定ファイルに追加します。")
            self.process_definitions.append(process_name)

            self._sort_process_definitions()
            self.config.set("process_definitions", self.process_definitions)

        # 最後に一度だけ保存
        self.config.save_config()

        self.root.destroy()

    def get_selection(self):
        self.root.mainloop()
        return self.selected_process, self.construction_number, self.supplier_name

    def _on_cancel(self):
        """ウィンドウがキャンセルされたときの処理"""
        self.selected_process = None
        self.construction_number = None
        self.supplier_name = None
        self.root.destroy()


def main():
    """
    メイン処理。工程を選択させ、その情報を引数としてスキャナを起動する。
    G_ScanBCD_main.py を参考に作成。
    """
    # --- シングルインスタンス化のためのロックファイル処理 (改善版) ---
    lock_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "G_ProcessSorter.py.lock"
    )

    if os.path.exists(lock_file_path):
        try:
            with open(lock_file_path, "r") as f:
                pid = int(f.read().strip())
            # プロセスが存在するかチェック (Windowsではtasklist, Unix系ではps)
            if sys.platform == "win32":
                output = subprocess.check_output(["tasklist", "/FI", f"PID eq {pid}"]).decode('utf-8', 'ignore')
                if str(pid) in output:
                    messagebox.showwarning("起動済み", "工程仕分けツールは既に起動しています。")
                    return
            else: # macOS, Linux
                # psコマンドでプロセスが存在するか確認
                if os.system(f"ps -p {pid} > /dev/null") == 0:
                    messagebox.showwarning("起動済み", "工程仕分けツールは既に起動しています。")
                    return
            # 実行中でなければロックファイルを削除
            os.remove(lock_file_path)
        except (ValueError, FileNotFoundError, subprocess.CalledProcessError):
            # ファイルが読めない、プロセスIDが不正などの場合は、ロックファイルを削除
            try:
                os.remove(lock_file_path)
            except FileNotFoundError:
                pass # すでに消えている場合は何もしない

    def cleanup_lock_file():
        """ロックファイルを削除するクリーンアップ関数"""
        if os.path.exists(lock_file_path):
            os.remove(lock_file_path)

    # --- スプラッシュスクリーンの表示 ---
    splash_root = tk.Tk()
    splash_root.title("起動中")
    splash_root.geometry("300x100")
    # ウィンドウを中央に配置
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    x = (screen_width // 2) - (300 // 2)
    y = (screen_height // 2) - (100 // 2)
    splash_root.geometry(f"+{x}+{y}")
    splash_root.overrideredirect(True)  # ウィンドウ枠を非表示
    ttk.Label(
        splash_root, text="アプリケーションを起動しています...", font=("", 10)
    ).pack(pady=20)
    progress = ttk.Progressbar(
        splash_root, orient="horizontal", length=250, mode="indeterminate"
    )
    progress.pack(pady=5)
    progress.start(10)
    splash_root.update()  # スプラッシュスクリーンを即時描画

    try:
        # --- 時間のかかる初期化処理 ---
        with open(lock_file_path, "w") as f:
            f.write(str(os.getpid()))

        config = Config("config.json")

        # メインウィンドウを裏で作成
        main_root = tk.Tk()
        main_root.withdraw()  # 表示はまだしない
        selector = ProcessSelector(main_root, config)

        # --- 初期化完了後、スプラッシュを消してメインを表示 ---
        progress.stop()  # プログレスバーのアニメーションを停止
        splash_root.destroy()

        # --- コマンドライン引数から位置情報を取得 ---
        pos_args = {}
        if "--pos" in sys.argv:
            try:
                index = sys.argv.index("--pos")
                pos_args["x"] = int(sys.argv[index + 1])
                pos_args["y"] = int(sys.argv[index + 2])
            except (ValueError, IndexError):
                pass  # 引数が不正な場合は無視

        # 位置情報があれば設定
        if "x" in pos_args and "y" in pos_args:
            main_root.geometry(f"+{pos_args['x']}+{pos_args['y']}")

        main_root.deiconify()  # メインウィンドウを表示

        # 1. 工程選択UIの表示と結果取得
        process, construction_no, supplier_name = selector.get_selection()

        if not all([process, construction_no, supplier_name]):
            print(
                "工程、工事番号、納品業者のいずれかが選択されなかったため、処理を中断します。"
            )
            return

        print(
            f"選択された工程: {process}, 工事番号: {construction_no}, 納品業者: {supplier_name}"
        )

        # 2. ProcessScannerのインスタンスを作成して起動
        scanner = ProcessScanner(
            config=config,
            construction_number=construction_no,
            process_name=process,
            supplier_name=supplier_name,
        )
        scanner.start()  # スキャンウィンドウが閉じるまで待機

        # CSVの状態チェック (重複・異常データの件数を取得)
        processed_csv_file = os.path.join(
            config.get("data_dir", "data"),
            f"{scanner.construction_number}_processed.csv",
        )
        csv_duplicates = 0
        csv_invalid = 0
        if os.path.exists(processed_csv_file):
            handler = CSVHandler(processed_csv_file, config)
            csv_status = handler.check_data_status()
            csv_duplicates = csv_status["duplicates"]
            csv_invalid = csv_status["invalid"]

        # 3. スキャン終了後に結果を表示
        result_display = ResultDisplay()
        result_display.show_results(
            scanner.scan_count,
            process,
            construction_no,
            supplier_name,
            context_label="工程",
            success_count=scanner.success_count,
            duplicate_count=csv_duplicates,
            failure_count=csv_invalid
        )

        # 4. ★★★ スキャン完了後に、CSVの重複・不正チェックを自動実行 ★★★
        print("\n工程データの重複・不正チェックを実行します...")
        # processed_csv_file は上で定義済み
        if os.path.exists(processed_csv_file):
            # データ修正ツールのハンドラーを呼び出す
            handler = CSVHandler(processed_csv_file, config)
            handler.find_duplicates_and_invalid_rows()
        else:
            print(
                f"情報: チェック対象のファイル {processed_csv_file} が見つかりませんでした。"
            )
    except Exception as e:
        # エラーが発生した場合はスプラッシュを閉じてからメッセージ表示
        if "progress" in locals() and progress.winfo_exists():
            # progressバーが存在すれば、親のsplash_rootも存在すると考えられる
            if splash_root.winfo_exists():
                progress.stop()
                splash_root.destroy()
        messagebox.showerror(
            "実行エラー", f"工程スキャナーの実行中にエラーが発生しました:\n{e}"
        )
    finally:
        # 正常終了時も異常終了時も必ずロックファイルを削除
        cleanup_lock_file()


if __name__ == "__main__":
    main()
