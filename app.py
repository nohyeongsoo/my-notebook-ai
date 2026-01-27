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
st.title("🏥 내 손안의 주치의 (무제한 버전)")

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

# 3. 스마트 검색 함수
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
    top_chunks = [chunk for score, chunk in relevant_chunks[:15]]
    return "\n...\n".join(top_chunks)

# 4. [핵심] 불굴의 답변 생성 함수 (자동 재시도 기능)
def generate_with_retry(model_name, prompt):
    # 최대 3번까지 다시 시도합니다.
    for attempt in range(3):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            # 429 에러(너무 빠름)가 뜨면 잠시 쉬었다가 다시 함
            if "429" in error_msg:
                time.sleep(3) # 3초 휴식
                continue # 다시 시도!
            else:
                raise e # 다른 에러면 그냥 멈춤
    raise Exception("서버가 너무 바쁩니다. 잠시 후 다시 시도해주세요.")

# 5. 사이드바 및 데이터 로드
with st.sidebar:
    st.header("📂 추가 자료 등록")
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
        st.error(f"파일 읽기 실패: {str(e)}")
        st.stop()
        
    if len(target_text) > 30000:
        use_smart_search = True
        st.toast("🚀 스마트 검색 모드 가동")
else:
    if encyclopedia_text:
        target_text = encyclopedia_text
        use_smart_search = True
    else:
        st.error("백과사전 파일이 없습니다.")
        st.stop()

# 6. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 증상을 입력하시면 백과사전에서 찾아드립니다."})

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

            # [최종 수정] 가장 널널한 모델 이름 사용
            # 선생님 목록에 있던 'gemini-flash-latest'는 1.5 버전의 별명입니다.
            # 이 모델은 하루 1,500회 무료입니다. (2.5는 20회였음)
            model_name = 'gemini-flash-latest'
            
            full_prompt = f"""
            문서 내용:
            {final_context}
            
            질문: {prompt}
            
            위 내용을 바탕으로 답변하세요.
            """
            
            # 여기서 '자동 재시도 함수'를 호출합니다!
            final_response = generate_with_retry(model_name, full_prompt)
            
            msg_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
        except Exception as e:
            st.error(f"❌ 에러 발생: {str(e)}")
            st.info("팁: 질문을 조금 더 구체적으로 적어주세요.")





















