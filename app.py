import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# 1. 앱 제목 및 설정
st.set_page_config(page_title="나만의 노트북LM", page_icon="🤖")
st.title("🤖 내 노트북 AI 비서")
st.write("PDF 문서를 분석하고 답변해드립니다. (설정 완료)")

# 2. 비밀 금고에서 API 키 꺼내기
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        # 혹시 모를 에러 방지용
        st.error("비밀 금고 설정을 확인해주세요.")
        st.stop()
except FileNotFoundError:
    st.error("Secrets 파일을 찾을 수 없습니다.")
    st.stop()

# 3. 파일 업로드 기능
uploaded_file = st.file_uploader("PDF 파일을 선택하세요", type=['pdf'])

# 4. 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. 채팅 화면 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 사용자 질문 처리
if prompt := st.chat_input("궁금한 점을 물어보세요!"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            genai.configure(api_key=api_key)
            # 텍스트 모드 + 무료 모델 사용 (안전 모드)
            model = genai.GenerativeModel('gemini-1.5-flash') 
            
            context = ""
            if uploaded_file:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    context += page.extract_text() + "\n"
                
                full_prompt = f"""
                다음은 문서의 내용입니다:
                {context}
                
                사용자의 질문: {prompt}
                
                위 문서 내용을 바탕으로 답변해주세요.
                """
                response = model.generate_content(full_prompt)
            else:
                response = model.generate_content(prompt)

            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"에러가 발생했습니다: {str(e)}")

