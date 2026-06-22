#!/usr/bin/env python3
"""发财就手 - 每日生成新一期8级递减序列"""
import json, os, random, base64
from datetime import datetime

DATA_FILE = "data/lottery_data.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
MAX_RECORDS = 20

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": [], "lastUpdate": 0}

def save_data(data):
    data["lastUpdate"] = int(datetime.now().timestamp() * 1000)
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_levels():
    """从0-9中随机选8个，逐级随机去掉1个"""
    digits = list(range(10))
    random.shuffle(digits)
    selected = digits[:8]
    levels = [selected[:]]
    current = selected[:]
    for _ in range(7):
        remove_idx = random.randint(0, len(current) - 1)
        current = [d for i, d in enumerate(current) if i != remove_idx]
        levels.append(current[:])
    return levels

def main():
    data = load_data()

    # 从本地数据获取最新期号，+1生成下一期
    if not data["records"]:
        print("无历史数据，无法生成")
        return

    latest_record = data["records"][-1]
    latest_period = int(latest_record["period"])

    # 只有当最新期已开奖，才生成下一期
    if not latest_record.get("winning"):
        print(f"最新期 {latest_period} 还未开奖，今天不生成新一期")
        return

    next_period = str(latest_period + 1)

    # 检查是否已生成
    existing_periods = [r["period"] for r in data["records"]]
    if next_period in existing_periods:
        print(f"期 {next_period} 已存在，跳过")
        return

    # 生成4个位置的8级递减序列
    positions = ["head", "hundred", "ten", "tail"]
    sequences = {pos: generate_levels() for pos in positions}

    new_record = {
        "period": next_period,
        "sequences": sequences,
        "winning": "",
        "hits": {}
    }

    data["records"].append(new_record)

    # 限制最多MAX_RECORDS条（保留最新的）
    if len(data["records"]) > MAX_RECORDS:
        data["records"] = data["records"][-MAX_RECORDS:]

    save_data(data)
    print(f"已生成期 {next_period}")

    # 提交到GitHub
    commit_to_github(f"生成{next_period}期8级递减序列")

def commit_to_github(message):
    if not REPO or not GH_TOKEN:
        print("无GH_TOKEN，跳过提交")
        return

    api = f"https://api.github.com/repos/{REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 获取当前SHA
    req = urllib.request.Request(api, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            sha = json.loads(resp.read())["sha"]
    except:
        sha = None

    # 读取文件内容
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    body = json.dumps({
        "message": message,
        "content": encoded,
        "sha": sha
    })

    req = urllib.request.Request(api, data=body.encode("utf-8"), headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"已提交到GitHub: {message}")
    except urllib.error.HTTPError as e:
        print(f"提交失败: {e.code} {e.read().decode()}")

if __name__ == "__main__":
    main()
