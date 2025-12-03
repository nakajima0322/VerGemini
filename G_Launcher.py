# G_Launcher.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import sys
import os
from G_config import Config  # Configクラスをインポート


class LauncherApp:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.title("Tool Launcher")
        # self.root.geometry("400x400") # 固定サイズ指定を削除し、自動調整に任せる

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # --- ★★★ 作業者選択エリア (新規追加) ★★★ ---
        worker_frame = ttk.LabelFrame(
            main_frame, text="作業者を選択してください", padding="10"
        )
        worker_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        worker_frame.rowconfigure(0, weight=1)
        worker_frame.columnconfigure(0, weight=1)

        # ListboxとScrollbarを配置するフレーム
        listbox_container = ttk.Frame(worker_frame)
        listbox_container.grid(row=0, column=0, sticky="nsew")
        listbox_container.rowconfigure(0, weight=1)
        listbox_container.columnconfigure(0, weight=1)

        self.worker_listbox = tk.Listbox(
            listbox_container, exportselection=False, height=4
        )
        self.worker_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            listbox_container, orient=tk.VERTICAL, command=self.worker_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.worker_listbox.config(yscrollcommand=scrollbar.set)

        worker_list = sorted(self.config.get("worker_list", []))
        for worker in worker_list:
            self.worker_listbox.insert(tk.END, worker)

        btn_width = 35
        btn_pady = 5

        # --- メインワークフロー カテゴリ ---
        workflow_frame = ttk.LabelFrame(
            main_frame, text="メインワークフロー", padding="10"
        )
        workflow_frame.pack(fill=tk.X, padx=10, pady=5)

        process_sorter_button = ttk.Button(
            workflow_frame,
            text="工程登録スキャン",
            command=self._run_process_sorter,
            width=btn_width,
        )
        process_sorter_button.pack(pady=btn_pady)

        scan_button = ttk.Button(
            workflow_frame,
            text="保管場所登録スキャン",
            command=self._run_scan_bcd_main,
            width=btn_width,
        )
        scan_button.pack(pady=btn_pady)

        location_viewer_button = ttk.Button(
            workflow_frame,
            text="保管場所照合ツール起動",
            command=self._run_location_viewer,
            width=btn_width,
        )
        location_viewer_button.pack(pady=btn_pady)

        part_info_button = ttk.Button(
            workflow_frame,
            text="部品情報表示ツール起動",
            command=self._run_part_info_viewer,
            width=btn_width,
        )
        part_info_button.pack(pady=btn_pady)

        combine_csv_button = ttk.Button(
            workflow_frame,
            text="結合CSV作成",
            command=self._run_create_combined_csv,
            width=btn_width,
        )
        combine_csv_button.pack(pady=btn_pady)

        # --- 管理・設定 カテゴリ ---
        admin_frame = ttk.LabelFrame(main_frame, text="管理・設定", padding="10")
        admin_frame.pack(fill=tk.X, padx=10, pady=5)

        worker_manager_button = ttk.Button(
            admin_frame,
            text="作業者リスト管理",
            command=self._open_worker_manager,
            width=btn_width,
        )
        worker_manager_button.pack(pady=btn_pady)

        csv_fixer_button = ttk.Button(
            admin_frame,
            text="データ修正ツール (FixCSV)",
            command=self._run_csv_fixer,
            width=btn_width,
        )
        csv_fixer_button.pack(pady=btn_pady)

        data_editor_button = ttk.Button(
            admin_frame,
            text="データビューア/エディタ",
            command=self._run_data_editor,
            width=btn_width,
        )
        data_editor_button.pack(pady=btn_pady)

        workflow_button = ttk.Button(
            admin_frame,
            text="ワークフロー管理ツール起動",
            command=self._run_workflow_manager,
            width=btn_width,
        )
        workflow_button.pack(pady=btn_pady)
        config_editor_button = ttk.Button(
            admin_frame,
            text="設定編集",
            command=self._run_config_editor,
            width=btn_width,
        )
        config_editor_button.pack(pady=btn_pady)

        # --- 終了ボタン ---
        exit_button = ttk.Button(
            main_frame, text="終了", command=self._on_closing, width=btn_width
        )
        exit_button.pack(side="bottom", pady=10)

        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind("<Escape>", lambda e: self._on_closing())

        # --- フォーカスイベントのバインド ---
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)

    def _check_file_exists(self, script_name):
        if not os.path.exists(script_name):
            messagebox.showerror(
                "ファイルエラー",
                f"{script_name} が見つかりません。\nカレントディレクトリを確認してください。",
                parent=self.root,
            )
            return False
        return True

    def _run_tool(self, script_name, args=None):
        """作業者が選択されていることを確認し、ツールを起動する"""
        # 1. ランチャー上のListboxから選択されている作業者名を取得
        selected_indices = self.worker_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning(
                "作業者未選択", "作業者を選択してください。", parent=self.root
            )
            return

        worker_name = self.worker_listbox.get(selected_indices[0])

        # 2. 新しい作業者であればリストを更新し、現在の作業者として設定を保存
        worker_list = self.config.get("worker_list", [])
        if worker_name not in worker_list:
            # このUIでは新しい作業者は追加されないが、念のためロジックは残す
            self.config.set("worker_list", sorted(worker_list))
        self.config.set("current_worker", worker_name)
        self.config.save_config()

        print(f"作業者 '{worker_name}' を選択して {script_name} を起動します。")

        # --- ツール起動直前に、ランチャーの最前面表示を一時的に解除 ---
        self.root.attributes("-topmost", False)

        # --- 新しいウィンドウの推奨位置を計算 ---
        # argsリストをコピーして変更
        final_args = list(args) if args else []
        try:
            self.root.update_idletasks()
            geo_str = self.root.winfo_geometry()  # "widthxheight+x+y"
            size, x_str, y_str = geo_str.split("+")
            width, _ = size.split("x")

            # ランチャーの右隣のX座標を計算 (20pxのマージン)
            new_x = int(x_str) + int(width) + 20
            final_args.extend(["--pos", str(new_x), str(y_str)])
        except Exception as e:
            print(f"ウィンドウ位置の計算中にエラーが発生しました: {e}")

        command = [sys.executable, script_name]
        if final_args:
            command.extend(final_args)

        try:
            print(f"実行中: {' '.join(command)}")
            subprocess.Popen(command)
        except Exception as e:
            messagebox.showerror(
                "実行エラー",
                f"{script_name} の起動中にエラーが発生しました:\n{e}",
                parent=self.root,
            )
            print(f"エラー: {script_name} 起動失敗 - {e}")
        finally:
            # ツール起動後、作業者リストの選択を解除し、フォーカスを外す
            self.worker_listbox.selection_clear(0, tk.END)
            self.root.focus_set()

    def _open_worker_manager(self):
        """作業者リストを管理するウィンドウを開く"""
        manager_win = tk.Toplevel(self.root)
        manager_win.title("作業者リスト管理")
        manager_win.transient(self.root)
        manager_win.grab_set()

        frame = ttk.Frame(manager_win, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Listbox to show workers
        listbox_frame = ttk.Frame(frame)
        listbox_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5)
        listbox_frame.rowconfigure(0, weight=1)
        listbox_frame.columnconfigure(0, weight=1)

        listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            listbox_frame, orient=tk.VERTICAL, command=listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        listbox.config(yscrollcommand=scrollbar.set)

        def populate_listbox():
            """リストボックスに現在の作業者リストを表示する"""
            listbox.delete(0, tk.END)
            self.config.load_config()  # 最新の情報を読み込む
            worker_list = sorted(self.config.get("worker_list", []))
            for worker in worker_list:
                listbox.insert(tk.END, worker)

        def delete_worker():
            """選択された作業者をリストから削除する"""
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning(
                    "選択エラー",
                    "削除する作業者を選択してください。",
                    parent=manager_win,
                )
                return

            selected_worker = listbox.get(selected_indices[0])
            if messagebox.askyesno(
                "削除確認",
                f"作業者 '{selected_worker}' をリストから削除しますか？",
                parent=manager_win,
            ):
                current_list = self.config.get("worker_list", [])
                if selected_worker in current_list:
                    current_list.remove(selected_worker)
                    self.config.set("worker_list", current_list)
                    self.config.save_config()
                    populate_listbox()  # リストを再表示
            # ランチャー本体のリストボックスも更新する
            self.update_launcher_worker_list()

        def add_worker():
            """新しい作業者を追加する"""
            new_worker = simpledialog.askstring(
                "作業者を追加", "新しい作業者名を入力してください:", parent=manager_win
            )
            if new_worker:
                new_worker = new_worker.strip()
                if new_worker:
                    current_list = self.config.get("worker_list", [])
                    if new_worker not in current_list:
                        current_list.append(new_worker)
                        self.config.set("worker_list", sorted(current_list))
                        self.config.save_config()
                        populate_listbox()  # リストを再表示
                        # ランチャー本体のリストボックスも更新する
                        self.update_launcher_worker_list()
                    else:
                        messagebox.showwarning(
                            "追加エラー",
                            f"作業者 '{new_worker}' は既に存在します。",
                            parent=manager_win,
                        )

        populate_listbox()

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(
            button_frame, text="選択した作業者を削除", command=delete_worker
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="作業者を追加", command=add_worker).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="閉じる", command=manager_win.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def update_launcher_worker_list(self):
        """ランチャーの作業者リストボックスを最新の情報に更新する"""
        self.worker_listbox.delete(0, tk.END)
        self.config.load_config()
        worker_list = sorted(self.config.get("worker_list", []))
        for worker in worker_list:
            self.worker_listbox.insert(tk.END, worker)

    def _run_process_sorter(self):
        self._run_tool("G_ProcessSorter.py")

    def _run_scan_bcd_main(self):
        self._run_tool("G_ScanBCD_main.py")

    def _run_location_viewer(self):
        # デモ用にデフォルトの工事番号を引数として渡す
        default_cn = self.config.get("default_construction_number", "")
        args = ["--cn", default_cn] if default_cn else []
        self._run_tool("G_DrawingNumberViewer.py", args=args)

    def _run_part_info_viewer(self):
        # デモ用にデフォルトの工事番号を引数として渡す
        default_cn = self.config.get("default_construction_number", "")
        args = [default_cn] if default_cn else []  # このツールは引数の形式が少し違う
        self._run_tool("G_PartInfoViewer.py", args=args)

    def _run_create_combined_csv(self):
        self._run_tool("create_combined_csv.py")

    def _run_config_editor(self):
        # 設定エディタは作業者選択が不要な場合、別のメソッドで起動
        if not self._check_file_exists("G_ConfigEditor.py"):
            return
        subprocess.Popen([sys.executable, "G_ConfigEditor.py"])

    def _run_csv_fixer(self):
        """データ修正ツール(G_ScanBCD_FixCSV.py)を起動する"""
        if not self._check_file_exists("G_ScanBCD_FixCSV.py"):
            return
        subprocess.Popen([sys.executable, "G_ScanBCD_FixCSV.py"])

    def _run_workflow_manager(self):
        self._run_tool("G_WorkflowManager.py")

    def _run_data_editor(self):
        self._run_tool("G_DataViewerEditor.py")

    def _on_closing(self):
        print("KHTツールランチャーを終了します。")
        self.root.quit()

    def _on_focus_in(self, event):
        """ウィンドウにフォーカスが戻ったときに最前面表示にする"""
        self.root.attributes("-topmost", True)

    def _on_focus_out(self, event):
        """ウィンドウからフォーカスが外れたときに最前面表示を解除する"""
        self.root.attributes("-topmost", False)


if __name__ == "__main__":
    try:
        config = Config("config.json")

        # メインのランチャーウィンドウを起動
        main_root = tk.Tk()
        app = LauncherApp(main_root, config)
        # ウィンドウを中央に表示
        main_root.update_idletasks()
        screen_width = main_root.winfo_screenwidth()
        screen_height = main_root.winfo_screenheight()
        x = (screen_width // 2) - (main_root.winfo_width() // 2)
        y = (screen_height // 2) - (main_root.winfo_height() // 2)
        main_root.geometry(f"+{x}+{y}")

        # ウィンドウを最前面に表示する
        main_root.attributes("-topmost", True)
        main_root.mainloop()

        print("ランチャーのコード実行が完了しました。")

    except Exception as e:
        messagebox.showerror("起動エラー", f"ランチャーの起動に失敗しました:\n{e}")
