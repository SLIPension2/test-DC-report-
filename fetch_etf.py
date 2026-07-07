"""
pykrx를 사용해 KRX 전일 ETF 거래대금 TOP5 + 수익률 TOP5를 수집하고
etf_data.json 으로 저장하는 스크립트

GitHub Actions에서 매일 평일 오전 7시(KST)에 자동 실행됩니다.
"""

import json
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

def get_last_business_day():
    """가장 최근 영업일(평일) 날짜 반환"""
    today = datetime.today()
    # 오늘이 월요일이면 지난 금요일
    if today.weekday() == 0:
        return (today - timedelta(days=3)).strftime('%Y%m%d')
    # 오늘이 일요일이면 지난 금요일
    elif today.weekday() == 6:
        return (today - timedelta(days=2)).strftime('%Y%m%d')
    else:
        return (today - timedelta(days=1)).strftime('%Y%m%d')

def fetch_etf_data():
    date = get_last_business_day()
    date_display = f"{date[:4]}.{date[4:6]}.{date[6:]}"
    print(f"📅 기준일: {date_display}")

    try:
        # ETF 전종목 시세 조회
        df = stock.get_etf_ohlcv_by_date(date, date, "KOSPI")
        if df is None or df.empty:
            df = stock.get_etf_ohlcv_by_date(date, date, "KOSDAQ")
    except Exception as e:
        print(f"❌ OHLCV 조회 실패: {e}")
        df = None

    # ETF 티커 목록 + 이름 매핑
    try:
        tickers = stock.get_etf_ticker_list(date)
        name_map = {t: stock.get_etf_ticker_name(t) for t in tickers}
    except Exception as e:
        print(f"⚠️ 티커 목록 조회 실패: {e}")
        tickers = []
        name_map = {}

    # 거래대금 + 수익률 데이터 수집
    records = []
    for ticker in tickers[:200]:  # 상위 200개만 처리 (속도)
        try:
            df_ticker = stock.get_etf_ohlcv_by_date(date, date, ticker)
            if df_ticker is None or df_ticker.empty:
                continue
            row = df_ticker.iloc[-1]
            close = float(row.get('종가', 0) or row.get('Close', 0))
            open_ = float(row.get('시가', 0) or row.get('Open', 0))
            volume = float(row.get('거래대금', 0) or row.get('거래금액', 0))
            change_pct = ((close - open_) / open_ * 100) if open_ > 0 else 0

            records.append({
                'ticker': ticker,
                'name': name_map.get(ticker, ticker),
                'close': close,
                'volume': volume,
                'change_pct': round(change_pct, 2),
                'detail': '',
            })
        except:
            continue

    if not records:
        print("⚠️ 데이터 없음, 기본 fallback 사용")
        # 데이터 수집 실패 시 빈 JSON 저장 (HTML이 fallback 사용)
        result = {"date": date_display, "volume": [], "return": []}
        with open('etf_data.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    df_all = pd.DataFrame(records)

    # 거래대금 TOP5
    top_volume = (
        df_all[df_all['volume'] > 0]
        .sort_values('volume', ascending=False)
        .head(5)
    )

    # 수익률 TOP5 (등락률 기준)
    top_return = (
        df_all[df_all['change_pct'].notna()]
        .sort_values('change_pct', ascending=False)
        .head(5)
    )

    def to_list(df_sub):
        return [
            {
                'name': row['name'],
                'detail': row['detail'],
                'volume': int(row['volume']),
                'change_pct': float(row['change_pct']),
            }
            for _, row in df_sub.iterrows()
        ]

    result = {
        'date': date_display,
        'volume': to_list(top_volume),
        'return': to_list(top_return),
    }

    with open('etf_data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ etf_data.json 저장 완료")
    print(f"   거래대금 TOP5: {[r['name'] for r in result['volume']]}")
    print(f"   수익률  TOP5: {[r['name'] for r in result['return']]}")

if __name__ == '__main__':
    fetch_etf_data()
