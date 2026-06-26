#!/usr/bin/env python3
"""发财就手 - 抓取开奖结果并计算粒数"""
import json, os, ssl, sys, time, urllib.request, urllib.error
from datetime import datetime
from common import DATA_FILE, load_data, save_data, commit_to_github

API_SPORTTERY = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=350133&provinceId=0&pageSize=10&is11=0"
API_HUINIAO = "https://api.huiniao.top/interface/home/lotteryHistory?type=plw&page=1&limit=10"
API_CJCP = "https://www.cjcp.com.cn/ajax/lottery/history?lotteryId=85&pageSize=10&pageNo=1"
API_JCJ = "https://www.lottery.gov.cn/api/lottery_kj_detail_new.jspx?_ltype=4&_term="  # 体彩官网新版API

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

    # 4. 体彩官网新版API（逐个期号查询）
    print("尝试体彩官网新版API...")
    try:
        # 用已知最近期号范围尝试
        for test_period in range(26166, 26156, -1):
            url = API_JCJ + str(test_period)
            result = _request(url, timeout=10)
            if result:
                draws = []
                # 新版API结构不同，需要解析
                if isinstance(result, dict):
                    number = result.get("lotteryDrawResult", "") or result.get("drawNumber", "")
                    period = str(result.get("lotteryDrawNum", "") or result.get("termNum", ""))
                    period = period[-3:] if len(period) >= 3 else period
                    number = str(number).replace(" ", "")
                    if period and number and len(number) >= 5:
                        draws.append({"period": period, "number": number})
                        print(f"  官网API成功: 获取{len(draws)}期")
                        return draws
    except Exception as e:
        print(f"  官网API失败: {e}")

    return []

def fill_draw(record, front_four):
    """填入开奖号码并计算粒数"""
    record["winning"] = front_four
    digit_index = {"head": 0, "hundred": 1, "ten": 2, "tail": 3}
    hits = {}
    for pos, idx in digit_index.items():
        draw_digit = int(front_four[idx])
        hits[pos] = calculate_hit(record["sequences"][pos], draw_digit)
    record["hits"] = hits
    return hits

def interactive_fill(data):
    """手动输入模式：用户直接输入开奖号码"""
    print("\n" + "=" * 50)
    print("📝 手动输入开奖号码模式")
    print("=" * 50)

    # 找到需要填入的期号
    pending = [r for r in data["records"] if not r.get("winning")]
    if not pending:
        print("✅ 所有期都已填入开奖号码！")
        return []

    print(f"待填入的期号: {', '.join(r['period'] for r in pending)}")

    for record in pending:
        period = record["period"]
        while True:
            number = input(f"\n请输入 {period} 期的开奖号码（前四位，如 1234）: ").strip()
            if len(number) == 4 and number.isdigit():
                break
            print("❌ 请输入4位数字！")

        hits = fill_draw(record, number)
        print(f"  ✅ {period}期: 开奖{number}, 粒数{hits}")
        updated_periods.append(period)

    return updated_periods

def main():
    data = load_data()
    updated_periods = []

    # 检查是否有命令行参数（手动输入模式）
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        updated_periods = interactive_fill(data)
        if not updated_periods:
            return
    else:
        # 自动API模式
        # 先检查是否有待填的期号
        pending_periods = [r["period"] for r in data["records"] if not r.get("winning")]
        if not pending_periods:
            print("所有期都已填入开奖号码，无需抓取")
            return

        print(f"待填入期号: {', '.join(pending_periods)}")

        draws = fetch_draws()
        if not draws:
            print(f"⚠️ 所有API均失败！待填入: {', '.join(pending_periods)}")
            # 在本地环境（无GH_TOKEN）时，尝试交互模式
            if not os.environ.get("GH_TOKEN"):
                print("检测到本地环境，切换到手动输入模式...")
                updated_periods = interactive_fill(data)
                if not updated_periods:
                    return
            else:
                # GitHub Actions 环境：API失败，打印明确警告
                print(f"❌ GitHub Actions中4个API全部失败！")
                print(f"❌ 以下期号未填入开奖号码: {', '.join(pending_periods)}")
                print(f"💡 可能原因: GitHub Actions IP被国内API安全策略拦截")
                print(f"💡 请手动运行: python scripts/lottery.py --manual")
                print(f"💡 或在本地环境运行: python scripts/lottery.py")
                # 不return，而是尝试更新lastUpdate让generate.py知道我们还活着
                # 但数据没变，不commit
                return
        else:
            # 构建期号→开奖映射
            draw_map = {d["period"]: d["number"] for d in draws}
            print(f"获取到{len(draw_map)}期开奖数据: {sorted(draw_map.keys())}")

            filled_count = 0
            for record in data["records"]:
                period = record["period"]
                if record.get("winning"):
                    continue  # 已填过，跳过
                if period not in draw_map:
                    print(f"  ⚠️ 期{period}不在API返回数据中（可能还未开奖）")
                    continue  # 没有这期的开奖数据

                number = draw_map[period]
                front_four = number[:4] if len(number) >= 4 else number
                hits = fill_draw(record, front_four)
                updated_periods.append(period)
                filled_count += 1
                print(f"  ✅ 期{period}: 开奖{front_four}, 粒数{hits}")

            # 检查是否还有未填的
            still_pending = [r["period"] for r in data["records"] if not r.get("winning")]
            if still_pending:
                print(f"⚠️ 仍有{len(still_pending)}期未填入: {', '.join(still_pending)}")
                print(f"   API返回的期号: {sorted(draw_map.keys())}")

    if not updated_periods:
        print("无需更新（所有期已填或无匹配开奖数据）")
        return

    save_data(data)

    # 在本地环境时自动 git add/commit/push
    if not os.environ.get("GH_TOKEN"):
        import subprocess
        try:
            subprocess.run(["git", "add", DATA_FILE], check=True)
            msg = f"填入{','.join(updated_periods)}期开奖结果"
            result = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
            if b"nothing to commit" not in result.stdout + result.stderr:
                subprocess.run(["git", "push"], check=True)
                print(f"已提交并推送: {msg}")
        except subprocess.CalledProcessError as e:
            print(f"Git操作失败: {e}")
    else:
        commit_to_github(f"填入{','.join(updated_periods)}期开奖结果")

if __name__ == "__main__":
    updated_periods = []  # 模块级变量，interactive_fill 使用
    main()
