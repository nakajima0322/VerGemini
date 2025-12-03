import cv2
import numpy as np
from pyzbar.pyzbar import decode
import time
import csv
import sys
import os
from datetime import datetime
from G_config import Config # 設定ファイル管理クラスをインポート

"""
バーコード読み取りテスト用スクリプト

Purpose:
To validate the logic for real-time analysis and user feedback on why a barcode cannot be read.
This script is independent of the main system, allowing for free experimentation.

Analyzed Items:
1. Focus: Evaluates image sharpness using Laplacian variance.
2. Brightness: Evaluates the average brightness of the entire image.
3. Barcode Size: Evaluates the rectangle size of the detected barcode.

How to Use:
1. Run the script to display the camera feed.
2. Hold a barcode up to the camera.
3. If the read is successful, barcode information and "OK" will be displayed.
4. If the read fails, the estimated cause will be displayed on the screen.
   - "Focus is off"
   - "Too dark" / "Too bright"
   - "Barcode too far" / "Barcode too close"
5. Press the 'q' key or ESC key to exit.
"""

# --- 設定の読み込み ---
# config.jsonからテストツールの設定を読み込む
config = Config("config.json")
tester_settings = config.get("readability_tester_settings", {})

# ぼやけ検出の閾値
FOCUS_THRESHOLD = tester_settings.get("focus_threshold", 115.0)

# 明るさ検出の閾値 (固定値でOKな場合が多い)
BRIGHTNESS_TOO_DARK_THRESHOLD = 70
BRIGHTNESS_TOO_BRIGHT_THRESHOLD = 180

# バーコードの推奨サイズ（面積）の閾値
SIZE_TOO_SMALL_THRESHOLD = tester_settings.get("size_too_small_threshold", 6500)
SIZE_TOO_LARGE_THRESHOLD = tester_settings.get("size_too_large_threshold", 148000)

# カメラ設定 (config.jsonのグローバル設定から読み込み)
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


def draw_gauge(frame, y_pos, label, value, min_val, max_val, optimal_min, optimal_max, peak_value):
    """
    アナログゲージ風のバーを画面に描画する。
    - y_pos: 描画するY座標
    - label: "Focus", "Brightness" などのラベル
    - value: 現在の値
    - min_val, max_val: ゲージの最小値と最大値
    - optimal_min, optimal_max: 正常範囲（グリーンゾーン）の最小・最大値
    - peak_value: ピークホールド値
    """
    gauge_x = CAMERA_WIDTH - 280
    gauge_width = 260
    gauge_height = 20

    # 0. ラベルを描画
    cv2.putText(frame, label, (gauge_x, y_pos - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 1. ゲージの背景を描画 (ダークグレー)
    cv2.rectangle(frame, (gauge_x, y_pos), (gauge_x + gauge_width, y_pos + gauge_height), (50, 50, 50), -1)

    # 2. 正常範囲（グリーンゾーン）を描画
    optimal_start_x = int(gauge_x + (optimal_min - min_val) / (max_val - min_val) * gauge_width)
    optimal_end_x = int(gauge_x + (optimal_max - min_val) / (max_val - min_val) * gauge_width)
    cv2.rectangle(frame, (optimal_start_x, y_pos), (optimal_end_x, y_pos + gauge_height), (0, 180, 0), -1)

    # 3. 現在値のバーを描画
    current_val_pos = int(gauge_x + (value - min_val) / (max_val - min_val) * gauge_width)
    current_val_pos = max(gauge_x, min(current_val_pos, gauge_x + gauge_width)) # 範囲内に収める
    cv2.rectangle(frame, (gauge_x, y_pos), (current_val_pos, y_pos + gauge_height), (200, 200, 200), -1)

    # 4. ピークホールド値のインジケーターを描画 (赤い線)
    if peak_value > min_val:
        peak_pos_x = int(gauge_x + (peak_value - min_val) / (max_val - min_val) * gauge_width)
        peak_pos_x = max(gauge_x, min(peak_pos_x, gauge_x + gauge_width))
        cv2.line(frame, (peak_pos_x, y_pos), (peak_pos_x, y_pos + gauge_height), (0, 0, 255), 2)

    # 5. ゲージの枠線を描画
    cv2.rectangle(frame, (gauge_x, y_pos), (gauge_x + gauge_width, y_pos + gauge_height), (255, 255, 255), 1)

    # 6. 現在の数値をテキストで表示
    value_text = f"{value:.1f}"
    cv2.putText(frame, value_text, (gauge_x + gauge_width + 10, y_pos + gauge_height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def analyze_readability(frame, barcodes):
    """
    フレームを分析し、バーコードが読み取れない原因を推定する。
    各項目のリアルタイム値とステータスを含む辞書を返す。
    """
    analysis_results = {} # Initialize analysis_results here
    primary_issue_text = "Scanning... (Center the barcode)"
    primary_issue_color = (255, 255, 255) # White

    # 1. グレースケールに変換
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. ぼやけ具合を分析 (ラプラシアン分散)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    focus_status = 'ok'
    if laplacian_var < FOCUS_THRESHOLD:
        focus_status = 'low'
        primary_issue_text = f"Focus is off (Value: {laplacian_var:.2f})"
        primary_issue_color = (0, 0, 255) # Red
    analysis_results['Focus'] = {'value': laplacian_var, 'status': focus_status}

    # 3. 明るさを分析 (平均輝度)
    mean_brightness = np.mean(gray)
    brightness_status = 'ok'
    if mean_brightness < BRIGHTNESS_TOO_DARK_THRESHOLD:
        brightness_status = 'low'
        primary_issue_text = f"Too dark (Value: {mean_brightness:.2f})"
        primary_issue_color = (0, 165, 255) # Orange
    elif mean_brightness > BRIGHTNESS_TOO_BRIGHT_THRESHOLD:
        brightness_status = 'high'
        primary_issue_text = f"Too bright (Value: {mean_brightness:.2f})"
        primary_issue_color = (0, 255, 255) # Yellow
    analysis_results['Brightness'] = {'value': mean_brightness, 'status': brightness_status}

    # 4. pyzbarでバーコードの位置だけを検出してみる
    barcode_area = 0
    size_status = 'na' # Not Applicable
    if barcodes:
        # 最初のバーコードのサイズを分析
        (x, y, w, h) = barcodes[0].rect
        barcode_area = w * h
        size_status = 'ok'
        if barcode_area < SIZE_TOO_SMALL_THRESHOLD:
            size_status = 'low'
            primary_issue_text = f"Barcode too far (Size: {barcode_area})"
            primary_issue_color = (255, 255, 0) # Cyan
        elif barcode_area > SIZE_TOO_LARGE_THRESHOLD:
            size_status = 'high'
            primary_issue_text = f"Barcode too close (Size: {barcode_area})"
            primary_issue_color = (255, 0, 255) # Magenta
    else: # No barcode region detected at all by pyzbar
        primary_issue_text = "No barcode detected"
        primary_issue_color = (128, 128, 128) # Gray
    analysis_results['Size'] = {'value': barcode_area, 'status': size_status}

    return primary_issue_text, primary_issue_color, analysis_results
def run_test(config_instance):
    # --- ロギング設定 ---
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, "readability_log.csv")
    log_header = [
        "timestamp", "result", "barcode_data",
        "focus_value", "brightness_value", "size_value", "primary_issue"
    ]
    # ファイルがなければヘッダーを書き込む
    file_exists = os.path.exists(log_filename)
    log_file = open(log_filename, 'a', newline='', encoding='utf-8')
    log_writer = csv.writer(log_file)
    if not file_exists:
        log_writer.writerow(log_header)


    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open camera (index: {CAMERA_INDEX}).")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    print("Starting barcode readability test. Press 'q' to quit.")

    last_success_time = 0
    COOLDOWN_PERIOD = 1.0 # 読み取り成功後のクールダウン時間（秒）

    ok_count = 0
    ng_count = 0
    
    last_ng_check_time = 0
    NG_CHECK_INTERVAL = 1.0 # NG判定を行う間隔（秒）

    # ピークホールド用の辞書
    peak_values = {
        'Focus': {'value': 0, 'timestamp': 0},
        'Brightness': {'value': 0, 'timestamp': 0},
        'Size': {'value': 0, 'timestamp': 0}
    }
    PEAK_HOLD_DURATION = 1.5 # ピーク値を保持する時間（秒）

    # 2値化ウィンドウ用の設定
    last_binary_update_time = 0
    BINARY_UPDATE_INTERVAL = 0.5 # 0.5秒ごとに更新 (1秒に2回)
    last_binary_frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH), dtype=np.uint8) # 初期フレーム

    # 自動分析用のデータ収集状況
    analysis_data_ready = False
    collected_data_types = set()

    # トータルOKカウント用の変数
    total_ok_count = 0
    
    # ユニークなバーコードを保存するためのセット
    scanned_unique_barcodes = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not get frame from camera.")
            break

        # --- 2値化ウィンドウの表示 ---
        current_time_for_update = time.time()
        if current_time_for_update - last_binary_update_time > BINARY_UPDATE_INTERVAL:
            last_binary_update_time = current_time_for_update
            gray_for_binary = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 適応的閾値処理を使用して2値化
            last_binary_frame = cv2.adaptiveThreshold(
                gray_for_binary, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 2
            )
        cv2.imshow("Binarized View", last_binary_frame)

        # --- ガイドボックスの計算と描画 ---
        # 目標となるバーコードの面積を計算
        target_area = (SIZE_TOO_SMALL_THRESHOLD + SIZE_TOO_LARGE_THRESHOLD) / 2
        aspect_ratio = 3.0  # バーコードの一般的なアスペクト比 (幅/高さ)
        guide_height = int(np.sqrt(target_area / aspect_ratio))
        guide_width = int(guide_height * aspect_ratio)
        # 画面中央にガイドボックスを描画
        center_x, center_y = CAMERA_WIDTH // 2, CAMERA_HEIGHT // 2
        guide_x1 = center_x - guide_width // 2
        guide_y1 = center_y - guide_height // 2
        guide_x2 = center_x + guide_width // 2
        guide_y2 = center_y + guide_height // 2
        # ガイドボックスとテキストを描画
        cv2.rectangle(frame, (guide_x1, guide_y1), (guide_x2, guide_y2), (255, 255, 255), 2)
        cv2.putText(frame, "Align barcode here", (guide_x1, guide_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # --- 常にバーコード検出を試み、検出された領域を描画 ---
        # 読み取り成否に関わらず、バーコードとして検出された領域を取得
        all_detected_barcodes = decode(frame)
        
        # 検出されたがデコードに失敗した領域を黄色で描画
        for barcode in all_detected_barcodes:
            pts = np.array([(p.x, p.y) for p in barcode.polygon], dtype=np.int32)
            hull = cv2.convexHull(pts)
            cv2.polylines(frame, [hull], isClosed=True, color=(0, 255, 255), thickness=2) # 黄色

        # pyzbarでバーコードをデコード
        current_time = time.time()
        
        # クールダウン期間中はデコード処理をスキップ
        if current_time - last_success_time < COOLDOWN_PERIOD:
            decoded_objects = []
        else:
            decoded_objects = decode(frame)

        status_text = ""
        status_color = (0, 255, 0) # デフォルトは緑 (成功)

        if decoded_objects:
            # 読み取り成功
            for obj in decoded_objects:
                total_ok_count += 1 # トータルOKを積算
                barcode_data = obj.data.decode("utf-8")
                # 新しいユニークなバーコードの場合のみOKカウントを増やす
                if barcode_data not in scanned_unique_barcodes:
                    ok_count += 1
                    scanned_unique_barcodes.add(barcode_data)
                last_success_time = current_time # 成功時刻を更新
                # 読み取った情報を描画
                points = obj.polygon
                if len(points) > 4:
                    # 座標リストを正しい形式 (N, 2) のNumpy配列に変換
                    pts = np.array([(p.x, p.y) for p in points], dtype=np.int32)
                    hull = cv2.convexHull(pts)
                    cv2.polylines(frame, [hull], isClosed=True, color=(0, 255, 0), thickness=2)
                
                barcode_type = obj.type
                status_text = f"OK: {barcode_data} ({barcode_type})"
                print(f"Success: {status_text}")

                # OKログを記録
                # この時点での analysis_results は前のフレームのものなので、再計算する
                _, _, analysis_results = analyze_readability(frame, decoded_objects)
                collected_data_types.add('OK')
                log_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 'OK', barcode_data,
                    analysis_results['Focus']['value'], analysis_results['Brightness']['value'],
                    analysis_results['Size']['value'], 'N/A'
                ])
        else:
            # 読み取り失敗時の処理
            if all_detected_barcodes and (current_time - last_ng_check_time > NG_CHECK_INTERVAL):
                # バーコード領域は検出されたがデコードに失敗し、かつ前回のNGチェックから1秒以上経過した場合
                ng_count += 1 # NGカウントを1増やす
                last_ng_check_time = current_time # NGチェック時刻を更新
                status_text, status_color, analysis_results = analyze_readability(frame, all_detected_barcodes)

                # 収集したNGデータタイプを記録
                issue_for_log = status_text.split(' (')[0]
                if 'Focus is off' in issue_for_log:
                    collected_data_types.add('NG_Focus')
                elif 'too far' in issue_for_log:
                    collected_data_types.add('NG_TooFar')
                elif 'too close' in issue_for_log:
                    collected_data_types.add('NG_TooClose')

                # NGログを記録
                log_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 'NG', '',
                    analysis_results['Focus']['value'], analysis_results['Brightness']['value'],
                    analysis_results['Size']['value'], issue_for_log
                ])

            elif all_detected_barcodes:
                # バーコード領域は検出されたが、まだNGチェック間隔内
                status_text, status_color, analysis_results = analyze_readability(frame, all_detected_barcodes)
            else: # バーコード領域すら検出できなかった場合 (NGカウントは増やさない)
                status_text, status_color, analysis_results = analyze_readability(frame, all_detected_barcodes)

            # --- 右上にリアルタイム値とゲージを表示 ---
            current_time = time.time()

            # OK/NGカウントの表示
            cv2.putText(frame, f"OK: {total_ok_count}", (CAMERA_WIDTH - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"NG: {ng_count}", (CAMERA_WIDTH - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # --- OK率の計算と表示 ---
            total_attempts = total_ok_count + ng_count # トータルOK数で率を計算
            if total_attempts > 0:
                success_rate = (total_ok_count / total_attempts) * 100
                rate_text = f"Success Rate: {success_rate:.1f}%"
                # 成功率に応じて色を変更
                if success_rate >= 80:
                    rate_color = (0, 255, 0) # 緑
                elif success_rate >= 50:
                    rate_color = (0, 255, 255) # 黄
                else:
                    rate_color = (0, 0, 255) # 赤
            else:
                rate_text = "Success Rate: N/A"
                rate_color = (255, 255, 255) # 白
            cv2.putText(frame, rate_text, (CAMERA_WIDTH - 280, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, rate_color, 2)
            
            # ピーク値の更新とリセット
            for key, data in analysis_results.items():
                if data['value'] > peak_values[key]['value']:
                    peak_values[key]['value'] = data['value']
                    peak_values[key]['timestamp'] = current_time
                elif current_time - peak_values[key]['timestamp'] > PEAK_HOLD_DURATION:
                    peak_values[key]['value'] *= 0.9

            # 各項目のゲージを描画
            draw_gauge(frame, y_pos=90, label="Focus", value=analysis_results['Focus']['value'],
                       min_val=0, max_val=500, optimal_min=FOCUS_THRESHOLD, optimal_max=500,
                       peak_value=peak_values['Focus']['value'])

            draw_gauge(frame, y_pos=130, label="Brightness", value=analysis_results['Brightness']['value'],
                       min_val=0, max_val=255, optimal_min=BRIGHTNESS_TOO_DARK_THRESHOLD, optimal_max=BRIGHTNESS_TOO_BRIGHT_THRESHOLD,
                       peak_value=peak_values['Brightness']['value'])

            draw_gauge(frame, y_pos=170, label="Size", value=analysis_results['Size']['value'],
                       min_val=0, max_val=SIZE_TOO_LARGE_THRESHOLD * 1.2, optimal_min=SIZE_TOO_SMALL_THRESHOLD, optimal_max=SIZE_TOO_LARGE_THRESHOLD,
                       peak_value=peak_values['Size']['value'])

        # --- 中央上部にユニークOK数を表示 ---
        unique_count_text = str(ok_count) # 数字のみ
        (text_w, text_h), _ = cv2.getTextSize(unique_count_text, cv2.FONT_HERSHEY_SIMPLEX, 3, 5) # フォントを大きく
        text_x = (CAMERA_WIDTH - text_w) // 2
        text_y = (CAMERA_HEIGHT + text_h) // 2
        cv2.putText(frame, unique_count_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0, 128), 5, cv2.LINE_AA) # 半透明に

        # ステータステキストを画面に描画
        # テキストの背景に黒い矩形を描画して見やすくする
        (text_w, text_h), _ = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(frame, (10, CAMERA_HEIGHT - 40), (20 + text_w, CAMERA_HEIGHT - 40 + text_h + 10), (0,0,0), -1)
        cv2.putText(frame, status_text, (20, CAMERA_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)

        # --- 分析データ収集完了メッセージの表示 ---
        all_required_types = {'OK', 'NG_Focus', 'NG_TooFar', 'NG_TooClose'}
        if not analysis_data_ready and collected_data_types.issuperset(all_required_types):
            analysis_data_ready = True
        
        if analysis_data_ready:
            # 収集完了メッセージ
            ready_text = "Analysis data collected! Quit (q) and run with --analyze."
            (text_w, text_h), _ = cv2.getTextSize(ready_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (5, 5), (15 + text_w, 15 + text_h), (0, 80, 0), -1)
            cv2.putText(frame, ready_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 255, 128), 1)
        else:
            # 収集中メッセージ
            needed_types = all_required_types - collected_data_types
            type_names_en = {
                'OK': 'OK',
                'NG_Focus': 'NG Focus',
                'NG_TooFar': 'NG Too Far',
                'NG_TooClose': 'NG Too Close'
            }

            if needed_types == {'NG_Focus'}:
                # Focus NGだけが足りない場合、設定が最適である可能性を示唆
                optimal_text = "Focus setting seems optimal (NG Focus data not collected)"
                cv2.putText(frame, optimal_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1) # 水色で表示
            else:
                needed_names = [type_names_en[t] for t in sorted(list(needed_types))]
                collecting_text = f"Collecting data... (Needed: {', '.join(needed_names)})"
                cv2.putText(frame, collecting_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1) # 黄色で表示

        cv2.imshow("Barcode Readability Tester", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27: # 'q' または ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    log_file.close() # ファイルを閉じる
    print("Test finished.")

def analyze_logs():
    """
    readability_log.csv を解析して、最適なパラメータを推奨する。
    """
    log_filename = os.path.join("log", "readability_log.csv")
    if not os.path.exists(log_filename):
        print(f"Error: Log file '{log_filename}' not found.")
        print("Please run the test first to collect log data.")
        return

    ok_data = {'focus': [], 'size': []}
    ng_data = {'focus_off': [], 'too_far': [], 'too_close': []}
    ok_count = 0
    ng_count = 0

    with open(log_filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                focus = float(row['focus_value'])
                size = float(row['size_value'])

                if row['result'] == 'OK':
                    ok_count += 1
                    ok_data['focus'].append(focus)
                    ok_data['size'].append(size)
                elif row['result'] == 'NG':
                    ng_count += 1
                    issue = row['primary_issue']
                    if 'Focus is off' in issue:
                        ng_data['focus_off'].append(focus)
                    elif 'too far' in issue:
                        ng_data['too_far'].append(size)
                    elif 'too close' in issue:
                        ng_data['too_close'].append(size)
            except (ValueError, KeyError):
                continue # 不正な行はスキップ

    print("\n--- Log Analysis Results ---")
    print(f"Analyzing log: {log_filename} (OK: {ok_count}, NG: {ng_count})\n")

    if ok_count < 10:
        print("Warning: Less than 10 successful (OK) logs. Accuracy will improve with more success data.")

    # --- 最適な閾値の計算 ---
    # FOCUS_THRESHOLD: 成功したフォーカス値の最小値と、フォーカス失敗時の最大値の中間点を推奨
    recommended_focus_threshold = FOCUS_THRESHOLD # デフォルト値
    if ok_data['focus'] and ng_data['focus_off']:
        min_ok_focus = min(ok_data['focus'])
        max_ng_focus = max(ng_data['focus_off'])
        if min_ok_focus > max_ng_focus:
            recommended_focus_threshold = (min_ok_focus + max_ng_focus) / 2
    elif ok_data['focus']:
        recommended_focus_threshold = min(ok_data['focus']) * 0.95 # 成功最小値の95%

    # SIZE_TOO_SMALL_THRESHOLD: 成功したサイズの最小値と、「遠すぎる」NGの最大値の中間点
    recommended_size_small_threshold = SIZE_TOO_SMALL_THRESHOLD
    if ok_data['size'] and ng_data['too_far']:
        min_ok_size = min(s for s in ok_data['size'] if s > 0)
        max_ng_size_far = max(ng_data['too_far'])
        if min_ok_size > max_ng_size_far:
            recommended_size_small_threshold = (min_ok_size + max_ng_size_far) / 2

    # SIZE_TOO_LARGE_THRESHOLD: 成功したサイズの最大値と、「近すぎる」NGの最小値の中間点
    recommended_size_large_threshold = SIZE_TOO_LARGE_THRESHOLD
    if ok_data['size'] and ng_data['too_close']:
        max_ok_size = max(ok_data['size'])
        min_ng_size_close = min(ng_data['too_close'])
        if max_ok_size < min_ng_size_close:
            recommended_size_large_threshold = (max_ok_size + min_ng_size_close) / 2

    # 現在の設定値と推奨値を比較
    is_focus_optimal = abs(FOCUS_THRESHOLD - recommended_focus_threshold) < 5.0
    is_size_small_optimal = abs(SIZE_TOO_SMALL_THRESHOLD - recommended_size_small_threshold) < 500
    is_size_large_optimal = abs(SIZE_TOO_LARGE_THRESHOLD - recommended_size_large_threshold) < 2000

    # --- 結果の表示と設定ファイルの更新 ---
    if is_focus_optimal and is_size_small_optimal and is_size_large_optimal:
        print("【Analysis Result】\n")
        print("Current settings are already optimal based on the collected log data.")
        print("No parameter changes are necessary at this time.\n")
    else:
        print("【Auto-Tuning Result】\n")
        print("Optimal parameters have been calculated and saved to config.json.\n")

        # 更新前の値を表示
        print(f"Focus Threshold:      {FOCUS_THRESHOLD:.1f} -> {recommended_focus_threshold:.1f}")
        print(f"Size Threshold (Small): {SIZE_TOO_SMALL_THRESHOLD} -> {int(recommended_size_small_threshold)}")
        print(f"Size Threshold (Large): {SIZE_TOO_LARGE_THRESHOLD} -> {int(recommended_size_large_threshold)}\n")

        # config.jsonに自動保存
        current_tester_settings = config.get("readability_tester_settings", {})
        current_tester_settings['focus_threshold'] = round(recommended_focus_threshold, 1)
        current_tester_settings['size_too_small_threshold'] = int(recommended_size_small_threshold)
        current_tester_settings['size_too_large_threshold'] = int(recommended_size_large_threshold)
        config.set("readability_tester_settings", current_tester_settings)
        config.save_config()
        print("Settings have been updated automatically for the next run.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--analyze':
        analyze_logs()
    else:
        run_test(config)
        print("\n--- Auto Log Analysis Start ---")
        analyze_logs()