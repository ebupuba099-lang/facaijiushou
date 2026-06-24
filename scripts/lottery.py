#!/usr/bin/env python3
"""发财就手 - 抓取开奖结果并计算粒数"""
import json, os, ssl, time, urllib.request, urllib.error, subprocess
from datetime import datetime

DATA_FILE = "data/lottery_data.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

API_SPORTTERY = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=10&is11=0"
API_HUINIAO = "https://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=10"
API_CJCP = "https://www.cjcp.com.cn/ajax/lottery/history?lotteryId=85&pageSize=10&pageNo=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.lottery.gov.cn/",
}

# 创建不验证SSL的context（GitHub Actions环境有时SSL证书有问题）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

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

def calculate_hit(levels, draw_digit):
    """计算粒数：开奖数字最后出现在第几级，该级剩余个数=粒数"""
    if draw_digit not in levels[0]:
        return 0
    last_level = 0
    for i in range(len(levels)):
        if draw_digit in levels[i]:
            last_level = i
        else:
            break
    return len(levels[last_level])

def _request(url, timeout=15):
    """带重试的HTTP请求"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  请求失败(第{attempt+1}次): {e}")
            if attempt < 2:
                time.sleep(2)
    return None

def fetch_draws():
    """从多个API抓取最近多期开奖号码，返回list"""

    # 1. 灰鸟API（优先，境外可访问）
    print("尝试灰鸟API...")
    result = _request(API_HUINIAO)
    if result:
        try:
            data = result.get("data", {})
            draws = []
            # 取 data.list（多期）
            items = data.get("list", [])
            if not items:
                # 备选: data.data.list
                items = data.get("data", {}).get("list", [])
            for item in items:
                period_full = str(item.get("code", ""))
                period = period_full[-3:] if len(period_full) >= 3 else period_full
                number = (item.get("one", "") + item.get("two", "") +
                          item.get("three", "") + item.get("four", "") +
                          item.get("five", ""))
                if period and number and len(number) >= 5:
                    draws.append({"period": period, "number": number})
            # 如果list为空，尝试取last单条
            if not draws:
                last = data.get("last", {})
                if last:
                    period_full = str(last.get("code", ""))
                    period = period_full[-3:] if len(period_full) >= 3 else period_full
                    number = (last.get("one", "") + last.get("two", "") +
                              last.get("three", "") + last.get("four", "") +
                              last.get("five", ""))
                    if period and number and len(number) >= 5:
                        draws.append({"period": period, "number": number})
            if draws:
                print(f"  灰鸟API成功: 获取{len(draws)}期")
                return draws
        except Exception as e:
            print(f"  灰鸟API解析失败: {e}")

    # 2. 体彩官方API（备选）
    print("尝试体彩官方API...")
    result = _request(API_SPORTTERY)
    if result:
        try:
            draws = []
            items = result.get("value", {}).get("list", [])
            for item in items:
                period_full = str(item.get("lotteryDrawNum", ""))
                period = period_full[-3:] if len(period_full) >= 3 else period_full
                number = item.get("lotteryDrawResult", "").replace(" ", "")
                if period and number and len(number) >= 5:
                    draws.append({"period": period, "number": number})
            if draws:
                print(f"  体彩API成功: 获取{len(draws)}期")
                return draws
        except Exception as e:
            print(f"  体彩API解析失败: {e}")

    # 3. 彩经网API
    print("尝试彩经网API...")
    result = _request(API_CJCP)
    if result:
        try:
            draws = []
            items = result.get("data", {}).get("list", [])
            for item in items:
                period_full = str(item.get("issue", ""))
                period = period_full[-3:] if len(period_full) >= 3 else period_full
                number = str(item.get("drawCode", "")).replace(",", "").replace(" ", "")
                if period and number and len(number) >= 5:
                    draws.append({"period": period, "number": number})
            if draws:
                print(f"  彩经网API成功: 获取{len(draws)}期")
                return draws
        except Exception as e:
            print(f"  彩经网API解析失败: {e}")

    return []

def commit_to_github(message):
    """通过 git commit + push 提交，避免 API 直接写文件导致的冲突"""
    if not REPO or not GH_TOKEN:
        print("无GH_TOKEN，跳过提交")
        return

    try:
        # 配置 git remote 使用 token
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

def main():
    data = load_data()

    draws = fetch_draws()
    if not draws:
        print("所有API均失败，无法获取开奖结果")
        return

    # 构建期号→开奖映射
    draw_map = {d["period"]: d["number"] for d in draws}
    print(f"获取到{len(draw_map)}期开奖数据")

    digit_index = {"head": 0, "hundred": 1, "ten": 2, "tail": 3}
    updated_periods = []

    for record in data["records"]:
        period = record["period"]
        if record["winning"]:
            continue  # 已填过，跳过
        if period not in draw_map:
            continue  # 没有这期的开奖数据

        number = draw_map[period]
        front_four = number[:4] if len(number) >= 4 else number
        record["winning"] = front_four

        hits = {}
        for pos, idx in digit_index.items():
            draw_digit = int(front_four[idx])
            hits[pos] = calculate_hit(record["sequences"][pos], draw_digit)
        record["hits"] = hits
        updated_periods.append(period)
        print(f"已更新期{period}: 开奖{front_four}, 粒数{hits}")

    if not updated_periods:
        print("无需更新（所有期已填或无匹配开奖数据）")
        return

    save_data(data)
    commit_to_github(f"填入{','.join(updated_periods)}期开奖结果")

if __name__ == "__main__":
    main()
