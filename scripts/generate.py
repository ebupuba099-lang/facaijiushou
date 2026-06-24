#!/usr/bin/env python3
"""发财就手 - 每日生成新一期8级递减序列"""
import random
from datetime import datetime
from common import DATA_FILE, load_data, save_data, commit_to_github

MAX_RECORDS = 50

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

if __name__ == "__main__":
    main()
