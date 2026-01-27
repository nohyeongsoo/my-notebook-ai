import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="모델 탐정", page_icon="🕵️‍♂️")
st.title("🕵️‍♂️ 내 계정의 사용 가능 모델 목록")

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

# 2. 모델 목록 조회 및 출력
try:
    st.write("구글 서버에 메뉴판을 요청하고 있습니다...")
    
    # 사용 가능한 모든 모델 가져오기
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)

    st.success(f"✅ 총 {len(available_models)}개의 모델이 발견되었습니다!")
    
    st.write("### 👇 이 이름들 중에서 하나를 골라야 합니다:")
    st.code("\n".join(available_models))
    
    st.info("위 목록에 있는 이름을 복사해서 알려주세요! (특히 'flash'가 들어간 것)")

except Exception as e:
    st.error(f"목록을 가져오는 중 에러 발생: {str(e)}")




























