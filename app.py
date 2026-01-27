import streamlit as st
import google.generativeai as genai

st.title("🚑 모델 진단 키트")

# 1. 비밀 금고에서 키 꺼내기
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        st.success(f"API 키 확인 완료! (키: {api_key[:5]}...)")
    else:
        st.error("비밀 금고에 키가 없습니다.")
        st.stop()
except Exception as e:
    st.error(f"키 설정 중 에러: {e}")
    st.stop()

# 2. 사용 가능한 모델 목록 조회
st.write("---")
st.subheader("사용 가능한 모델 목록:")

try:
    # 시스템에 등록된 모든 모델을 불러옵니다
    models = genai.list_models()
    found_any = False
    
    for m in models:
        # '대화(generateContent)'가 가능한 모델만 표시
        if 'generateContent' in m.supported_generation_methods:
            st.code(m.name) # 화면에 모델 이름 출력
            found_any = True
            
    if not found_any:
        st.warning("사용 가능한 모델이 하나도 안 보입니다. API 설정을 확인해야 합니다.")
        
except Exception as e:
    st.error(f"목록을 불러오는 중 에러 발생: {e}")
    st.info("팁: 구글 클라우드 콘솔에서 'Generative Language API'가 켜져 있는지 확인하세요.")







