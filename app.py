import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import os

# ==========================================
# [설정 1] 미리 심어둘 파일 이름을 여기에 적으세요!
# (GitHub에 이 파일이 같이 올라가 있어야 합니다)
DEFAULT_FILE_NAME = "jsbgocrc.pdf" 
# ==========================================

# 1. 앱 기본 설정
st.set_page_config(page_title="노짱 AI 비서", page_icon="🤖")
st.title("🤖 노짱 AI 비서")

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

# 3. 문서 내용을 읽어오는 함수 (PDF, Word, TXT 지원)
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

# 4. 사이드바: 파일 업로드 (선택 사항)
with st.sidebar:
    st.header("📂 파일 업로드")
    st.write("파일을 올리면 그 내용을 분석하고, 안 올리면 기본 문서를 분석합니다.")
    uploaded_file = st.file_uploader("PDF, Word, TXT 파일", type=['pdf', 'docx', 'txt'])

# 5. 어떤 파일을 쓸지 결정 (핵심 로직!)
target_text = ""
source_name = ""

if uploaded_file:
    # 사용자가 파일을 올렸으면 그걸 사용
    target_text = get_text_from_file(uploaded_file, uploaded_file.name)
    source_name = "📂 업로드한 파일"
elif os.path.exists(DEFAULT_FILE_NAME):
    # 안 올렸지만, 미리 심어둔 파일이 있으면 그걸 사용
    with open(DEFAULT_FILE_NAME, "rb") as f:
        target_text = get_text_from_file(f, DEFAULT_FILE_NAME)
    source_name = f"📕 기본 탑재 문서 ({DEFAULT_FILE_NAME})"
else:
    # 둘 다 없으면
    st.warning("분석할 파일이 없습니다. 파일을 업로드하거나 소스 파일을 등록해주세요.")
    st.stop()

# 화면에 현재 어떤 파일을 보고 있는지 표시
st.info(f"현재 **[{source_name}]** 내용을 보고 있습니다.")

# 6. 채팅 인터페이스
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("내용에 대해 질문하세요!"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # 안전하고 빠른 모델 사용
            model = genai.GenerativeModel('gemini-1.5-flash') 
            
            full_prompt = f"""
            다음은 문서의 내용입니다:
            {target_text}
            
            사용자의 질문: {prompt}
            
            위 문서 내용을 바탕으로 친절하고 명확하게 답변해주세요.
            """
            
            response = model.generate_content(full_prompt)
            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")





