#!/usr/bin/env python3
"""发财就手 - 公共工具函数"""
import json, os, subprocess
from datetime import datetime

DATA_FILE = "data/lottery_data.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": [], "lastUpdate": 0}


def save_data(data, is_generate=False):
    data["lastUpdate"] = int(datetime.now().timestamp() * 1000)
    # 如果是生成操作，记录首次检测到未开奖的时间（不覆盖已有的）
    if is_generate and "lastGenerateAttempt" not in data:
        data["lastGenerateAttempt"] = data["lastUpdate"]
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def commit_to_github(message):
    """通过 git commit + push 提交，避免 API 直接写文件导致的冲突"""
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
