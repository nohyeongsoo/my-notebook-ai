import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 기본 탑재 백과사전 파일 목록
BOOK_PARTS = [
    "jsbgocrc1.pdf",
    "jsbgocrc2.pdf",
    "jsbgocrc3.pdf",
    "jsbgocrc4.pdf"
]
# ==========================================

st.set_page_config(page_title="홈 닥터 AI", page_icon="🏥", layout="wide")
st.title("🏥 내 손안의 주치의 (정밀 진단 모드)")

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

# 4. 사이드바 (파일 업로드)
with st.sidebar:
    st.header("📂 추가 자료 등록")
    uploaded_file = st.file_uploader("파일 업로드 (PDF/TXT)", type=['pdf', 'txt'])
    st.info(f"기본 탑재: 백과사전 (총 {len(BOOK_PARTS)}권)")

# 5. 데이터 로드 및 검증
encyclopedia_text = load_and_merge_books(BOOK_PARTS)
target_text = ""
source_info = ""
use_smart_search = False

if uploaded_file:
    # 업로드 파일 읽기
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
        st.error(f"❌ 파일 읽기 실패: {str(e)}")
        st.stop()
        
    source_info = f"📂 업로드된 파일 ({uploaded_file.name})"
    
    # [진단 1] 텍스트가 텅 비었는지 확인 (스캔본 체크)
    if len(target_text.strip()) == 0:
        st.error("⚠️ 경고: 파일에서 글자를 하나도 읽지 못했습니다!")
        st.warning("혹시 '이미지로 된 스캔 파일(사진)'인가요? 이 앱은 '글자(텍스트)'가 포함된 PDF만 읽을 수 있습니다.")
        st.stop()
        
    # [진단 2] 용량에 따른 모드 전환
    if len(target_text) > 30000:
        use_smart_search = True
        st.toast(f"🚀 파일이 큽니다({len(target_text)}자). 스마트 검색을 켭니다.")
    else:
        use_smart_search = False

else:
    # 백과사전 사용
    if encyclopedia_text:
        target_text = encyclopedia_text
        source_info = "📕 증상 백과사전 (전체)"
        use_smart_search = True
    else:
        st.error("백과사전 파일이 없습니다.")
        st.stop()

# 6. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 증상을 분석해 드릴게요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 정밀 분석 중...")
        
        try:
            if use_smart_search:
                final_context = get_relevant_content(target_text, prompt)
                if not final_context or len(final_context.strip()) == 0:
                    msg_placeholder.warning("⚠️ 파일에서 질문과 관련된 단어를 찾지 못했습니다. (검색 결과 없음)")
                    # 검색 실패 시, AI에게 그냥 일반 지식으로라도 답하게 할지 선택
                    final_context = "관련 내용을 찾을 수 없습니다."
            else:
                final_context = target_text

            model = genai.GenerativeModel('gemini-2.5-flash')
            
            full_prompt = f"""
            문서 내용:
            {final_context}
            
            질문: {prompt}
            
            위 내용을 바탕으로 답변하세요.
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            # [진단 3] 에러 메시지를 숨기지 않고 그대로 보여줌!
            error_msg = str(e)
            st.error(f"❌ 에러가 발생했습니다!")
            st.code(error_msg) # 빨간 박스로 에러 코드 출력
            
            if "429" in error_msg:
                st.info("💡 힌트: '하루 무료 사용량'을 초과했거나, '너무 빨리' 질문해서 그렇습니다.")
            elif "400" in error_msg:
                st.info("💡 힌트: 질문 내용이나 파일 내용에 문제가 있습니다.")
            elif "Empty" in error_msg:
                st.info("💡 힌트: AI에게 보낼 내용이 텅 비어있습니다. (스캔 파일 가능성)")

















