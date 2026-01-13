#   G_config.py
import json


class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(
                f"設定ファイル {self.config_file} が見つかりませんでした。デフォルト設定を使用します。"
            )
            return {}
        except json.JSONDecodeError:
            print(
                f"設定ファイル {self.config_file} の形式が不正です。デフォルト設定を使用します。"
            )
            return {}

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"設定ファイル {self.config_file} の保存に失敗しました: {e}")


if __name__ == "__main__":
    config = Config()
    print(config.get("locations", ["デフォルト場所1", "デフォルト場所2"]))
    config.set("test_key", "test_value")
    print(config.get("test_key"))
