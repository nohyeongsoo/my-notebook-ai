import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import time

# ==========================================
# [설정] 백과사전 파일 목록
BOOK_PARTS = [
    "jsbgocrc1.pdf",
    "jsbgocrc2.pdf",
    "jsbgocrc3.pdf",
    "jsbgocrc4.pdf"
]
# ==========================================

st.set_page_config(page_title="홈 닥터 AI", page_icon="🏥", layout="wide")
st.title("🏥 내 손안의 주치의 (최종 수정)")

# 1. 키 설정
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("비밀 금고에 키가 없습니다.")
        st.stop()
except:
    st.error("키 설정 오류")
    st.stop()

# 2. 데이터 통합 함수
@st.cache_resource
def load_and_merge_books(file_list):
    full_text = ""
    status_text
































