# `config.json` 設定リファレンス

このドキュメントは `config.json` ファイルに含まれる各設定項目の目的と機能について説明します。

---

## `___ACTIVE_SETTINGS___` - 現在有効な設定

このセクションの項目は、アプリケーションの基本的な動作を制御する静的な設定です。

### スキャナ・カメラ関連

- `auto_stop` (boolean): `true`の場合、`idle_timeout`で指定した時間スキャンがないと、カメラを自動的に停止します。
- `barcode_type` (string): スキャン対象のバーコードの種類を指定します (例: `"CODE39"`)。
- `camera_height` / `camera_width` (integer): カメラ画像の解像度（高さ・幅）をピクセル単位で指定します。
- `camera_index` (integer): 使用するカメラのデバイスインデックス番号を指定します。通常は`0`が内蔵またはデフォルトのカメラです。
- `expected_length` (integer): 読み取るバーコードの期待する文字数を指定します。この文字数と一致しないバーコードは無視されます。
- `idle_timeout` (integer): `auto_stop`が有効な場合に、スキャンが何秒間ないとタイムアウトとみなすかを指定します。
- `target_fps` (integer): カメラの目標フレームレート（Frame Per Second）を指定します。

### 表示・オーバーレイ関連

- `overlay_alpha` (float): スキャン画面に表示される情報ウィンドウの透明度を`0.0`（完全透明）から`1.0`（完全不透明）の間で指定します。
- `overlay_color` (array of integers): 情報ウィンドウの背景色を`[B, G, R]` (青, 緑, 赤) の値で指定します。
- `overlay_enabled` (boolean): `true`の場合、スキャン画面に情報ウィンドウを表示します。
- `font_scale` (float): 情報ウィンドウに表示されるテキストのフォントサイズ倍率を指定します。
- `display_lines` (integer): スキャン履歴を画面に何行表示するかを指定します。
- `display_time` (integer): スキャンしたバーコード情報を画面に何秒間表示し続けるかを指定します。

### ファイル・ディレクトリ関連

- `data_dir` (string): スキャン結果のCSVファイルなどが保存されるディレクトリ名を指定します。
- `log_dir` (string): アプリケーションの動作ログファイルが保存されるディレクトリ名を指定します。
- `scan_log` (string): `log_dir`内に作成されるログファイルの名前を指定します。
- `source_data_dir` (string): `G_DrawingNumberViewer`などのツールが参照する、マスターデータとなるCSVファイルが格納されているディレクトリ名を指定します。

### 各ツールのデフォルト値・マッピング

- `default_construction_number` (string): 場所選択画面で、工事番号入力欄にデフォルトで表示される値を指定します。
- `default_location` (string): 場所選択画面で、場所の入力欄にデフォルトで表示される値を指定します。
- `default_source_csv_filename` (string): `G_DrawingNumberViewer`で、デフォルトで選択されるマスターデータCSVのファイル名を指定します。
- `display_text_mapping` (object): 場所選択画面のボタン表示名と、内部的に記録される場所名の対応を定義します (例: `"カブト1F": "Kabuto 1F"`)。
- `manual_entry_drawing_barcode_type` (string): 手動登録機能で使われる特殊なバーコードタイプ名を指定します。
- `source_csv_*_column` (string): `G_DrawingNumberViewer`などのツールがマスターデータCSVを読み込む際に、どの列がどのデータ（例: `発注伝票№`, `図番`）に該当するかを指定します。これにより、異なるフォーマットのCSVに対応できます。

---

## `___STATE_AND_HISTORY___` - 前回終了時の状態（自動更新）

このセクションの項目は、ユーザーが最後に行った操作の状態を保存するためのものです。アプリケーションが終了する際に**自動的に書き換えられ**、次回起動時にその状態が復元されます。手動で編集する必要は基本的にありません。

- `last_construction_no_part_viewer`: `G_PartInfoViewer`で最後に使用した工事番号。
- `last_construction_number`: `G_DrawingNumberViewer`で最後に使用した工事番号。
- `last_construction_number_scanner`: `G_ScanBCD_main`（スキャナ本体）で最後に使用した工事番号。
- `last_filter_start_value`: `G_DrawingNumberViewer`で最後に使用したフィルターの開始値。
- `last_location_filter_viewer`: `G_DrawingNumberViewer`で最後に使用した場所フィルター。
- `last_sort_length` / `last_sort_start_index`: `G_DrawingNumberViewer`で最後に使用したソート設定。
- `last_source_csv_path`: `G_DrawingNumberViewer`で最後に使用したマスターデータCSVのフルパス。

---

## `___WINDOW_GEOMETRIES___` - ウィンドウの位置とサイズ（自動更新）

このセクションの項目は、各ツールのウィンドウを最後に閉じたときの位置とサイズを記録します。アプリケーションが終了する際に**自動的に書き換えられ**、次回起動時にその状態が復元されます。

- `window_geometries` (object): 各ツールのクラス名をキーとして、`"幅x高さ+X座標+Y座標"` の形式でウィンドウ情報を保持します。

---

## `___UNUSED_OR_DEPRECATED___` - 未使用または旧式の項目

このセクションの項目は、現在のバージョンの主要なコードからは使用されていないか、より新しい設定に置き換えられたものです。互換性や将来的な改修のために残されていますが、現在の動作には影響を与えません。

- `barcode_data`, `scanned_info`, `scan_count`, `construction_number`, `location`: これらはアプリ実行中に内部的に管理されるデータであり、設定ファイルから読み込む意味がないため、現在は使われていません。
- `csv_file`: かつてデータファイル名を指定していましたが、現在は工事番号から自動生成される仕組みに変わっています。`placeholder_data_filename_for_display`に改名することが推奨されます。
- `data_file`: `scan_log`と同様のログファイル名として想定されていたようですが、現在は使われていません。
- `no_barcode_current_id`: バーコードがない部品にユニークIDを付与する機能で使われる想定だったようですが、現在のコードではこの値を使用している箇所が見当たりません。
