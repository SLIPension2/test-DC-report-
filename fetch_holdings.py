"""
pykrx로 ETF 구성종목을 수집해 etf_holdings.json으로 저장
GitHub Actions에서 월 1회 실행 (매월 1일 오전 7시 KST)

etf_holdings.json 구조:
{
  "updated": "2026-07-08",
  "holdings": {
    "360750": [
      {"name": "Apple Inc.", "weight": 7.12},
      {"name": "Microsoft Corp.", "weight": 6.88},
      ...
    ],
    ...
  }
}
"""

import json, time, traceback
from datetime import datetime, timedelta
from pykrx import stock

def get_last_business_day():
    today = datetime.today()
    if today.weekday() == 0:   return (today - timedelta(days=3)).strftime('%Y%m%d')
    elif today.weekday() == 6: return (today - timedelta(days=2)).strftime('%Y%m%d')
    else:                      return (today - timedelta(days=1)).strftime('%Y%m%d')

def fetch_holdings():
    # etf_list.json에서 코드 읽기
    with open('etf_list.json', encoding='utf-8') as f:
        etf_list = json.load(f)

    date = get_last_business_day()
    print(f"기준일: {date} | 총 {len(etf_list)}개 ETF 처리 시작")

    holdings = {}
    success = 0
    fail    = 0

    for i, etf in enumerate(etf_list):
        code = etf.get('code', '').strip()
        name = etf.get('name', '')
        if not code:
            continue

        try:
            df = stock.get_etf_portfolio_deposit_file(date, code)
            if df is None or df.empty:
                holdings[code] = []
                fail += 1
                continue

            # 컬럼명 정규화
            df.columns = [str(c).strip() for c in df.columns]

            # 종목명 컬럼 찾기
            name_col   = next((c for c in df.columns if '종목' in c or 'name' in c.lower()), None)
            weight_col = next((c for c in df.columns if '비중' in c or 'weight' in c.lower() or '%' in c), None)

            if not name_col or not weight_col:
                # 컬럼을 못 찾으면 첫번째, 마지막 컬럼 사용
                name_col   = df.columns[0]
                weight_col = df.columns[-1]

            items = []
            for _, row in df.iterrows():
                n = str(row[name_col]).strip()
                try:
                    w = round(float(row[weight_col]), 2)
                except:
                    w = 0.0
                if n and n != 'nan' and w > 0:
                    items.append({"name": n, "weight": w})

            # 비중 내림차순 정렬, 상위 20개만 저장
            items.sort(key=lambda x: x['weight'], reverse=True)
            holdings[code] = items[:20]
            success += 1

        except Exception as e:
            holdings[code] = []
            fail += 1
            if fail <= 5:
                print(f"  ❌ [{i+1}] {name}({code}): {e}")

        # KRX 서버 부하 방지 딜레이
        time.sleep(0.5)

        # 진행상황 출력
        if (i+1) % 100 == 0:
            print(f"  진행: {i+1}/{len(etf_list)} | 성공:{success} 실패:{fail}")

    result = {
        "updated": datetime.today().strftime('%Y-%m-%d'),
        "base_date": date,
        "total": len(holdings),
        "holdings": holdings
    }

    with open('etf_holdings.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 완료! 성공:{success} 실패:{fail}")
    print(f"etf_holdings.json 저장 완료 ({len(holdings)}개 ETF)")

if __name__ == '__main__':
    fetch_holdings()
