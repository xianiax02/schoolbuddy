import os
import io
import time
import json
import boto3
import psycopg2
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# LangChain 및 AWS 연동
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.messages import HumanMessage

# 환경 변수 로드
load_dotenv()

# --- [1] 인프라 및 서비스 초기화 ---
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

def find_relevant_docs(query, bedrock_client):
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

# --- [2] UI/UX 설정 (가독성 개선 적용) ---
st.set_page_config(page_title="School Buddy", page_icon="🎒", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; }

/* Sidebar - Orange Gradient */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #FF9800 0%, #F57C00 100%) !important; }
[data-testid="stSidebar"] * { color: white !important; }

/* Dashboard Cards - 가독성 강화 수정 */
.notice-card { 
    background-color: #FFFFFF !important; 
    border-radius: 16px; 
    padding: 1.5rem; 
    margin-bottom: 1.2rem; 
    border-left: 8px solid #FF9800; /* 포인트를 더 두껍게 */
    box-shadow: 0 4px 15px rgba(0,0,0,0.1); /* 그림자 강조로 영역 구분 */
}

/* 제목: 아주 진한 검은색 */
.notice-card h4 { 
    color: #111111; 
    margin-top: 0; 
    margin-bottom: 10px;
    font-size: 1.25rem;
    font-weight: 800; 
}

/* 본문 요약: 진한 회색 */
.notice-card p { 
    color: #333333 !important; 
    line-height: 1.6; 
    font-size: 1rem;
    margin-bottom: 15px;
}

/* 하단 날짜 및 준비물: 명확한 대비 */
.notice-info { 
    display: flex; 
    gap: 20px; 
    border-top: 1px solid #EEEEEE; 
    padding-top: 10px;
    color: #444444 !important; 
    font-size: 0.9rem; 
}
.notice-info b { color: #000000 !important; }

/* Status Monitor */
.mcp-monitor { background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); border-radius: 16px; padding: 1.2rem; display: flex; align-items: center; gap: 1rem; border: 1px solid #A5D6A7; margin-bottom: 1.5rem; }
.mcp-monitor .status { margin-left: auto; background: #2E7D32; color: white; padding: 0.4rem 1rem; border-radius: 20px; font-size: 0.8rem; }

/* Chat Bubbles */
.chat-bubble { padding: 1rem; border-radius: 18px; margin-bottom: 0.5rem; max-width: 80%; line-height: 1.6; }
.user-bubble { background: #FF9800; color: white; margin-left: auto; border-radius: 18px 18px 4px 18px; }
.assistant-bubble { background: white; color: #333; border: 1px solid #EEE; border-radius: 18px 18px 18px 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
</style>
""", unsafe_allow_html=True)

bedrock, s3 = init_aws()
if 'messages' not in st.session_state: st.session_state.messages = []
if 'current_page' not in st.session_state: st.session_state.current_page = 'dashboard'
if 'language' not in st.session_state: st.session_state.language = '한국어 (Korean)'

# --- [3] 사이드바 내비게이션 및 업로드 ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><h1>🎒</h1><h2>School Buddy</h2><p>다문화가정 지능형 비서</p></div>", unsafe_allow_html=True)
    st.session_state.language = st.selectbox("🌐 Language / 언어", ["한국어 (Korean)", "English", "Tiếng Việt", "中文"])
    
    st.markdown("---")
    if st.button("🏠 대시보드", use_container_width=True): st.session_state.current_page = 'dashboard'
    if st.button("💬 AI 도우미", use_container_width=True): st.session_state.current_page = 'chat'
    if st.button("📖 용어사전", use_container_width=True): st.session_state.current_page = 'dictionary'
    
    st.markdown("---")
    st.markdown("### 📄 새로운 통신문 등록")
    uploaded_file = st.file_uploader("PDF 파일을 올려주세요", type=['pdf'], label_visibility="collapsed")
    
    if st.button("🚀 분석 및 저장", use_container_width=True):
        if uploaded_file:
            with st.spinner("AI가 통신문을 분석 중입니다..."):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"raw/{file_name}", Body=file_bytes)
                
                try:
                    import pypdf
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    full_text = "".join([p.extract_text() for p in pdf_reader.pages])

                    llm = ChatBedrock(client=bedrock, model_id="anthropic.claude-3-haiku-20240307-v1:0")
                    summary_prompt = f"다음 통신문을 분석하여 반드시 JSON으로만 답하세요. 필드: title, summary(2문장), details(date, items:[])\n\n내용: {full_text[:3000]}"
                    response = llm.invoke([HumanMessage(content=summary_prompt)])
                    
                    res_content = response.content
                    json_str = res_content[res_content.find('{'):res_content.rfind('}')+1]
                    s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"analysis/{file_name}.json", Body=json_str)
                    
                    st.success("분석 완료!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"오류 발생: {e}")

# --- [4] 메인 화면: 대시보드 (긴급 로직 제거 및 디자인 수정) ---
if st.session_state.current_page == 'dashboard':
    st.title("🏠 학교 소식 대시보드")
    
    st.markdown("""
    <div class="mcp-monitor">
        <div style="font-size: 2rem;">🔍</div>
        <div>
            <h3 style="margin:0; color: #2E7D32;">AI 가정통신문 분석</h3>
            <p style="margin:0; color: #558B2F;">최근 등록된 소식들을 확인하세요.</p>
        </div>
        <div class="status">● 작동중</div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📬 최근 소식")
    try:
        response = s3.list_objects_v2(Bucket=os.getenv('BUCKET_NAME'), Prefix='analysis/')
        if 'Contents' in response:
            sorted_files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_files[:3]:
                file_obj = s3.get_object(Bucket=os.getenv('BUCKET_NAME'), Key=obj['Key'])
                data = json.loads(file_obj['Body'].read().decode('utf-8'))
                
                # [수정] 긴급 로직 제거 및 진한 텍스트 컬러 적용
                st.markdown(f"""
                <div class="notice-card">
                    <h4>📄 {data.get('title')}</h4>
                    <p>{data.get('summary')}</p>
                    <div class="notice-info">
                        <span style="margin-right: 15px;">📅 날짜: <b>{data.get('details', {}).get('date')}</b></span>
                        <span>🎒 준비물: <b>{", ".join(data.get('details', {}).get('items', [])) if data.get('details', {}).get('items') else '없음'}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("아직 분석된 통신문이 없습니다.")
    except Exception:
        st.error("데이터를 불러오는 중 오류가 발생했습니다.")

# --- [5] 메인 화면: AI 채팅 ---
elif st.session_state.current_page == 'chat':
    st.title("💬 AI 도우미")
    for msg in st.session_state.messages:
        role_class = "user-bubble" if msg["role"] == "user" else "assistant-bubble"
        st.markdown(f'<div class="chat-bubble {role_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    if query := st.chat_input("궁금한 점을 물어보세요"):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("assistant"):
            with st.status("분석 중...", expanded=False):
                docs = find_relevant_docs(query, bedrock)
                context_text = "\n\n".join(docs)
            
            prompt = f"School Buddy assistant. Language: {st.session_state.language}. Context: {context_text}"
            llm = ChatBedrock(client=bedrock, model_id="anthropic.claude-3-haiku-20240307-v1:0")
            response = llm.invoke([HumanMessage(content=prompt + f"\n\nQuestion: {query}")])
            st.markdown(response.content)
            st.session_state.messages.append({"role": "assistant", "content": response.content})
            st.rerun()

# --- [6] 메인 화면: 용어 사전 ---
elif st.session_state.current_page == 'dictionary':
    st.title("📖 학교 용어 사전")
    terms = {"가정통신문": "학교 알림", "스쿨뱅킹": "교육비 납부", "알림장": "준비물 체크", "방과후학교": "특별 수업", "실내화": "교내 신발"}
    cols = st.columns(2)
    for i, (term, desc) in enumerate(terms.items()):
        with cols[i % 2]:
            st.markdown(f"<div style='background:white; padding:1.2rem; border-radius:12px; border:1px solid #EEE; margin-bottom:1rem;'><h4 style='color:#FF9800; margin:0;'>📌 {term}</h4><p style='color:#333;'>{desc}</p></div>", unsafe_allow_html=True)

st.markdown("<br><hr><p style='text-align:center; color:#999; font-size:0.8rem;'>© 2026 School Buddy</p>", unsafe_allow_html=True)