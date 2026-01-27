import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 쪼개서 올린 파일 이름들 (책장 목록)
# 선생님이 올리신 파일명으로 정확히 적어주세요!
BOOK_PARTS = [
    "book1.pdf",
    "book2.pdf",
    "book3.pdf",
    "book4.pdf"
    # 필요한 만큼 파일 이름을 계속 추가하세요 (콤마 주의!)
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

# 2. [수정됨] 제한 없이 끝까지 읽는 함수
@st.cache_resource
def load_and_merge_books(file_list):
    full_text = ""
    total_pages_read = 0
    
    # 진행 상황 표시
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        total_files = len(file_list)
        
        for idx, filename in enumerate(file_list):
            if not os.path.exists(filename):
                continue
            
            status_text.info(f"📚 {idx+1}번째 책({filename})을 읽는 중...")
            
            with open(filename, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)
                
                # [핵심] 페이지 제한 없이 for문이 끝까지 돕니다!
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
                
                total_pages_read += num_pages
            
            # 진행률 업데이트
            progress_bar.progress((idx + 1) / total_files)

        status_text.success(f"✅ 백과사전 완전 정복! (총 {total_pages_read}페이지)")
        progress_bar.empty()
        return full_text

    except Exception as e:
        status_text.error(f"책을 읽는 중 에러 발생: {e}")
        return None

# 3. 실행 로직
if not any(os.path.exists(f) for f in BOOK_PARTS):
    st.error("⚠️ GitHub에 업로드된 책 파일이 없습니다. BOOK_PARTS 설정을 확인해주세요.")
    st.stop()

# 책 합체 및 로드
encyclopedia_text = load_and_merge_books(BOOK_PARTS)

if not encyclopedia_text:
    st.stop()

# 4. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "어디가 불편하신가요? 712페이지 전체 내용을 검색해 드릴게요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요 (예: 명치 쪽이 답답해요)"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 전체 백과사전을 분석 중입니다...")
        
        try:
            # 2.5 모델 (대용량 처리용)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            full_prompt = f"""
            당신은 유능한 의학 상담 AI입니다.
            아래 [백과사전 통합본] 내용을 바탕으로 답변하세요.

            [백과사전 통합본]
            {encyclopedia_text}
            
            [사용자 증상]
            {prompt}
            
            규칙:
            1. 백과사전 내용에 기반하여 전문적으로 답변하세요.
            2. 관련된 의학 정보를 찾아서 원인과 대처법을 설명하세요.
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            # 진짜 구글 한도 초과 시 에러 메시지
            if "429" in str(e):
                msg_placeholder.error("⚠️ 내용이 너무 방대하여 구글 서버가 잠시 숨을 고르고 있습니다. (1분 뒤 다시 시도해주세요)")
            else:
                msg_placeholder.error(f"에러가 발생했습니다: {str(e)}")













