import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import os

# ==========================================
# [설정] 미리 심어둘 파일 이름을 여기에 적으세요!
# (GitHub에 이 파일이 반드시 같이 업로드되어 있어야 합니다)
DEFAULT_FILE_NAME = "jsbgocrc.pdf" 
# ==========================================

# 1. 앱 기본 설정
st.set_page_config(page_title="노짱의닥터AI", page_icon="🤖")
st.title("🤖 노짱의닥터AI")

# 2. 비밀 금고에서 키 꺼내기
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
    else:
        st.error("비밀 금고(Secrets)에 키가 없습니다.")
        st.stop()
except:
    st.error("Secrets 설정을 확인해주세요.")
    st.stop()

# 3. 문서 내용을 읽어오는 함수 (PDF, Word, TXT)
def get_text_from_file(file, filename):
    text = ""
    try:
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif filename.endswith(".docx"):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif filename.endswith(".txt"):
            text = file.read().decode("utf-8")
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    return text

# 4. 사이드바: 파일 업로드
with st.sidebar:
    st.header("📂 자료실")
    st.info(f"기본 탑재 문서: {DEFAULT_FILE_NAME}")
    st.write("---")
    st.write("다른 파일을 분석하고 싶다면 아래에 업로드하세요.")
    uploaded_file = st.file_uploader("새 파일 업로드 (PDF, Word, TXT)", type=['pdf', 'docx', 'txt'])

# 5. 어떤 파일을 쓸지 결정 (핵심 로직)
target_text = ""
source_name = ""

if uploaded_file:
    # 사용자가 파일을 올렸으면 우선 사용
    target_text = get_text_from_file(uploaded_file, uploaded_file.name)
    source_name = f"📂 업로드한 파일 ({uploaded_file.name})"
elif os.path.exists(DEFAULT_FILE_NAME):
    # 안 올렸으면 미리 심어둔 파일 사용
    with open(DEFAULT_FILE_NAME, "rb") as f:
        target_text = get_text_from_file(f, DEFAULT_FILE_NAME)
    source_name = f"📕 기본 탑재 문서 ({DEFAULT_FILE_NAME})"
else:
    # 둘 다 없으면
    st.warning(f"'{DEFAULT_FILE_NAME}' 파일을 찾을 수 없습니다. GitHub에 파일을 올려주세요.")
    st.stop()

# 화면에 현재 상태 표시
st.success(f"현재 **[{source_name}]** 내용을 학습했습니다. 질문해주세요!")

# 6. 채팅 인터페이스
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("궁금한 점을 물어보세요!"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # [중요] 선생님 목록에 있던 최신 모델 사용!
            model = genai.GenerativeModel('gemini-2.5-flash') 
            
            full_prompt = f"""
            다음은 문서의 내용입니다:
            {target_text}
            
            사용자의 질문: {prompt}
            
            위 문서 내용을 바탕으로 답변해주세요. 내용은 요약하지 말고 구체적으로 설명해주세요.
            """
            
            response = model.generate_content(full_prompt)
            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            # 145MB 파일 등 용량 문제로 에러가 나면 안내
            if "429" in str(e):
                st.error("⚠️ 파일 내용이 너무 많아서 AI가 한 번에 읽지 못했습니다. (무료 한도 초과)")
                st.info("팁: PDF 용량 줄이기 사이트에서 압축해서 올리거나, 파일을 나누어 올려주세요.")
            else:
                st.error(f"에러가 발생했습니다: {str(e)}")








