# G_ScanBCD_Overlay.py
import cv2
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class OverlayDisplay:
    # 要求される設定値のキー
    REQUIRED_KEYS = {
        "font_scale",
        "display_lines",
        "overlay_alpha",
        "overlay_color",
        "display_text_mapping",
        "display_time",
        "barcode_type",
        "expected_length",
        "japanese_font_path", # 日本語フォントパスを追加
    }

    def __init__(self, config):
        self.config = config
        self.scanned_info = []  # scanned_infoをインスタンス変数として保持
        self.last_seen = {}  # バーコードの最終検出時間と位置を記録
        self.detection_timeout = 1.0  # 検出が途切れてから矩形を消すまでの時間
        self.font = None # 日本語フォントを保持する変数
        self.font_large = None # 強調表示用の大きなフォント
        self.frame_count = 0 # デバッグ用フレームカウンタ
        self.last_debug_info = None # デバッグ情報の変更検知用

        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if self.config.get(key) is None:
                missing_keys.append(key)
        if missing_keys:
            raise ValueError(f"設定ファイルに以下のキーが存在しません: {', '.join(missing_keys)}")
        
        # 日本語フォントの読み込み
        try:
            font_path = self.config.get("japanese_font_path")
            font_size = int(self.config.get("font_scale", 0.5) * 32) # font_scaleからサイズを計算
            self.font = ImageFont.truetype(font_path, font_size)
            self.font_large = ImageFont.truetype(font_path, int(font_size * 2.0)) # 2倍サイズのフォントを作成
        except IOError:
            print(f"警告: 指定された日本語フォント '{font_path}' が見つかりません。日本語表示が文字化けします。")
            self.font = None # フォントが見つからない場合はNoneのまま
            self.font_large = None

    def _get_japanese_text_size(self, text):
        """Pillowフォントを使ってテキストの描画サイズを取得する"""
        if self.font:
            try:
                # getlengthはより正確な幅を返す。高さはgetbboxで取得。
                width = self.font.getlength(text) # 幅はgetlengthを使用
                # 高さはbboxから取得するが、topがマイナスになることがあるため、bottomをそのまま高さとして扱う
                # left, rightは幅の計算に使用しない
                _, top, _, bottom = self.font.getbbox(text)
                height = bottom - top # topを考慮した高さを計算
                return width, height
            except AttributeError: # 古いPillowバージョン対策 (getlengthがない場合)
                # getsizeは非推奨だがフォールバックとして残す
                return self.font.getsize(text)
        else:
            (width, height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, self.config.get("font_scale"), 2)
            return width, height

    def _draw_japanese_text(self, frame, text, position, color):
        """Pillowを使用して日本語テキストをフレームに描画する"""
        if not self.font:
            # フォントがない場合は、OpenCVの英数字用関数で代替（文字化けする）
            cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, self.config.get("font_scale"), color, 2, cv2.LINE_AA)
            return frame

        # OpenCVのBGR形式からPillowのRGB形式に変換
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        draw.text(position, text, font=self.font, fill=color, stroke_width=0, stroke_fill=color)
        # PillowのRGB形式からOpenCVのBGR形式に戻す
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    def _draw_text_with_pil(self, draw, text, position, color, stroke_width=0, font=None):
        """
        PillowのDrawオブジェクトにテキストを描画するヘルパー関数。
        フォントの有無をチェックする。
        """
        use_font = font if font else self.font
        if use_font:
            draw.text(position, text, font=use_font, fill=color, stroke_width=stroke_width, stroke_fill=color)
        else:
            # フォントがない場合、描画をスキップ（またはOpenCVでの代替描画も可能だが、ここでは何もしない）
            print(f"警告: Pillowフォントが未設定のため、テキスト '{text}' は描画されません。")

    def display_overlay(
            self,
            frame,
            barcodes,
            scan_count,
            success_count,
            failure_count,
            duplicate_count,
            context_label, # 引数名を汎用的に変更
            construction_number,
            remaining_time,
            barcode_type,
            expected_length):

        height = self.config.get("camera_height", 480)
        width = self.config.get("camera_width", 640)
        overlay_x = 30
        overlay_y = 30

        # --- 描画処理の開始前に一度だけ画像形式を変換 ---
        # OpenCV(BGR) -> Pillow(RGBA) へ変換。アルファチャンネルを扱うためRGBAにする。
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        # ベースとなる描画用レイヤーを作成
        draw = ImageDraw.Draw(img_pil)

        text_mapping = self.config.get("display_text_mapping")
        
        # 呼び出し元で整形された文字列をそのまま使用する
        spec_text = f"Type: {self.config.get('barcode_type')} | Digits: {self.config.get('expected_length')} | {context_label} | 工事番号: {construction_number}"

        font_scale = self.config.get("font_scale")
        display_lines = self.config.get("display_lines")

        # テキストを改行で分割
        spec_text_lines = spec_text.split(" | ")

        # --- 左上情報エリアの背景サイズ計算 ---
        line_heights = []
        max_text_width = 0 # このブロックで使う最大幅
        for line in spec_text_lines:
            text_w, text_h = self._get_japanese_text_size(line)
            max_text_width = max(max_text_width, text_w)
            line_heights.append(text_h)

        line_spacing = 10
        total_text_height = sum(line_heights) + line_spacing * (len(line_heights) - 1)

        # 背景の描画範囲を調整
        padding_x = 10
        padding_y = 10
        background_left = overlay_x - padding_x
        background_top = overlay_y - padding_y
        background_right = int(overlay_x + max_text_width + padding_x)
        background_bottom = int(overlay_y + total_text_height + padding_y)

        # --- 半透明の背景とテキストを描画 ---
        # 1. 半透明の背景用の別レイヤーを作成
        alpha = self.config.get("overlay_alpha")
        overlay_color = self.config.get("overlay_color")
        alpha_int = int(alpha * 255)
        overlay_img = Image.new('RGBA', img_pil.size, (255, 255, 255, 0)) # 全体が透明なレイヤー
        draw_overlay = ImageDraw.Draw(overlay_img)

        # 2. 背景レイヤーに半透明の四角形を描画
        draw_overlay.rectangle(
            (background_left, background_top, background_right, background_bottom),
            fill=tuple(overlay_color) + (alpha_int,)
        )

        # 3. テキストを背景レイヤーの上に描画
        for i, line in enumerate(spec_text_lines):
            current_y = overlay_y + sum(line_heights[:i]) + line_spacing * i
            self._draw_text_with_pil(draw_overlay, line, (overlay_x, current_y), (255, 255, 255, 255), stroke_width=0)

        # 4. ベース画像に背景とテキストが描画されたレイヤーを合成
        img_pil = Image.alpha_composite(img_pil, overlay_img)
        # 再度描画するためにDrawオブジェクトを再生成
        draw = ImageDraw.Draw(img_pil)

        # --- スキャン済みリストの表示 (位置を修正) ---
        # 左上の情報表示エリアのすぐ下に表示する
        scanned_list_y = background_bottom + 20
        for info in self.scanned_info:  # インスタンス変数から参照
            barcode_info = info['barcode']
            barcode_type = info['type']
            timestamp = info['timestamp']

            if time.time() - timestamp <= self.config.get("display_time"):
                text = f"Scanned: {barcode_info} ({barcode_type})"
                self._draw_text_with_pil(draw, text, (overlay_x, scanned_list_y), (0, 255, 0), stroke_width=1)
                scanned_list_y += 25 # 次の行へ

        # 古いスキャン情報をリストから削除
        self.scanned_info[:] = [info for info in self.scanned_info if time.time() - info['timestamp'] <= self.config.get("display_time")]

        # --- バーコードの矩形と情報の描画 --- 
        current_time = time.time()

        # 現フレームで検出されたバーコードでlast_seenを更新
        for barcode in barcodes:
            barcode_info_str = barcode.data.decode('utf-8')
            self.last_seen[barcode_info_str] = {'barcode': barcode, 'timestamp': current_time}

        # last_seenにあるバーコードを描画（色分けしつつ）
        to_remove = []
        for barcode_info, seen_data in self.last_seen.items():
            elapsed_time = current_time - seen_data['timestamp']

            if elapsed_time > self.detection_timeout:
                to_remove.append(barcode_info)
                continue

            # 時間経過で色を決定
            if elapsed_time < 0.2:
                color = (0, 255, 0)  # 緑
            elif elapsed_time < 0.5:
                color = (0, 255, 255) # 黄
            else:
                color = (0, 0, 255)  # 赤

            barcode_obj = seen_data['barcode']
            
            # 矩形を描画
            rect_points = barcode_obj.polygon
            if len(rect_points) == 4:
                pts = np.array(rect_points, dtype=np.int32).reshape((-1, 1, 2))
            else:
                x, y, w, h = barcode_obj.rect
                pts = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.int32).reshape((-1, 1, 2))

            # Pillowで矩形を描画
            draw.polygon([tuple(p) for p in pts.reshape(-1, 2)], outline=color, width=2)

            # テキストを描画
            text = f"{barcode_info} ({barcode_obj.type})"
            text_w, text_h = self._get_japanese_text_size(text) # Pillowフォントでサイズ取得
            text_pos = (pts[0][0][0], pts[0][0][1] - text_h - 15)
            draw.rectangle((text_pos[0], text_pos[1], text_pos[0] + text_w, text_pos[1] + text_h + 5), fill=color)
            self._draw_text_with_pil(draw, text, (text_pos[0], text_pos[1] - 2), (0, 0, 0), stroke_width=0)

        # タイムアウトしたバーコードを辞書から削除
        for key in to_remove:
            del self.last_seen[key]
        
        # --- 画面右下にカウント情報を描画 --- (再有効化)
        # Pillowフォントを使用するため、OpenCVのフォント設定は不要
        line_height = 28 # 行間を少し広げる
        start_x = width - 220 # 右端からのオフセット
        start_y = height - 140 # 表示項目が増えたため開始位置を上に調整
        
        # --- データ取り込み数（成功数）を大きく表示 ---
        # カウント群の上に表示する
        self._draw_text_with_pil(draw, f"Data: {success_count}", (start_x, start_y - 60), (255, 0, 0), stroke_width=2, font=self.font_large)

        # Pillowで描画するため、一度に描画するテキストリストを作成
        count_texts_with_colors = [
            (f"Scans: {scan_count}", (0, 255, 0)),          # 緑
            (f"Success: {success_count}", (0, 255, 0)),     # 緑
            (f"Failure: {failure_count}", (0, 255, 0)),     # 緑
            (f"Duplicates: {duplicate_count}", (0, 255, 0)), # 緑
            (f"Time left: {int(remaining_time)}s", (0, 255, 0)) # 緑
        ]
        
        for i, (text, color) in enumerate(count_texts_with_colors):
            self._draw_text_with_pil(draw, text, (start_x, start_y + i * line_height), color, stroke_width=0)

        # --- すべての描画が完了したので、一度だけ画像形式を戻す ---
        # RGBA -> BGR
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGBA2BGR)

        return frame
