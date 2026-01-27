import streamlit as st
import google.generativeai as genai
import PyPDF2
import docx
import os

# ==========================================
# [설정] 미리 심어둘 파일 이름 (수정하지 마세요)
DEFAULT_FILE_NAME = "jsbgocrc.pdf" 
# ==========================================

# 1. 앱 기본 설정
st.set_page_config(page_title="나만의 AI 비서", page_icon="🤖")
st.title("🤖 만능 문서 AI 비서 (안전 모드)")

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

# 3. 문서 내용을 읽어오는 함수 (★ 핵심 수정: 페이지 제한 기능)
def get_text_from_file(file, filename):
    text = ""
    try:
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file)
            # [안전장치] 무료 한도 초과 방지를 위해 앞부분 30페이지만 읽습니다.
            max_pages = 30 
            count = 0
            for i, page in enumerate(pdf_reader.pages):
                if i >= max_pages:
                    st.toast(f"⚠️ 파일이 너무 커서 앞부분 {max_pages}페이지만 읽었습니다.")
                    break
                text += page.extract_text() + "\n"
                count += 1
            
        elif filename.endswith(".docx"):
            doc = docx.Document(file)
            text = ""
            for i, para in enumerate(doc.paragraphs):
                if i >= 1000: break # 워드도 너무 길면 자름
                text += para.text + "\n"
                
        elif filename.endswith(".txt"):
            text = file.read().decode("utf-8")
            if len(text) > 30000: # 텍스트도 3만자 제한
                text = text[:30000]
                
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    return text

# 4. 사이드바: 파일 업로드
with st.sidebar:
    st.header("📂 자료실")
    st.info(f"기본 탑재 문서: {DEFAULT_FILE_NAME}")
    st.write("---")
    uploaded_file = st.file_uploader("새 파일 업로드", type=['pdf', 'docx', 'txt'])

# 5. 파일 로드 로직
target_text = ""
source_name = ""

if uploaded_file:
    target_text = get_text_from_file(uploaded_file, uploaded_file.name)
    source_name = f"📂 업로드한 파일 ({uploaded_file.name})"
elif os.path.exists(DEFAULT_FILE_NAME):
    with open(DEFAULT_FILE_NAME, "rb") as f:
        target_text = get_text_from_file(f, DEFAULT_FILE_NAME)
    source_name = f"📕 기본 탑재 문서 ({DEFAULT_FILE_NAME})"
else:
    st.warning(f"'{DEFAULT_FILE_NAME}' 파일을 찾을 수 없습니다.")
    st.stop()

st.success(f"현재 **[{source_name}]** 의 내용을 학습했습니다. (최대 30페이지)")

# 6. 채팅 인터페이스
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("질문해주세요!"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # 2.5 Flash 모델 사용
            model = genai.GenerativeModel('gemini-2.5-flash') 
            
            full_prompt = f"""
            다음은 문서의 내용입니다 (앞부분 발췌):
            {target_text}
            
            사용자의 질문: {prompt}
            
            위 문서 내용을 바탕으로 답변해주세요.
            """
            
            response = model.generate_content(full_prompt)
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            st.error("⚠️ 에러: 내용이 너무 길거나 AI가 바쁩니다. 잠시 후 다시 시도하거나, 더 짧은 파일을 사용하세요.")










