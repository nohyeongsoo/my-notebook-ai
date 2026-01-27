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
st.title("🏥 내 손안의 주치의 (Premium)")

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

# 3. 스마트 검색 함수 (유료니까 넉넉하게 10개!)
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
    # 유료 회원이시니 정보를 더 많이(10개) 봅니다.
    top_chunks = [chunk for score, chunk in relevant_chunks[:10]]
    return "\n...\n".join(top_chunks)

# 4. [핵심] 만능 자동 접속 함수 (알아서 찾아냄)
def generate_with_auto_selection(prompt):
    # 시도할 모델 순서 (성능 좋고 안정적인 순서)
    candidate_models = [
        "gemini-1.5-flash",          # 1순위: 가장 표준적이고 빠름
        "gemini-1.5-flash-001",      # 2순위: 구버전 (안정성 甲)
        "gemini-2.0-flash-lite",     # 3순위: 신형 라이트
        "gemini-flash-latest"        # 4순위: 최후의 보루
    ]
    
    last_error = None
    
    for model_name in candidate_models:
        try:
            # 접속 시도
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name # 성공 시 내용과 모델명 반환
            
        except Exception as e:
            last_error = e
            # 실패하면 다음 모델로 조용히 넘어감
            continue 

    # 모든 모델이 다 실패했을 때만 에러 뿜음
    raise Exception(f"모든 접속 실패. 마지막 에러: {str(last_error)}")

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
        st.toast("🚀 스마트 검색 가동 (Premium)")
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
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 무엇이든 물어보세요."})

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
            
            # [자동 접속 실행]
            final_response, used_model = generate_with_auto_selection(full_prompt)
            
            msg_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            # 연결된 모델 이름 표시 (성공 확인용)
            st.caption(f"⚡ Connected to: {used_model}")
            
        except Exception as e:
            st.error("❌ 연결 실패")
            st.error(f"에러 메시지: {str(e)}")
            st.warning("⚠️ 유료 결제한 프로젝트의 API 키가 Secrets에 정확히 들어갔는지 확인해주세요.")








