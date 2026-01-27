import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 쪼개서 올린 백과사전 파일 목록
# (GitHub 파일명과 일치해야 합니다)
BOOK_PARTS = [
    "jsbgocrc1.pdf",
    "jsbgocrc2.pdf",
    "jsbgocrc3.pdf",
    "jsbgocrc4.pdf"
]
# ==========================================

st.set_page_config(page_title="홈 닥터 AI", page_icon="🏥", layout="wide")
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

# 3. [핵심 기술] 스마트 검색 함수
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
    # 상위 15개 블록(약 1.5만 자)만 뽑아서 보냄
    top_chunks = [chunk for score, chunk in relevant_chunks[:15]]
    
    return "\n...\n".join(top_chunks)

# 4. 사이드바 (파일 업로드)
with st.sidebar:
    st.header("📂 추가 자료 등록")
    st.write("백과사전 대신 분석할 파일이 있다면 올리세요.")
    uploaded_file = st.file_uploader("파일 업로드 (PDF/TXT)", type=['pdf', 'txt'])
    
    st.write("---")
    st.info(f"기본 탑재: 백과사전 (총 {len(BOOK_PARTS)}권)")

# 5. 데이터 로드 및 '스마트 모드' 결정
encyclopedia_text = load_and_merge_books(BOOK_PARTS)
target_text = ""
source_info = ""
use_smart_search = False  # 기본값

if uploaded_file:
    # 업로드 파일 읽기
    if uploaded_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            target_text += page.extract_text() + "\n"
    else:
        target_text = uploaded_file.read().decode("utf-8")
        
    source_info = f"📂 업로드된 파일 ({uploaded_file.name})"
    
    # [수정된 핵심 로직] 
    # 업로드된 파일 글자수가 3만 자(약 20페이지)가 넘으면 자동으로 '스마트 검색' 켜기!
    if len(target_text) > 30000:
        use_smart_search = True
        st.toast("🚀 파일이 커서 '스마트 검색 모드'로 자동 전환되었습니다.")
    else:
        use_smart_search = False # 짧으면 그냥 통째로 분석
        
else:
    # 백과사전 사용
    if encyclopedia_text:
        target_text = encyclopedia_text
        source_info = "📕 증상 백과사전 (전체)"
        use_smart_search = True # 백과사전은 무조건 스마트 검색
    else:
        st.error("백과사전 파일이 없습니다.")
        st.stop()

# 6. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 증상을 말씀해 주시면 분석해 드릴게요."})

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
            # 스마트 검색 적용 여부에 따라 내용 자르기
            if use_smart_search:
                final_context = get_relevant_content(target_text, prompt)
                if not final_context:
                    final_context = "관련된 내용을 찾을 수 없습니다."
            else:
                final_context = target_text

            # 모델 호출
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            full_prompt = f"""
            당신은 의학 상담 AI입니다.
            아래 [문서 내용]을 근거로 답변하세요.

            [문서 내용 (발췌)]
            {final_context}
            
            [사용자 증상]
            {prompt}
            
            규칙:
            1. 제공된 문서 내용에 있는 정보만으로 답변하세요.
            2. 문서에 없는 내용이면 "해당 파일에서 관련 내용을 찾을 수 없습니다"라고 말하세요.
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            msg_placeholder.error("⚠️ 잠시 연결이 원활하지 않습니다. (질문을 조금 더 구체적으로 해주세요)")
















