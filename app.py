import streamlit as st
import sqlite3
from bs4 import BeautifulSoup
import requests
import docx
import io
from google import genai
from google.genai import types
from anthropic import Anthropic

# 데이터베이스 설정 (History 저장용)
def init_db():
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY, topic TEXT, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# URL 텍스트 추출 함수
def get_url_text(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        return f"URL 읽기 실패: {e}"

# UI 구성
st.set_page_config(page_title="Research Pipeline", layout="wide")

# (기존 비밀번호 및 로그인 로직은 유지하되, 사이드바를 아래와 같이 변경합니다)

with st.sidebar:
    st.title("📂 내 연구 기록 (History)")
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("SELECT id, topic FROM history ORDER BY timestamp DESC")
    records = c.fetchall()
    
    for rec in records:
        if st.button(f"📖 {rec[1][:20]}...", key=f"hist_{rec[0]}"):
            st.session_state.selected_hist = rec[0]
    conn.close()
    
    st.markdown("---")
    # ... (기존 설정 메뉴 위치)

# 메인 화면
st.title("🔬 AI Dual-Agent 파이프라인")

# URL 입력 필드 추가
col_input1, col_input2 = st.columns([2, 1])
with col_input1:
    user_topic = st.text_area("연구 주제")
with col_input2:
    url_input = st.text_input("참조할 웹페이지 URL (선택)")

if st.button("🚀 실행"):
    # URL 텍스트가 있으면 가져오기
    extra_text = get_url_text(url_input) if url_input else ""
    
    # ... (기존 Gemini/Claude 호출 로직 수행)
    
    # 실행 완료 후 DB 저장
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("INSERT INTO history (topic, result) VALUES (?, ?)", (user_topic, st.session_state.final_output))
    conn.commit()
    conn.close()
    st.rerun()

# 기록 불러오기 로직
if "selected_hist" in st.session_state:
    conn = sqlite3.connect("history.db")
    c = conn.cursor()
    c.execute("SELECT result FROM history WHERE id=?", (st.session_state.selected_hist,))
    res = c.fetchone()
    if res:
        st.markdown(res[0])
