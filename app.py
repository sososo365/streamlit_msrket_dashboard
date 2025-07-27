import streamlit as st
import yfinance as yf
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="📊 Market Sentiment Strategy", layout="centered")

# 상태 변수 (세션 저장)
if 'schd' not in st.session_state:
    st.session_state.schd = 100.0
    st.session_state.tqqq = 0.0
    st.session_state.month_counter = 0
    st.session_state.last_month = None

# 색상 대체 텍스트 표시
def sentiment_color_label(text, color):
    return f"**{text}**"

def get_qqq_data():
    try:
        qqq = yf.Ticker("QQQ")
        data = qqq.history(period="1d")
        if data.empty:
            return None, None
        qqq_price = data['Close'].iloc[-1]
        qqq_history = qqq.history(period="200d")['Close']
        if len(qqq_history) < 200:
            return None, None
        qqq_sma = qqq_history.mean()
        return qqq_price, qqq_sma
    except:
        return None, None

def get_vix_data():
    try:
        vix = yf.Ticker("^VIX")
        data = vix.history(period="1d")
        if data.empty:
            return None
        return data['Close'].iloc[-1]
    except:
        return None

def interpret_vix(vix):
    if vix is None:
        return "N/A"
    if vix < 15:
        return "Low Volatility (Bullish) - 매도 신호"
    elif vix < 25:
        return "Moderate Volatility (Neutral) - 대기"
    else:
        return "High Volatility (Bearish) - 매수 신호"

def fetch_fgi():
    try:
        url = 'https://feargreedmeter.com/'
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        fgi_element = soup.find('div', class_='text-center text-4xl font-semibold mb-1 text-white')
        if fgi_element:
            text = fgi_element.text.strip()
            return int(text) if text.isdigit() else None
        return None
    except:
        return None

def fetch_pci():
    try:
        url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        td_elements = soup.find_all('td', class_='col-6')
        for td in td_elements:
            try:
                return float(td.text.strip().replace(',', ''))
            except:
                continue
        return None
    except:
        return None

def interpret_fgi(fgi):
    if fgi is None:
        return "N/A"
    if fgi <= 25:
        return "Extreme Fear (매수 신호)"
    elif fgi <= 45:
        return "Fear (매수 신호)"
    elif fgi <= 55:
        return "Neutral (대기)"
    elif fgi <= 75:
        return "Greed (매도 신호)"
    else:
        return "Extreme Greed (매도 신호)"

def interpret_pci(pci):
    if pci is None:
        return "N/A"
    if pci > 0.95:
        return "Bearish (매수 신호)"
    elif pci < 0.65:
        return "Bullish (매도 신호)"
    else:
        return "Neutral (대기)"

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else None

def update_strategy(qqq_price, qqq_sma):
    now = datetime.now()
    if qqq_price is None or qqq_sma is None:
        return "데이터 부족"
    if qqq_price < qqq_sma:
        if st.session_state.last_month != now.month:
            st.session_state.month_counter += 1
            st.session_state.last_month = now.month
            shift_pct = min(st.session_state.month_counter * 5, 100)
            total = st.session_state.schd + st.session_state.tqqq
            shift_amount = total * (shift_pct / 100)
            st.session_state.schd -= shift_amount
            st.session_state.tqqq += shift_amount
            return f"{shift_pct}%를 TQQQ로 이동"
        else:
            return "이번 달 이미 이동 완료"
    else:
        st.session_state.month_counter = 0
        return "QQQ가 SMA 이상 - 초기화"

# 데이터 불러오기
qqq_price, qqq_sma = get_qqq_data()
vix = get_vix_data()
fgi = fetch_fgi()
pci = fetch_pci()
spy_data = yf.Ticker("SPY").history(period="200d")["Close"]
rsi_value = calculate_rsi(spy_data) if not spy_data.empty else None

# 대시보드 UI
st.title("📊 Market Sentiment Dashboard")
st.write("실시간 시장 심리 기반 투자 전략")

col1, col2 = st.columns(2)
col1.metric("QQQ 현재가", f"${qqq_price:.2f}" if qqq_price else "N/A")
col2.metric("200일 평균", f"${qqq_sma:.2f}" if qqq_sma else "N/A")

st.subheader("📉 RSI (SPY)")
if rsi_value:
    rsi_status = "과매도 (매수)" if rsi_value < 30 else "과매수 (매도)" if rsi_value > 70 else "중립"
    st.write(f"RSI: **{rsi_value:.2f}** → {rsi_status}")
else:
    st.write("RSI 데이터 없음")

st.subheader("📊 기타 지표")
st.write(f"Fear & Greed Index: **{fgi}** → {interpret_fgi(fgi)}")
st.write(f"Put/Call Ratio (PCI): **{pci}** → {interpret_pci(pci)}")
st.write(f"VIX 변동성 지수: **{vix:.2f}** → {interpret_vix(vix)}" if vix else "VIX 정보 없음")

st.subheader("💸 투자 전략")
action = update_strategy(qqq_price, qqq_sma)
st.success(f"전략 결과: {action}")

st.info(f"SCHD: {st.session_state.schd:.1f}% | TQQQ: {st.session_state.tqqq:.1f}% | 전환개월: {st.session_state.month_counter}")

st.caption("📆 마지막 갱신: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
