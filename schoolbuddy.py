import os
import io
import time
import json
import boto3
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage
import pypdf

# Load Environment Variables
load_dotenv()

# --- [UI/UX] Page Configuration ---
st.set_page_config(
    layout="wide", 
    page_title="School Buddy", 
    page_icon=""
)

# --- [UI/UX] Pure Apple Style CSS (No Dark Navy) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;600&display=swap');
    
    /* 1. Base Body - Pure White & Apple Typography */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
        background-color: #FFFFFF !important;
        color: #1D1D1F; /* Apple Black */
    }

    /* 2. Sidebar - Light Neutral (Off-White) */
    [data-testid="stSidebar"] {
        background-color: #F5F5F7 !important;
        border-right: 1px solid #D2D2D7 !important;
    }
    
    /* 3. Hero Header - Clean & Airy */
    .hero-section {
        padding: 5rem 0 3rem 0;
        text-align: center;
        background-color: #FFFFFF;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        color: #1D1D1F;
    }
    .hero-subtitle {
        font-size: 1.5rem;
        color: #86868B; /* Apple Gray */
        font-weight: 400;
        margin-top: 0.5rem;
    }

    /* 4. Buttons - Pure Apple Style */
    .stButton>button {
        border-radius: 20px !important;
        border: none !important;
        background-color: #F5F5F7 !important;
        color: #0066CC !important; /* Apple Link Blue */
        font-weight: 500 !important;
        padding: 0.6rem 1.2rem !important;
        transition: background 0.2s ease !important;
    }
    .stButton>button:hover {
        background-color: #E8E8ED !important;
    }
    
    /* Primary Call-to-Action */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) .stButton>button {
        background-color: #0071E3 !important;
        color: #FFFFFF !important;
    }

    /* 5. Chat Interface - Light & Clean Bubbles */
    [data-testid="stChatMessage"] {
        background-color: #F5F5F7 !important;
        border-radius: 18px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.8rem !important;
    }
    
    /* User Message Differentiation */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageContent-user"]) {
        background-color: #FFFFFF !important;
        border: 1px solid #D2D2D7 !important;
    }

    /* 6. Info Cards - Clean Bordered Style */
    .apple-card {
        padding: 1.8rem;
        background-color: #FFFFFF;
        border-radius: 20px;
        border: 1px solid #D2D2D7;
        margin-bottom: 1.2rem;
    }
    .card-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #86868B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .card-value {
        font-size: 1.3rem;
        font-weight: 500;
        color: #1D1D1F;
        margin-top: 0.4rem;
    }

    /* Input Field Customization */
    .stChatInputContainer {
        border-radius: 25px !important;
        background-color: #F5F5F7 !important;
        border: 1px solid #D2D2D7 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [Logic] Infrastructure & Services (Unchanged) ---
@st.cache_resource
def init_aws():
    region = "us-west-2" 
    bedrock = boto3.client("bedrock-runtime", region_name=region)
    s3 = boto3.client('s3', region_name=region)
    return bedrock, s3

def get_db_conn():
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port='5432', connect_timeout=3
        )
    except: return None

def find_docs(query, bedrock_client):
    embeddings = BedrockEmbeddings(client=bedrock_client, model_id="amazon.titan-embed-text-v1", region_name="us-west-2")
    try:
        q_vector = embeddings.embed_query(query)
        conn = get_db_conn()
        if not conn: return []
        cur = conn.cursor()
        cur.execute("SELECT content FROM documents ORDER BY embedding <=> %s::vector LIMIT 3", (q_vector,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [r[0] for r in rows]
    except: return []

@st.cache_data
def load_education_guide():
    """교육부 학부모가이드 주요 내용 (수동 입력)"""
    return {
        "가정통신문": """
        가정통신문(家庭通信文)은 학교에서 가정으로 보내는 공식 안내문입니다.
        - 학교 행사, 준비물, 일정 변경 등을 안내
        - 반드시 확인 후 회신이 필요한 경우가 많음
        - 온라인(e-알리미, 클래스팅) 또는 종이로 발송
        - 중요한 내용은 번역 서비스 이용 권장
        """,
        
        "학부모 상담": """
        학부모 상담은 자녀의 학교생활을 점검하는 중요한 시간입니다.
        - 정기 상담: 학기별 1-2회 실시
        - 수시 상담: 필요시 담임교사와 약속
        - 상담 내용: 학습태도, 교우관계, 생활지도
        - 통역 서비스 신청 가능 (다문화가정 지원)
        """,
        
        "준비물": """
        학교 준비물 안내:
        - 교과서, 학용품, 체육복 등
        - 가정통신문으로 미리 안내
        - 학교 매점이나 인근 문구점에서 구매 가능
        - 경제적 어려움 시 교육복지 지원 신청
        """,
        
        "급식": """
        학교 급식 관련 정보:
        - 영양사가 작성한 균형잡힌 식단 제공
        - 알레르기 정보 사전 신고 필수
        - 종교적 이유로 특정 음식 제외 요청 가능
        - 급식비 지원 제도 있음 (저소득층 대상)
        """,
        
        "방과후학교": """
        방과후학교 프로그램:
        - 정규 수업 외 추가 교육 프로그램
        - 예체능, 학습, 돌봄 프로그램 운영
        - 유료/무료 프로그램 혼재
        - 신청서 작성 후 참여 가능
        """,
        
        "학교폭력": """
        학교폭력 예방 및 대응:
        - 학교폭력신고전화: 117
        - 담임교사, 상담교사에게 즉시 신고
        - 학교폭력대책자치위원회 운영
        - 피해학생 보호 및 가해학생 선도 조치
        """,
        
        "다문화가정 지원": """
        다문화가정을 위한 교육 지원:
        - 한국어 교육 프로그램 제공
        - 통역 서비스 지원
        - 문화 이해 교육 실시
        - 멘토링 프로그램 운영
        - 교육비 지원 제도 안내
        """
    }

def search_education_content(query):
    """교육 가이드에서 관련 내용 검색"""
    guide = load_education_guide()
    query_lower = query.lower()
    
    # 키워드 매칭
    keywords = {
        "가정통신문": ["가정통신문", "통신문", "안내문", "알림"],
        "학부모 상담": ["상담", "면담", "학부모상담"],
        "준비물": ["준비물", "학용품", "교과서", "체육복"],
        "급식": ["급식", "점심", "식사", "알레르기"],
        "방과후학교": ["방과후", "특별활동", "프로그램"],
        "학교폭력": ["폭력", "괴롭힘", "신고", "117"],
        "다문화가정 지원": ["다문화", "지원", "한국어", "통역"]
    }
    
    relevant_content = []
    for topic, topic_keywords in keywords.items():
        if any(keyword in query_lower for keyword in topic_keywords):
            relevant_content.append(f"[{topic}]\n{guide[topic]}")
    
    return "\n\n".join(relevant_content) if relevant_content else ""

# --- [Logic] Execution ---
bedrock, s3 = init_aws()
if 'messages' not in st.session_state: st.session_state.messages = []

# --- [UI/UX] Sidebar ---
with st.sidebar:
    st.markdown("### Library")
    st.markdown("Digitize materials for AI analysis.")
    uploaded_file = st.file_uploader("Upload PDF", type=['pdf'], label_visibility="collapsed")
    
    if st.button("Start Analysis"):
        if uploaded_file:
            with st.spinner("Analyzing..."):
                s3.upload_fileobj(io.BytesIO(uploaded_file.getvalue()), os.getenv('BUCKET_NAME'), uploaded_file.name)
                time.sleep(30)
                st.success("Complete")
                st.rerun()
    
    st.write("---")
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# --- [UI/UX] Main Dashboard ---
st.markdown("""
    <div class="hero-section">
        <div class="hero-title">School Buddy.</div>
        <div class="hero-subtitle">Intelligent support for every parent.</div>
    </div>
    """, unsafe_allow_html=True)

col_chat, col_info = st.columns([2.2, 0.8], gap="large")

with col_chat:
    st.markdown("##### Discover")
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("The Newsletter"): st.session_state.temp_query = "What is a School Newsletter(가정통신문)?"
    with nav2:
        if st.button("Health Guide"): st.session_state.temp_query = "Guide for school vaccinations(예방접종)."
    with nav3:
        if st.button("Registration"): st.session_state.temp_query = "How to renew my ID card(외국인등록증)?"

    st.write("")
    
    # Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    query = st.chat_input("Ask a question...")
    
    if hasattr(st.session_state, 'temp_query'):
        query = st.session_state.temp_query
        del st.session_state.temp_query

    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.write(query)

        with st.chat_message("assistant"):
            with st.status("교육부 가이드 및 학교 자료 분석 중...", expanded=False) as status:
                docs = find_docs(query, bedrock)
                education_guide = search_education_content(query)
                
                context = ""
                if education_guide:
                    context = f"교육부 학부모가이드 관련 내용:\n{education_guide}\n\n"
                if docs:
                    context += f"기타 학교 문서:\n{chr(10).join(docs)}"
                
                status.update(label="분석 완료", state="complete")
            
            prompt = f"""You are 'School Buddy', 다문화가정을 위한 지능형 교육 도우미입니다.

[참고 자료]: {context if context else '관련 문서를 찾을 수 없습니다'}

답변 지침:
- 교육부 학부모가이드의 내용을 최우선으로 참고하여 답변하세요
- 질문한 언어로 답변하되, 중요한 영어 용어는 괄호 안에 병기하세요
- 구체적이고 실용적인 정보를 제공하세요
- 필요시 단계별 안내를 제공하세요
- 다문화가정의 특수한 상황을 고려하여 답변하세요"""
            
            llm = ChatBedrock(client=bedrock, model_id="anthropic.claude-3-haiku-20240307-v1:0", region_name="us-west-2")
            response = llm.invoke([HumanMessage(content=prompt + f"\n\nQuestion: {query}")])
            st.markdown(response.content)
            st.session_state.messages.append({"role": "assistant", "content": response.content})

with col_info:
    st.markdown("##### Resources")
    
    st.markdown("""
        <div class="apple-card">
            <div class="card-label">Family Support Center</div>
            <div class="card-value">1577-5432</div>
        </div>
        <div class="apple-card">
            <div class="card-label">Immigration Service</div>
            <div class="card-value">1345</div>
        </div>
        <div class="apple-card">
            <div class="card-label">Knowledge Base</div>
            <div class="card-value">교육부 학부모가이드 연동</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption("Information is based on verified Ministry of Education guidelines.")

st.markdown("---")
st.caption("School Buddy. Designed for families. © 2026")