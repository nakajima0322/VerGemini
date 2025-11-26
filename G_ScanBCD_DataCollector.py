# G_ScanBCD_DataCollector.py
# データ収集クラス
class G_ScanBCD_DataCollector:
    def collect(self, barcode_info, barcode_type, timestamp, location, construction_number, worker_name):
        # データを収集し、適切なデータ構造に格納
        data = {
            "barcode_info": barcode_info,
            "construction_number": construction_number,
            "location": location,
            "barcode_type": barcode_type,
            "timestamp": timestamp,
            "worker_name": worker_name,
        }
        return data
