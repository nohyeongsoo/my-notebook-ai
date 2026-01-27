import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 쪼개서 올린 파일 이름들을 여기에 다 적어주세요!
# 앱이 이 순서대로 읽어서 하나로 합칩니다.
BOOK_PARTS = [
    "jsbgocrc1.pdf",
    "jsbgocrc2.pdf",
    "jsbgocrc3.pdf",
    "jsbgocrc4.pdf" 
    # 필요한 만큼 계속 추가하세요 (콤마 주의!)
]
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

# 2. 여러 파일을 읽어서 하나로 합치는 함수
@st.cache_resource
def load_and_merge_books(file_list):
    full_text = ""
    total_pages_read = 0
    
    # 진행 상황을 보여줄 빈칸
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        total_files = len(file_list)
        
        for idx, filename in enumerate(file_list):
            if not os.path.exists(filename):
                continue # 파일 없으면 건너뜀
            
            status_text.info(f"📚 {idx+1}번째 책({filename})을 읽고 합치는 중...")
            
            with open(filename, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                # 각 책의 페이지를 다 읽음
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
                
                total_pages_read += len(pdf_reader.pages)
            
            # 진행률 바 업데이트
            progress_bar.progress((idx + 1) / total_files)

        # 다 읽었으면 정리
        status_text.success(f"✅ 총 {total_pages_read}페이지 분량의 백과사전 학습 완료!")
        progress_bar.empty() # 진행바 숨김
        return full_text

    except Exception as e:
        status_text.error(f"책을 읽는 중 에러 발생: {e}")
        return None

# 3. 실행 로직
# 파일들이 하나라도 있는지 확인
if not any(os.path.exists(f) for f in BOOK_PARTS):
    st.error("⚠️ GitHub에 업로드된 책 파일이 없습니다. 파일 이름을 확인해주세요.")
    st.stop()

# 합체 시작!
encyclopedia_text = load_and_merge_books(BOOK_PARTS)

if not encyclopedia_text:
    st.stop()

# 4. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "어디가 불편하신가요? 증상을 말씀해 주세요. 백과사전 전체를 검색해 드릴게요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요 (예: 오른쪽 배가 콕콕 쑤셔요)"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 720페이지 전체를 분석 중입니다...")
        
        try:
            # 2.5 모델 (대용량 처리에 강함)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            full_prompt = f"""
            당신은 유능한 의학 상담 AI입니다.
            아래 [백과사전 통합본]을 바탕으로 사용자의 증상을 분석하세요.

            [백과사전 통합본 내용]
            {encyclopedia_text}
            
            [사용자 증상]
            {prompt}
            
            답변 시 주의사항:
            1. 백과사전에 있는 내용에 근거해서 설명하세요.
            2. 추측하지 말고 책에 있는 팩트를 전달하세요.
            3. 심각해 보이면 병원에 가보라는 조언을 덧붙이세요.
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            msg_placeholder.error("⚠️ 내용이 너무 방대하여 처리가 지연되었습니다. 잠시 후 다시 시도하거나, 질문을 조금 더 구체적으로 해주세요.")












