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
st.title("🏥 내 손안의 주치의 (만능 접속 버전)")

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
    status_text = st.empty()
    try:
        valid_files = [f for f in file_list if os.path.exists(f)]
        if not valid_files:
            return None

        status_text.info("📚 백과사전 데이터를 통합하고 있습니다...")
        for filename in valid_files:
            with open(filename, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        full_text += extracted + "\n"
        
        status_text.success(f"✅ 백과사전 준비 완료! (총 {len(full_text)}자)")
        return full_text
    except Exception as e:
        status_text.error(f"오류 발생: {e}")
        return None

# 3. 스마트 검색 함수 (가볍게 5개만 추출)
def get_relevant_content(full_text, query):
    chunk_size = 1000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    relevant_chunks = []
    query_keywords = query.split()
    
    for chunk in chunks:
        score = 0
        for word in query_keywords:
            if word in chunk:
                score += 1
        if score > 0:
            relevant_chunks.append((score, chunk))
    
    relevant_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for score, chunk in relevant_chunks[:5]]
    return "\n...\n".join(top_chunks)

# 4. [핵심] 만능 접속 시도 함수 (순서대로 다 찔러봄)
def generate_with_auto_model_selection(prompt):
    # 시도해볼 모델 목록 (우선순위: 제한이 널널한 1.5 시리즈)
    candidate_models = [
        "gemini-1.5-flash",          # 1순위: 가장 표준적인 무제한 모델
        "gemini-1.5-flash-001",      # 2순위: 구버전 (안정적)
        "gemini-1.5-flash-002",      # 3순위: 신버전
        "gemini-1.5-flash-latest",   # 4순위: 최신 별칭
        "gemini-flash-latest"        # 5순위: 최후의 수단
    ]
    
    last_error = ""
    
    for model_name in candidate_models:
        try:
            # 모델 생성 시도
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name # 성공하면 내용과 모델명 반환
            
        except Exception as e:
            error_msg = str(e)
            # 429(제한초과)나 404(모델없음)면 다음 모델로 넘어감
            last_error = error_msg
            continue 

    # 모든 모델이 실패했을 때
    raise Exception(f"모든 모델 접속 실패. 마지막 에러: {last_error}")

# 5. UI 및 로직
with st.sidebar:
    st.header("📂 자료 등록")
    uploaded_file = st.file_uploader("파일 업로드 (PDF/TXT)", type=['pdf', 'txt'])
    st.info(f"기본 탑재: 백과사전 (총 {len(BOOK_PARTS)}권)")

encyclopedia_text = load_and_merge_books(BOOK_PARTS)
target_text = ""
use_smart_search = False

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    target_text += extracted + "\n"
        else:
            target_text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"읽기 실패: {str(e)}")
        st.stop()
        
    if len(target_text) > 30000:
        use_smart_search = True
        st.toast("🚀 스마트 검색 가동")
else:
    if encyclopedia_text:
        target_text = encyclopedia_text
        use_smart_search = True
    else:
        st.error("백과사전 파일 없음")
        st.stop()

# 6. 채팅창
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 증상을 말씀해 주세요. (가장 빠른 모델을 자동으로 찾습니다)"})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 접속 가능한 모델을 찾는 중...")
        
        try:
            if use_smart_search:
                final_context = get_relevant_content(target_text, prompt)
                if not final_context or len(final_context.strip()) == 0:
                    final_context = "관련 내용을 찾을 수 없습니다."
            else:
                final_context = target_text

            full_prompt = f"""
            문서 내용:
            {final_context}
            
            질문: {prompt}
            
            위 내용을 바탕으로 답변하세요.
            """
            
            # [자동 찾기 실행]
            final_response, used_model = generate_with_auto_model_selection(full_prompt)
            
            msg_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            # (디버깅용) 어떤 모델이 성공했는지 작게 표시
            st.caption(f"⚡ 연결된 모델: {used_model}")
            
        except Exception as e:
            st.error("❌ 모든 연결 시도가 실패했습니다.")
            st.error(f"에러 내용: {str(e)}")
            if "429" in str(e):
                st.warning("⚠️ 현재 모든 모델의 사용량이 꽉 찼습니다. 내일 다시 시도해야 할 수도 있습니다.")


























