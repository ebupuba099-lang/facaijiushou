#!/usr/bin/env python3
"""发财就手 - 每日生成新一期8级递减序列"""
import json, os, random
from datetime import datetime

DATA_FILE = "data/lottery_data.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
MAX_RECORDS = 50

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
    # 但如果最新期超过2天还没开奖（API持续失败），也继续生成避免永久卡死
    if not latest_record.get("winning"):
        now_ts = int(datetime.now().timestamp() * 1000)
        stale_ms = now_ts - data.get("lastUpdate", 0)
        if stale_ms < 2 * 24 * 3600 * 1000:
            print(f"最新期 {latest_period} 还未开奖（{stale_ms/3600000:.1f}小时前更新），今天不生成新一期")
            return
        else:
            print(f"最新期 {latest_period} 超过2天未开奖，跳过继续生成下一期")

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
    """通过 git commit + push 提交，避免 API 直接写文件导致的冲突"""
    import subprocess
    if not REPO or not GH_TOKEN:
        print("无GH_TOKEN，跳过提交")
        return

    try:
        repo_url = f"https://x-access-token:{GH_TOKEN}@github.com/{REPO}.git"
        subprocess.run(["git", "config", "user.name", "发财就手Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@facaijiushou.local"], check=True)

        # 先 pull 确保同步
        subprocess.run(["git", "pull", "--rebase", repo_url, "main"], check=True, capture_output=True)

        # add + commit + push
        subprocess.run(["git", "add", DATA_FILE], check=True)
        result = subprocess.run(["git", "commit", "-m", message], capture_output=True)
        if b"nothing to commit" in result.stdout + result.stderr:
            print("无变更，跳过提交")
            return

        subprocess.run(["git", "push", repo_url, "main"], check=True)
        print(f"已提交到GitHub: {message}")
    except subprocess.CalledProcessError as e:
        print(f"Git操作失败: {e}")
        if e.stderr:
            print(f"  stderr: {e.stderr.decode()[:500]}")

if __name__ == "__main__":
    main()
