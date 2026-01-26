import streamlit as st
import google.generativeai as genai
import PyPDF2

# 1. 앱 제목 설정
st.set_page_config(page_title="나만의 노트북LM", page_icon="🤖")
st.title("🤖 내 노트북 AI 비서 (텍스트 모드)")
st.write("PDF 파일을 올리면, 내용을 분석해 답변해줍니다.")

# 2. 사이드바: API 키 입력받기
with st.sidebar:
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    st.markdown("---")
    st.markdown("Google AI Studio에서 발급받은 키를 입력해주세요.")

# 3. 파일 업로드 기능
uploaded_file = st.file_uploader("학습시킬 PDF 파일을 선택하세요", type=['pdf'])

# 4. 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. 채팅 화면 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. 사용자 질문 처리
if prompt := st.chat_input("내용에 대해 궁금한 점을 물어보세요!"):
    if not api_key:
        st.error("왼쪽 사이드바에 API Key를 먼저 입력해주세요!")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            genai.configure(api_key=api_key)
            
            # === [핵심] 텍스트 모드로 가장 안전한 모델 사용 ===
            # 목록에 있던 것 중 가장 무난한 모델
            model = genai.GenerativeModel('gemini-flash-latest') 
            
            context = ""
            if uploaded_file:
                # [우회법] 파일을 구글에 안 올리고, 여기서 직접 글자를 뺍니다.
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                for page in pdf_reader.pages:
                    context += page.extract_text() + "\n"
                
                # AI에게 줄 편지(프롬프트) 완성
                full_prompt = f"""
                다음은 문서의 내용입니다:
                {context}
                
                사용자의 질문: {prompt}
                
                위 문서 내용을 바탕으로 답변해주세요.
                """
                
                response = model.generate_content(full_prompt)
            else:
                # 파일이 없을 때는 그냥 질문만
                response = model.generate_content(prompt)

            full_response = response.text
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"에러가 발생했습니다: {str(e)}")