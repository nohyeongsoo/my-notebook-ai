import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 쪼개서 올린 백과사전 파일 목록
# (GitHub에 올린 파일 이름과 똑같이 적어주세요)
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

# 2. 책 읽기 함수 (한 번만 실행)
@st.cache_resource
def load_and_merge_books(file_list):
    full_text = ""
    status_text = st.empty()
    try:
        # 파일이 하나라도 있는지 확인
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

# 3. [핵심 기술] 스마트 검색 함수 (에러 해결사!)
# 질문과 관련된 내용만 뽑아냅니다.
def get_relevant_content(full_text, query):
    # 본문을 1000자 단위로 쪼갭니다
    chunk_size = 1000
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    relevant_chunks = []
    query_keywords = query.split() # 질문을 단어로 쪼갬
    
    for chunk in chunks:
        # 질문의 단어가 포함된 부분만 찾음
        score = 0
        for word in query_keywords:
            if word in chunk:
                score += 1
        
        if score > 0:
            relevant_chunks.append((score, chunk))
    
    # 가장 관련성 높은 순서로 정렬해서 상위 10개만 뽑음 (약 1만 자)
    # 이렇게 하면 AI에게 보내는 양이 확 줄어서 에러가 안 납니다!
    relevant_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for score, chunk in relevant_chunks[:15]]
    
    return "\n...\n".join(top_chunks)

# 4. 사이드바 (파일 업로드 기능 추가)
with st.sidebar:
    st.header("📂 추가 자료 등록")
    st.write("백과사전 외에 분석할 파일이 있다면 여기에 올리세요.")
    uploaded_file = st.file_uploader("개인 의료기록 등 (PDF/TXT)", type=['pdf', 'txt'])
    
    st.write("---")
    st.info(f"기본 탑재: 백과사전 (총 {len(BOOK_PARTS)}권)")

# 5. 데이터 로드 로직
encyclopedia_text = load_and_merge_books(BOOK_PARTS)
target_text = ""
source_info = ""

# 사용자가 파일을 올렸으면 그걸 우선으로, 아니면 백과사전을 사용
if uploaded_file:
    # 업로드 파일 읽기
    if uploaded_file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            target_text += page.extract_text() + "\n"
    else:
        target_text = uploaded_file.read().decode("utf-8")
    source_info = f"📂 업로드된 파일 ({uploaded_file.name})"
    use_smart_search = False # 업로드 파일은 짧으니까 전체 분석
else:
    # 백과사전 사용
    if encyclopedia_text:
        target_text = encyclopedia_text
        source_info = "📕 증상 백과사전 (전체)"
        use_smart_search = True # 백과사전은 너무 크니까 스마트 검색 사용!
    else:
        st.error("백과사전 파일이 없습니다. GitHub를 확인하세요.")
        st.stop()

# 6. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 증상을 말씀해 주시면 백과사전에서 찾아 알려드릴게요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("증상을 입력하세요 (예: 열이 나고 오한이 있어요)"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 관련 내용을 찾는 중...")
        
        try:
            # [중요] 스마트 검색 적용
            if use_smart_search:
                # 질문과 관련된 부분만 쏙 뽑아서 AI에게 줍니다.
                final_context = get_relevant_content(target_text, prompt)
                if not final_context:
                    final_context = "관련된 내용을 찾을 수 없습니다."
                    msg_placeholder.info("참고: 백과사전에서 정확한 키워드를 찾지 못했습니다. 증상을 더 자세히 적어보세요.")
            else:
                final_context = target_text

            # 2.5 모델 사용
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
            2. 문서에 없는 내용이면 "책에서 해당 증상에 대한 내용을 찾을 수 없습니다"라고 말하세요.
            3. 전문적이고 친절하게 설명하세요.
            """
            
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            msg_placeholder.error("⚠️ 잠시 연결이 원활하지 않습니다. (질문을 조금 더 구체적으로 해주세요)")















