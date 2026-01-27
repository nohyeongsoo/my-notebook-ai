import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# ==========================================
# [설정] 백과사전 파일 이름을 정확히 적어주세요!
# (GitHub에 업로드된 파일명)
ENCYCLOPEDIA_FILE = "jsbgocrc.pdf"
# ==========================================

# 1. 앱 기본 설정
st.set_page_config(page_title="홈 닥터 AI", page_icon="🏥")
st.title("🏥 내 손안의 주치의 (증상 백과사전)")
st.caption("증상을 입력하면 720페이지 의학 백과사전을 분석하여 답변합니다.")

# 2. 키 설정
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    else:
        st.error("비밀 금고에 키가 없습니다.")
        st.stop()
except:
    st.error("키 설정 오류")
    st.stop()

# 3. (핵심) 백과사전 통째로 읽어서 기억하기 (캐시 기능)
# @st.cache_resource는 이 무거운 작업을 '딱 한 번만' 하게 해줍니다.
@st.cache_resource
def load_encyclopedia(filename):
    text_content = ""
    try:
        if not os.path.exists(filename):
            return None
        
        # 파일을 엽니다
        with open(filename, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            # 페이지 한도 없이 전체를 다 읽습니다! (글자만 추출)
            # 그림은 버리고 글자만 가져오기 때문에 720페이지도 가능합니다.
            status_text = st.empty()
            status_text.info(f"📚 백과사전 {total_pages}페이지를 읽고 있습니다... 잠시만 기다려주세요.")
            
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            
            status_text.empty() # 로딩 메시지 삭제
            
    except Exception as e:
        st.error(f"책을 읽는 중 에러 발생: {e}")
        return None
        
    return text_content

# 4. 앱 시작 시 책 로드
if not os.path.exists(ENCYCLOPEDIA_FILE):
    st.error(f"⚠️ '{ENCYCLOPEDIA_FILE}' 파일을 찾을 수 없습니다. GitHub에 파일을 올려주세요.")
    st.stop()

# 여기서 책 내용을 불러옵니다 (이미 읽었다면 기억된 걸 가져옴)
full_text = load_encyclopedia(ENCYCLOPEDIA_FILE)

if full_text is None:
    st.stop()

st.success(f"✅ 백과사전 학습 완료! 증상을 말씀해 주세요.")

# 5. 채팅 화면
if "messages" not in st.session_state:
    st.session_state.messages = []
    # AI가 먼저 인사하기
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 어디가 불편하신가요? 증상을 자세히 말씀해 주시면 백과사전을 찾아보고 알려드릴게요."})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 질문 처리 (전체 검색)
if prompt := st.chat_input("예: 배가 아프고 열이 나요"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 백과사전을 검색 중입니다...")
        
        try:
            # [중요] 대용량 처리에 강한 1.5 Flash 모델 사용
            # (만약 404 에러가 나면 'gemini-2.5-flash'로 바꾸세요)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # AI에게 주는 명령 (프롬프트)
            full_prompt = f"""
            당신은 전문적인 가정의학과 AI 상담사입니다.
            아래 제공된 [의학 백과사전]의 내용을 바탕으로 사용자의 증상을 분석하고 조언해주세요.
            
            [규칙]
            1. 반드시 아래 제공된 백과사전 내용에 있는 정보만으로 답변하세요.
            2. 백과사전에 없는 내용이라면 "죄송합니다. 해당 증상은 책에서 찾을 수 없습니다."라고 말하세요.
            3. 사용자의 증상과 가장 관련 깊은 부분을 찾아서 원인, 대처법, 주의사항을 설명하세요.
            4. 말투는 친절하고 전문적인 의사 선생님처럼 하세요.

            [의학 백과사전 내용]
            {full_text}
            
            [사용자 증상]
            {prompt}
            """
            
            # 답변 생성
            response = model.generate_content(full_prompt)
            msg_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            if "429" in str(e):
                msg_placeholder.error("⚠️ 질문이 너무 많거나 책이 너무 길어서 잠시 멈췄습니다. 1분 뒤에 다시 시도해주세요.")
            elif "404" in str(e):
                msg_placeholder.error("⚠️ 모델 설정 오류: 코드에서 모델 이름을 'gemini-2.5-flash'로 바꿔보세요.")
            else:
                msg_placeholder.error(f"에러가 발생했습니다: {str(e)}")












