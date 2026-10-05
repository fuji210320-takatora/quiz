import json
import os
import socket

# データの保存先
QUIZ_FILE = "quizzes.json"
STATE_FILE = "game_state.json"

def load_json(filepath, default_data):
    if not os.path.exists(filepath):
        return default_data
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default_data

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 自分のPCのローカルIPを取得する関数（QRコード作成用）
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
