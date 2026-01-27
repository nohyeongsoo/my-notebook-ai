import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 백과사전 파일 이름
ENCYCLOPEDIA_FILE = "jsbgocrc.pdf"
# ==========================================

st.set_page_config(page_title="홈 닥터 AI", page_icon="🏥")
st.title("🏥 내 손안의 주치의 (증상 백과사전)")

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

# 2. (수정됨) 안전 한도 내에서 최대한 읽기
@st.cache_resource
def load_encyclopedia(filename):
    text_content = ""
    # 무료 버전 안전 한도 (글자수 약 30만 자 = 책 200~300페이지 분량)
    # 이 이상 넘어가면 429 에러가 뜰 확률이 높습니다.
    MAX_CHARS = 300000 
    
    try:
        if not os.path.exists(filename):
            return None
        
        with open(filename, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            status_text = st.empty()
            progress_bar = st.progress(0)
            status_text.info(f"📚 백과사전 읽는 중... (최대 {MAX_CHARS}자까지)")
            
            for i, page in enumerate(pdf_reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
                
                # 진행률 표시
                progress_bar.progress(min((i + 1) / total_pages, 1.0))
                
                # [안전장치] 글자 수가 한도를 넘으면 멈춤!
                if len(text_content) >= MAX_CHARS:
                    status_text.warning(f"⚠️ 용량 안전장치 발동: 전체 {total_pages}페이지 중 앞부분 {i+1}페이지까지만 학습했습니다. (무료 한도 보호)")
                    return text_content
            
            status_text.success(f"✅ 전체 {total_pages}페이지 학습 완료!")
            progress_bar.empty()
            
    except Exception as e:
        st.error(f"책을 읽는 중 에러 발생: {e}")
        return None
        
    return text_content

# 3. 로딩 및 실행
if not os.path.exists(ENCYCLOPEDIA_FILE):
    st.error(f"파일을 찾을 수 없습니다: {ENCYCLOPEDIA_FILE}")
    st.stop()

full_text = load_encyclopedia(ENCYCLOPEDIA_FILE)

if full_text is None:
    st.stop()

# 4. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "어디가 불편하신가요? 증상을 말씀해 주세요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 분석 중...")
        
        try:
            # 선생님 계정에 있는 2.5 모델 사용
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            full_prompt = f"""
            당신은 가정의학과 AI입니다. 
            아래 [백과사전 내용]을 바탕으로 답변하세요.
            내용이 없으면 "책에 없는 내용입니다"라고 하세요.

            [백과사전 내용 (발췌)]
            {full_text}
            
            [환자 증상]
            {prompt}
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            msg_placeholder.error("⚠️ 잠시만요! 질문이 너무 많거나 내용이 깁니다. 1분 뒤에 다시 시도해주세요.")












