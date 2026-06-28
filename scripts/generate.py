#!/usr/bin/env python3
"""发财就手 - 每日生成新一期 v2 (API直写)"""
import json, os, sys, ssl, random, base64, time
from urllib.request import Request, urlopen
from datetime import datetime, timezone, timedelta

REPO = os.environ.get('GITHUB_REPOSITORY', 'ebupuba099-lang/facaijiushou')
DATA_FILE = 'data/lottery_data.json'
TZ = timezone(timedelta(hours=8))
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def log(msg):
    print(f'[{datetime.now(TZ).strftime("%H:%M:%S")}] {msg}', flush=True)

def github_get(path):
    token = os.environ.get('GH_TOKEN', '')
    req = Request(f'https://api.github.com/repos/{REPO}/contents/{path}',
                  headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'})
    resp = urlopen(req, timeout=30, context=ctx)
    info = json.loads(resp.read().decode())
    return info['sha'], json.loads(base64.b64decode(info['content']).decode('utf-8'))

def github_put(path, content, sha, msg):
    token = os.environ.get('GH_TOKEN', '')
    b64 = base64.b64encode(json.dumps(content, ensure_ascii=False, indent=2).encode('utf-8')).decode('utf-8')
    payload = {'message': msg, 'content': b64, 'sha': sha}
    req = Request(f'https://api.github.com/repos/{REPO}/contents/{path}',
                  data=json.dumps(payload).encode('utf-8'),
                  headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json',
                           'Content-Type': 'application/json'}, method='PUT')
    resp = urlopen(req, timeout=30, context=ctx)
    return json.loads(resp.read().decode())

def generate_levels():
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
    log('===== 生成新期 v2 =====')
    
    sha, data = github_get(DATA_FILE)
    records = data.get('records', [])
    
    if not records:
        log('无数据')
        return
    
    # 找最大期号
    latest = max(records, key=lambda r: int(str(r['period'])))
    latest_period = int(str(latest['period']))
    
    # 检查是否已开奖
    if not latest.get('winning'):
        now_ts = int(datetime.now().timestamp() * 1000)
        last_attempt = data.get('lastGenerateAttempt', data.get('lastUpdate', 0))
        stale_ms = now_ts - last_attempt
        if stale_ms < 2 * 24 * 3600 * 1000:
            if 'lastGenerateAttempt' not in data:
                data['lastGenerateAttempt'] = now_ts
            log(f'{latest_period}期未开奖，跳过')
            return
        else:
            log(f'{latest_period}期超48h未开奖，跳过生成下一期')
    
    next_period = str(latest_period + 1)
    if next_period in [str(r['period']) for r in records]:
        log(f'{next_period}期已存在')
        return
    
    # 生成新期
    positions = ['head', 'hundred', 'ten', 'tail']
    sequences = {pos: generate_levels() for pos in positions}
    
    new_record = {
        'period': next_period,
        'sequences': sequences,
        'winning': '',
        'hits': {}
    }
    records.append(new_record)
    if len(records) > 50:
        records = records[-50:]
    
    data['records'] = records
    data['lastUpdate'] = int(datetime.now().timestamp() * 1000)
    data.pop('lastGenerateAttempt', None)
    
    result = github_put(DATA_FILE, data, sha, f'生成{next_period}期')
    log(f'✅ 已生成{next_period}期: {result["content"]["sha"][:8]}')

if __name__ == '__main__':
    main()
