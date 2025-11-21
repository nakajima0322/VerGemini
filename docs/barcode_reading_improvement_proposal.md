# バーコード読取精度向上のための改善案

## 概要

`G_ScanBCD_Analyzer.py` におけるバーコードの解析処理を改善し、読取精度を向上させるための提案です。
現在の実装は、画像をグレースケールに変換して `pyzbar` で解析する基本的なものですが、照明が不均一な環境や、印刷が不鮮明なバーコードでは認識に失敗することがあります。

そこで、OpenCVを用いた高度な画像前処理を導入することで、より堅牢なバーコード読み取りを目指します。

## 提案内容

以下の2つの画像処理技術を導入し、`config.json` で機能をON/OFFできるようにします。

1. **適応的閾値処理 (Adaptive Thresholding)**
    * 画像の局所的な明るさに応じて二値化を行う手法です。画像全体の明るさが均一でない場合でも、バーコードの線をより明確に抽出できます。

2. **形態学的変換 (Morphological Transformations)**
    * オープニング処理でバーコード以外の微細なノイズを除去し、クロージング処理でバーコードの線が途切れている部分を補完します。これにより、`pyzbar` の認識率を高める効果が期待できます。

## 実装コード案

### `G_ScanBCD_Analyzer.py` の変更案

`analyze` メソッドを以下のように変更します。

```python
# G_ScanBCD_Analyzer.py

import cv2
import numpy as np
from pyzbar.pyzbar import decode

class G_ScanBCD_Analyzer:
    def __init__(self, config):
        self.config = config
        self.use_advanced_processing = self.config.get("use_advanced_barcode_processing", False)
        print("\nバーコード解析開始...")
        if self.use_advanced_processing:
            print("INFO: 高度なバーコード解析処理が有効です。")

    def analyze(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)

        if not barcodes and self.use_advanced_processing:
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=1)
            barcodes = decode(closing)

        return barcodes, image
```

### `config.json` の変更案

`___ACTIVE_SETTINGS___` の直下に以下の設定項目を追加します。`true` にすることで、上記の前処理が有効になります。

```json
{
    "___ACTIVE_SETTINGS___": "--- 現在有効な設定 ---",
    "use_advanced_barcode_processing": false,
    ...
}
```
