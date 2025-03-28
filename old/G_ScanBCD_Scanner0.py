#G_ScanBCD_Scanner.py
import sys
sys.stdout.reconfigure(encoding='utf-8')

import cv2
import time
import csv
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime

class BarcodeScanner:
    def __init__(self, scan_log, expected_length, location, construction_number, config):
        self.scan_log = scan_log
        self.expected_length = expected_length
        self.location = location
        self.construction_number = construction_number
        self.barcode_data = []
        self.scan_count = 0
        self.scanned_info = []
        self.display_time = config.get("display_time", 3)
        self.config = config

    def start(self, auto_stop=True):
        cap = cv2.VideoCapture(self.config.get("camera_index", 0))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.get("camera_width", 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.get("camera_height", 480))

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            barcodes = decode(frame)
            self.display_scan_result(frame, barcodes)

            for barcode in barcodes:
                barcode_info = barcode.data.decode('utf-8')
                barcode_type = barcode.type
                if len(barcode_info) == self.expected_length and barcode_info not in self.barcode_data:
                    self.barcode_data.append(barcode_info)
                    self.scan_count += 1
                    self.write_to_csv(barcode_info, barcode_type)
                    print(f"Scanned Barcode: {barcode_info} Type: {barcode_type}")

                    self.scanned_info.append({
                        'barcode': barcode_info,
                        'type': barcode_type,
                        'timestamp': time.time()
                    })

            self.remove_expired_info()

            cv2.imshow('Barcode Scanner', frame)

            if auto_stop and len(self.barcode_data) >= self.expected_length:
                break

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def display_scan_result(self, frame, barcodes):
        height, width, _ = frame.shape
        overlay_x = 10
        overlay_y = 30

        text_mapping = self.config.get("display_text_mapping", {})
        display_location = text_mapping.get(self.location, self.location)
        spec_text = f"Type: {self.config.get('barcode_type', 'CODE39')} | Digits: {self.expected_length} | Location: {display_location} | Construction: {self.construction_number}"

        font_scale = self.config.get("font_scale", 0.6)
        display_lines = self.config.get("display_lines", 1)

        if display_lines == 1:
            cv2.putText(frame, spec_text, (overlay_x, overlay_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            spec_text_lines = spec_text.split(" | ")
            for i, line in enumerate(spec_text_lines):
                if i < display_lines:
                    cv2.putText(frame, line, (overlay_x, overlay_y + i * 20), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 0, 255), 2, cv2.LINE_AA)

        barcode_count = len(barcodes)
        scan_text = f"Scans: {self.scan_count}"
        cv2.putText(frame, scan_text, (width - 200, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

        for info in self.scanned_info:
            barcode_info = info['barcode']
            barcode_type = info['type']
            timestamp = info['timestamp']

            if time.time() - timestamp <= self.display_time:
                text = f"{barcode_info} ({barcode_type})"
                cv2.putText(frame, text, (overlay_x, overlay_y + display_lines * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
                overlay_y += 20

            if time.time() - timestamp > self.display_time:
                self.scanned_info = [info for info in self.scanned_info if time.time() - info['timestamp'] <= self.display_time]

        for barcode in barcodes:
            rect_points = barcode.polygon
            if len(rect_points) == 4:
                pts = np.array(rect_points, dtype=np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            else:
                x, y, w, h = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.imshow('Barcode Scanner', frame)

    def remove_expired_info(self):
        current_time = time.time()
        self.scanned_info = [info for info in self.scanned_info if current_time - info['timestamp'] <= self.display_time]

    def write_to_csv(self, barcode_info, barcode_type):
        try:
            with open(self.scan_log, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([barcode_info, barcode_type, self.location, self.construction_number, self.get_current_timestamp()])
        except Exception as e:
            print(f"⚠ CSV書き込みエラー: {e}")

    def get_current_timestamp(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

if __name__ == "__main__":
    from G_config import Config
    config = Config("config.json")
    scanner = BarcodeScanner(scan_log="scanned_barcodes.csv", expected_length=10, location="Kabuto 1F", construction_number="1234", config=config)
    scanner.start(auto_stop=True)