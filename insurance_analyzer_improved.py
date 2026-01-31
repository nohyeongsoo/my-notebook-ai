import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import time
import pandas as pd
from datetime import datetime
import json

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="보험 약관 비교 분석 AI", 
    page_icon="⚖️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS로 UI 개선
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
    }
    .upload-box {
        border: 2px dashed #1f77b4;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background-color: #f0f8ff;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 헤더
# ==========================================
st.markdown('<div class="main-header">⚖️ 보험 약관 비교 분석 AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">여러 보험사의 약관을 한 번에 비교하고 핵심 보장 내용을 분석합니다</div>', unsafe_allow_html=True)

# ==========================================
# API 키 설정
# ==========================================
@st.cache_resource
def configure_api():
    """API 키 설정 (캐싱으로 성능 향상)"""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            return True
        else:
            st.error("🔑 Secrets에 GEMINI_API_KEY가 설정되지 않았습니다.")
            st.info("💡 Streamlit Cloud에서 Settings > Secrets에 API 키를 추가하세요.")
            return False
    except Exception as e:
        st.error(f"❌ API 키 설정 오류: {str(e)}")
        return False

if not configure_api():
    st.stop()

# ==========================================
# 유틸리티 함수들
# ==========================================

@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_bytes, filename):
    """PDF에서 텍스트 추출 (캐싱 적용)"""
    try:
        from io import BytesIO
        pdf_file = BytesIO(file_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        total_pages = len(pdf_reader.pages)
        
        for i, page in enumerate(pdf_reader.pages):
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        return text, total_pages, None
    except Exception as e:
        return "", 0, str(e)

def get_smart_context(full_text, query, max_chunks=15):
    """
    스마트 컨텍스트 검색 (개선된 버전)
    - 키워드 매칭 강화
    - TF-IDF 스타일 스코어링
    """
    if not full_text or not query:
        return ""
    
    chunk_size = 2500  # 더 큰 청크로 컨텍스트 향상
    overlap = 500  # 중복 영역 추가
    
    chunks = []
    for i in range(0, len(full_text), chunk_size - overlap):
        chunk = full_text[i:i+chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    
    # 검색어 전처리
    query_keywords = [word.lower() for word in query.split() if len(word) > 1]
    
    scored_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = 0
        
        # 키워드별 가중치 부여
        for keyword in query_keywords:
            count = chunk_lower.count(keyword)
            # 빈도가 높을수록 높은 점수
            score += count * (1 + len(keyword) / 10)
        
        if score > 0:
            scored_chunks.append((score, chunk))
    
    # 점수순 정렬
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 청크 선택
    top_chunks = [chunk for score, chunk in scored_chunks[:max_chunks]]
    
    return "\n\n━━━━━━━━━━━━━━━━━━\n\n".join(top_chunks)

def generate_ai_response(prompt, temperature=0.3):
    """
    AI 응답 생성 (폴백 모델 지원)
    """
    candidate_models = [
        "gemini-2.0-flash-exp",      # 최신 모델 우선
        "gemini-1.5-flash",          
        "gemini-1.5-flash-001",      
        "gemini-flash-latest"        
    ]
    
    generation_config = {
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }
    
    last_error = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            response = model.generate_content(prompt)
            
            # 안전 필터 체크
            if hasattr(response, 'prompt_feedback'):
                if response.prompt_feedback.block_reason:
                    continue
            
            return response.text, model_name
            
        except Exception as e:
            last_error = e
            continue
    
    raise Exception(f"모든 모델 시도 실패. 마지막 오류: {str(last_error)}")

def create_comparison_prompt(context, question, file_names):
    """
    비교 분석을 위한 최적화된 프롬프트 생성
    """
    prompt = f"""
당신은 **보험 약관 분석 전문가**입니다.

📋 **분석 대상 파일들**
{', '.join(file_names)}

📚 **제공된 약관 내용**
{context}

❓ **사용자 질문**
{question}

📊 **답변 형식 요구사항**

1. **비교 표 작성 필수**
   - 마크다운 표(Markdown Table) 형식 사용
   - 열 구성: `항목` | `보험사1` | `보험사2` | `보험사3` | `비고`
   - 각 셀은 간결하고 명확하게 작성

2. **핵심 차이점 강조**
   - 보장 금액, 보장 범위, 특약 등의 차이를 명확히 표시
   - 중요한 차이는 **굵은 글씨**로 강조

3. **정확성 우선**
   - 약관에 없는 내용은 절대 지어내지 말 것
   - 불명확한 부분은 "약관에 명시 안 됨" 표기

4. **추가 분석**
   - 표 아래에 핵심 인사이트 3가지 요약
   - 소비자 관점에서 주의할 점 언급

5. **시각적 구조화**
   - 이모지 활용으로 가독성 향상
   - 섹션별 구분 명확히

답변을 시작하세요:
"""
    return prompt

# ==========================================
# 사이드바 - 파일 업로드
# ==========================================
with st.sidebar:
    st.header("📂 약관 파일 업로드")
    
    st.markdown("""
    <div class="upload-box">
        <p>💼 여러 보험사 약관을 한 번에 선택하세요</p>
        <small>PDF 또는 TXT 파일 지원</small>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "파일 선택",
        type=['pdf', 'txt'],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)}개 파일 업로드 완료")
        
        # 파일 정보 표시
        with st.expander("📄 업로드된 파일 목록", expanded=True):
            for idx, file in enumerate(uploaded_files, 1):
                file_size = len(file.getvalue()) / 1024  # KB
                st.write(f"{idx}. **{file.name}** ({file_size:.1f} KB)")
    
    st.divider()
    
    # 분석 옵션
    st.subheader("⚙️ 분석 옵션")
    analysis_depth = st.select_slider(
        "분석 깊이",
        options=["빠른 분석", "표준", "상세 분석"],
        value="표준"
    )
    
    include_recommendations = st.checkbox("💡 추천 사항 포함", value=True)
    
    st.divider()
    
    # 사용 가이드
    with st.expander("📖 사용 가이드"):
        st.markdown("""
        **1단계**: 왼쪽에서 약관 파일 업로드
        
        **2단계**: 채팅창에 질문 입력
        - 예: "암 진단금 비교해줘"
        - 예: "수술비 차이를 표로 보여줘"
        
        **3단계**: AI 분석 결과 확인
        
        **팁**: 구체적인 질문이 더 정확한 답변을 받습니다!
        """)

# ==========================================
# 메인 영역
# ==========================================

if not uploaded_files:
    # 파일이 없을 때 안내 화면
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("👈 왼쪽 사이드바에서 약관 파일을 업로드해주세요")
        
        st.markdown("### 🎯 주요 기능")
        features = {
            "📊 자동 비교 표": "여러 약관을 한눈에 비교",
            "🤖 AI 분석": "핵심 차이점 자동 추출",
            "💬 대화형 인터페이스": "궁금한 점을 자유롭게 질문",
            "📈 시각화": "복잡한 정보를 쉽게 이해"
        }
        
        for feature, desc in features.items():
            st.markdown(f"**{feature}**: {desc}")
        
        st.markdown("### 💡 질문 예시")
        example_questions = [
            "암 진단금과 수술비를 보험사별로 비교해줘",
            "갱신형과 비갱신형의 차이가 뭐야?",
            "특약 내용을 표로 정리해줘",
            "보장 제외 항목은 어떤 게 있어?"
        ]
        
        for q in example_questions:
            st.code(q, language=None)
    
    st.stop()

# ==========================================
# 파일 처리 및 분석
# ==========================================

# 진행 상태 표시
progress_bar = st.progress(0)
status_text = st.empty()

combined_text = ""
file_names = []
file_stats = []

# 파일 읽기
status_text.text("📄 파일을 읽는 중...")
for idx, uploaded_file in enumerate(uploaded_files):
    progress = (idx + 1) / len(uploaded_files)
    progress_bar.progress(progress)
    
    file_names.append(uploaded_file.name)
    content = ""
    pages = 0
    error = None
    
    try:
        if uploaded_file.name.endswith(".pdf"):
            file_bytes = uploaded_file.getvalue()
            content, pages, error = extract_text_from_pdf(file_bytes, uploaded_file.name)
        else:
            content = uploaded_file.read().decode("utf-8")
            pages = len(content.split('\n'))
        
        if error:
            st.warning(f"⚠️ {uploaded_file.name}: {error}")
        
        # 파일별 구분자 추가
        combined_text += f"\n\n{'='*50}\n"
        combined_text += f"[파일: {uploaded_file.name}]\n"
        combined_text += f"{'='*50}\n\n"
        combined_text += content
        
        file_stats.append({
            "파일명": uploaded_file.name,
            "페이지/줄": pages,
            "크기": f"{len(uploaded_file.getvalue()) / 1024:.1f} KB",
            "글자수": len(content)
        })
        
    except Exception as e:
        st.error(f"❌ {uploaded_file.name} 처리 실패: {str(e)}")

progress_bar.empty()
status_text.empty()

# 통계 표시
if file_stats:
    st.success("✅ 모든 파일 처리 완료!")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 파일 수", len(file_stats))
    with col2:
        total_chars = sum(stat["글자수"] for stat in file_stats)
        st.metric("📝 총 글자 수", f"{total_chars:,}")
    with col3:
        total_size = sum(float(stat["크기"].replace(" KB", "")) for stat in file_stats)
        st.metric("💾 총 크기", f"{total_size:.1f} KB")
    with col4:
        st.metric("🎯 분석 준비", "완료")
    
    # 상세 통계 (접기 가능)
    with st.expander("📊 파일별 상세 정보"):
        df_stats = pd.DataFrame(file_stats)
        st.dataframe(df_stats, use_container_width=True)

st.divider()

# ==========================================
# 채팅 인터페이스
# ==========================================

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    
    welcome_msg = f"""
안녕하세요! 👋

총 **{len(file_names)}개의 약관**이 준비되었습니다:
{chr(10).join([f"• {name}" for name in file_names])}

궁금하신 내용을 자유롭게 질문해주세요!

**추천 질문:**
- "각 보험사의 암 진단금과 수술비를 비교해줘"
- "특약 내용의 차이점을 표로 보여줘"
- "보장 제외 항목은 뭐가 있어?"
"""
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome_msg
    })

# 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
if prompt := st.chat_input("💬 질문을 입력하세요... (예: 암 진단금 비교해줘)"):
    # 사용자 메시지 추가
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # AI 응답 생성
    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("🔍 약관을 분석하는 중...")
        
        try:
            # 분석 깊이에 따른 청크 수 조정
            chunk_map = {
                "빠른 분석": 8,
                "표준": 15,
                "상세 분석": 25
            }
            max_chunks = chunk_map.get(analysis_depth, 15)
            
            # 컨텍스트 추출
            with st.spinner("📚 관련 내용을 찾는 중..."):
                relevant_context = get_smart_context(
                    combined_text, 
                    prompt, 
                    max_chunks=max_chunks
                )
            
            if not relevant_context.strip():
                msg_placeholder.warning("⚠️ 질문과 관련된 내용을 찾을 수 없습니다. 다른 질문을 시도해보세요.")
                st.stop()
            
            # 프롬프트 생성
            analysis_prompt = create_comparison_prompt(
                relevant_context,
                prompt,
                file_names
            )
            
            # AI 응답 생성
            start_time = time.time()
            response_text, model_used = generate_ai_response(analysis_prompt)
            elapsed_time = time.time() - start_time
            
            # 응답 표시
            msg_placeholder.markdown(response_text)
            
            # 메타 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"⚡ 모델: {model_used}")
            with col2:
                st.caption(f"⏱️ 소요시간: {elapsed_time:.2f}초")
            with col3:
                st.caption(f"📏 분석 깊이: {analysis_depth}")
            
            # 추천 사항 추가
            if include_recommendations and "추천" not in prompt.lower():
                with st.expander("💡 AI 추천 사항"):
                    st.info("더 궁금한 점이 있으시면 구체적으로 질문해주세요!")
            
            # 메시지 저장
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text
            })
            
        except Exception as e:
            msg_placeholder.error("❌ 분석 중 오류가 발생했습니다")
            st.error(f"오류 세부정보: {str(e)}")
            
            # 에러 로깅
            if st.session_state.get("debug_mode", False):
                st.exception(e)

# ==========================================
# 푸터
# ==========================================
st.divider()
col1, col2, col3 = st.columns([2, 3, 2])
with col2:
    st.caption("⚖️ 보험 약관 비교 분석 AI | Powered by Google Gemini")
    st.caption("⚠️ 본 분석은 참고용이며, 최종 결정 시 약관 원문을 확인하세요")


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
st.title("🏥 내 손안의 주치의 (Premium)")

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

# 3. 스마트 검색 함수 (유료니까 넉넉하게 10개!)
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
    # 유료 회원이시니 정보를 더 많이(10개) 봅니다.
    top_chunks = [chunk for score, chunk in relevant_chunks[:10]]
    return "\n...\n".join(top_chunks)

# 4. [핵심] 만능 자동 접속 함수 (알아서 찾아냄)
def generate_with_auto_selection(prompt):
    # 시도할 모델 순서 (성능 좋고 안정적인 순서)
    candidate_models = [
        "gemini-1.5-flash",          # 1순위: 가장 표준적이고 빠름
        "gemini-1.5-flash-001",      # 2순위: 구버전 (안정성 甲)
        "gemini-2.0-flash-lite",     # 3순위: 신형 라이트
        "gemini-flash-latest"        # 4순위: 최후의 보루
    ]
    
    last_error = None
    
    for model_name in candidate_models:
        try:
            # 접속 시도
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, model_name # 성공 시 내용과 모델명 반환
            
        except Exception as e:
            last_error = e
            # 실패하면 다음 모델로 조용히 넘어감
            continue 

    # 모든 모델이 다 실패했을 때만 에러 뿜음
    raise Exception(f"모든 접속 실패. 마지막 에러: {str(last_error)}")

# 5. UI 및 로직
with st.sidebar:
    st.header("📂 자료 등록")
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
        st.error(f"읽기 실패: {str(e)}")
        st.stop()
        
    if len(target_text) > 30000:
        use_smart_search = True
        st.toast("🚀 스마트 검색 가동 (Premium)")
else:
    if encyclopedia_text:
        target_text = encyclopedia_text
        use_smart_search = True
    else:
        st.error("백과사전 파일 없음")
        st.stop()

# 6. 채팅창
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "안녕하세요. 무엇이든 물어보세요."})

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

            full_prompt = f"""
            문서 내용:
            {final_context}
            
            질문: {prompt}
            
            위 내용을 바탕으로 답변하세요.
            """
            
            # [자동 접속 실행]
            final_response, used_model = generate_with_auto_selection(full_prompt)
            
            msg_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            # 연결된 모델 이름 표시 (성공 확인용)
            st.caption(f"⚡ Connected to: {used_model}")
            
        except Exception as e:
            st.error("❌ 연결 실패")
            st.error(f"에러 메시지: {str(e)}")
            st.warning("⚠️ 유료 결제한 프로젝트의 API 키가 Secrets에 정확히 들어갔는지 확인해주세요.")
