import os
import io
import time
import json
import boto3
import psycopg2
import requests
import pandas as pd  # 시각화를 위해 추가
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# LangChain 및 AWS 연동
from langchain_aws import BedrockEmbeddings

load_dotenv()

# --- [1] 서비스 및 보안 설정 ---
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)
MODEL_NAME = 'models/gemini-2.5-flash'

@st.cache_resource
def init_aws():
    region = "us-west-2" 
    bedrock = boto3.client("bedrock-runtime", region_name=region)
    s3 = boto3.client('s3', region_name=region)
    return bedrock, s3

@st.cache_resource
def get_embeddings_model():
    bedrock, _ = init_aws()
    return BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-text-v1")

def get_db_conn():
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
            port='5432', connect_timeout=3
        )
    except: return None

bedrock, s3 = init_aws()

# --- [2] 핵심 유틸리티 함수 ---

# 관리자용: 로그 데이터 가져오기
def fetch_logs():
    conn = get_db_conn()
    if conn:
        try:
            # 컬럼명을 created_at -> clicked_at 으로 변경
            query = "SELECT user_lang, program_title, program_link, clicked_at FROM program_logs"
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"데이터 조회 중 오류 발생: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(show_spinner=False, ttl=3600)
def translate_content(raw_json_str, target_lang):
    if target_lang == "한국어 (Korean)":
        return json.loads(raw_json_str)
    
    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    You are a professional JSON translation engine. 
    Translate the following JSON string into {target_lang}.
    Rules:
    - Translate ONLY the string values.
    - Preserve the original JSON structure and all keys ('title', 'summary', 'details') exactly.
    - Return valid JSON ONLY.
    
    JSON:
    {raw_json_str}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        return json.loads(raw_json_str)

def log_interaction(title, link):
    conn = get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO program_logs (user_lang, program_title, program_link) VALUES (%s, %s, %s)",
                (st.session_state.language, title, link)
            )
            conn.commit(); cur.close(); conn.close()
        except: pass

@st.cache_data(ttl=3600)
def fetch_external_programs():
    url = "https://www.liveinkorea.kr/web/lay1/bbs/S1T10C27/A/4/list.do"
    programs = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select(".tbl_type1_wrap dl.tbl_list_type1")
        for dl in items[:6]:
            title_tag = dl.select_one("dt a span.title")
            link_tag = dl.select_one("dt a")
            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                href = link_tag.get('href', '')
                link = "https://www.liveinkorea.kr/web/lay1/bbs/S1T10C27/A/4/" + href
                date = "N/A"
                date_items = dl.select("dd ul.date_search li")
                if len(date_items) >= 2: date = date_items[1].get_text(strip=True)
                programs.append({"title": title, "link": link, "date": date})
        return programs
    except: return []

# --- [3] UI/UX 설정 ---
st.set_page_config(page_title="School Buddy", page_icon="🎒", layout="wide")

# 세션 상태 초기화
if 'language' not in st.session_state: st.session_state.language = '한국어 (Korean)'
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# 최상단 관리자 스위치
col_t1, col_t2 = st.columns([8, 2])
with col_t2:
    st.session_state.admin_mode = st.toggle("🔒 Admin Mode", value=st.session_state.admin_mode)

lang_pack = {
    "한국어 (Korean)": {
        "title": "🏠 학교 소식 대시보드", "monitor_h3": "AI 가정통신문 분석", "monitor_p": "최근 소식을 확인하세요.",
        "status": "작동중", "date": "날짜", "sidebar_upload": "새 공지 등록", "upload_label": "PDF/이미지 선택",
        "chat_placeholder": "학교 생활에 대해 물어보세요...", "btn_analyze": "🚀 분석 및 DB 저장",
        "menu_program": "🌟 맞춤 프로그램 추천", "prog_desc": "다누리 지원센터의 최신 프로그램을 추천해 드립니다.",
        "admin_title": "📊 시스템 로그 분석"
    },
    "English": {
        "title": "🏠 News Dashboard", "monitor_h3": "AI Document Analysis", "monitor_p": "Check recent updates.",
        "status": "Active", "date": "Date", "sidebar_upload": "Upload Notice", "upload_label": "Select PDF/Image",
        "chat_placeholder": "Ask about school life...", "btn_analyze": "🚀 Analyze & Save",
        "menu_program": "🌟 Program Recommendations", "prog_desc": "Latest programs from Danuri Center.",
        "admin_title": "📊 System Log Analysis"
    },
    # ... (기타 언어 생략)
}
curr_lang = lang_pack.get(st.session_state.language, lang_pack["한국어 (Korean)"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; background-color: #0E1117 !important; color: #E0E0E0 !important; }
[data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D !important; }
.notice-card { background-color: #1D1D1F !important; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.2rem; border-left: 5px solid #FF9800; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
.mcp-monitor { background: rgba(46, 125, 50, 0.1); border-radius: 16px; padding: 1.2rem; display: flex; align-items: center; gap: 1rem; border: 1px solid #2E7D32; margin-bottom: 1.5rem; }
.admin-sidebar { background: #21262d; padding: 10px; border-radius: 10px; border: 1px solid #FF9800; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

if 'messages' not in st.session_state: st.session_state.messages = []
if 'current_page' not in st.session_state: st.session_state.current_page = 'dashboard'

# --- [4] 사이드바 로직 ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><h1>🎒</h1><h2>School Buddy</h2></div>", unsafe_allow_html=True)
    
    # 관리자 모드일 때 사이드바 상단에 시각화 대시보드 표시
    if st.session_state.admin_mode:
        st.markdown(f"### {curr_lang.get('admin_title', '📊 Admin Dashboard')}")
        df_logs = fetch_logs()
        if not df_logs.empty:
            # 1. 프로그램별 클릭 수 차트
            st.write("📈 **인기 프로그램 TOP 5**")
            top_programs = df_logs['program_title'].value_counts().head(5)
            st.bar_chart(top_programs)
            
            # 2. 언어별 사용자 분포
            st.write("🌐 **언어별 이용 현황**")
            lang_dist = df_logs['user_lang'].value_counts()
            st.write(lang_dist)
            
            # 3. 최근 로그 데이터 (정렬 기준을 clicked_at으로 변경)
            with st.expander("📄 상세 로그 보기"):
                # 정렬 기준 컬럼명도 clicked_at으로 수정
                st.dataframe(df_logs.sort_values(by='clicked_at', ascending=False), use_container_width=True)
        else:
            st.info("수집된 로그 데이터가 없습니다.")

        # 일반 메뉴
        selected_lang = st.selectbox("🌐 Language", options=list(lang_pack.keys()), index=list(lang_pack.keys()).index(st.session_state.language))
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            st.rerun()
    
    st.markdown("---")
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.current_page = 'dashboard'
    if st.button("💬 AI Chat", use_container_width=True): st.session_state.current_page = 'chat'
    if st.button(f"{curr_lang['menu_program']}", use_container_width=True): st.session_state.current_page = 'programs'
    
    st.markdown("---")
    uploaded_file = st.file_uploader(curr_lang['upload_label'], type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    if st.button(curr_lang['btn_analyze'], use_container_width=True, type="primary"):
        if uploaded_file:
            with st.spinner("이미지/PDF 분석 및 지식 베이스 등록 중..."):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                file_ext = file_name.split('.')[-1].lower()
                s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"raw/{file_name}", Body=file_bytes)
                
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    extracted_text = ""

                    if file_ext in ['jpg', 'jpeg', 'png']:
                        image_part = {"mime_type": f"image/{file_ext.replace('jpg', 'jpeg')}", "data": file_bytes}
                        ocr_prompt = "이 이미지에 포함된 모든 텍스트를 한국어로 정확히 읽어서 텍스트만 출력해줘."
                        ocr_res = model.generate_content([ocr_prompt, image_part])
                        extracted_text = ocr_res.text
                    else:
                        import pypdf
                        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                        extracted_text = "".join([p.extract_text() for p in pdf_reader.pages])

                    if extracted_text.strip():
                        analysis_prompt = f"Analyze notice. Respond in JSON ONLY. Fields: title, summary, details:{{date: 'YYYY-MM-DD'}}. Content: {extracted_text[:3000]}"
                        res = model.generate_content(analysis_prompt, generation_config={"response_mime_type": "application/json"})
                        s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"analysis/{file_name}.json", Body=res.text)
                        
                        embeddings_model = get_embeddings_model()
                        chunks = [extracted_text[i:i+1000] for i in range(0, len(extracted_text), 800)]
                        conn = get_db_conn()
                        if conn:
                            cur = conn.cursor()
                            for chunk in chunks:
                                vector = embeddings_model.embed_query(chunk)
                                cur.execute(
                                    "INSERT INTO documents (content, embedding, metadata) VALUES (%s, %s, %s)",
                                    (chunk, vector, json.dumps({"source": file_name, "type": file_ext}))
                                )
                            conn.commit(); cur.close(); conn.close()
                        st.success("✅ 분석 및 지식 베이스 등록 완료!")
                        st.rerun()
                    else:
                        st.error("텍스트를 추출할 수 없습니다.")
                except Exception as e: st.error(f"분석 오류: {e}")

# --- [5] 메인 화면 로직 (변경 없음) ---
# (대시보드, 채팅, 프로그램 추천 로직은 기존과 동일하게 유지됩니다)
if st.session_state.current_page == 'dashboard':
    st.title(curr_lang["title"])
    st.markdown(f'<div class="mcp-monitor">🔍 <b>{curr_lang["monitor_h3"]}</b>: {curr_lang["monitor_p"]} <span style="margin-left:auto;">● {curr_lang["status"]}</span></div>', unsafe_allow_html=True)
    
    try:
        response = s3.list_objects_v2(Bucket=os.getenv('BUCKET_NAME'), Prefix='analysis/')
        if 'Contents' in response:
            json_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.json')]
            sorted_files = sorted(json_files, key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_files[:3]:
                file_obj = s3.get_object(Bucket=os.getenv('BUCKET_NAME'), Key=obj['Key'])
                raw_json_str = file_obj['Body'].read().decode('utf-8')
                data = translate_content(raw_json_str, st.session_state.language)
                st.markdown(f"""
                <div class="notice-card">
                    <h4>📄 {data.get('title')}</h4>
                    <p>{data.get('summary')}</p>
                    <div style="font-size:0.85rem; color:#86868B;">📅 {curr_lang['date']}: <b>{data.get('details', {}).get('date')}</b></div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info("데이터가 없습니다.")
    except Exception as e: st.error(f"S3 데이터 로드 오류: {e}")

elif st.session_state.current_page == 'chat':
    st.title("💬 AI Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if query := st.chat_input(curr_lang['chat_placeholder']):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            with st.spinner("정보를 분석 중..."):
                embeddings_model = get_embeddings_model()
                query_vector = embeddings_model.embed_query(query)
                conn = get_db_conn()
                context_text = ""
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT content FROM documents ORDER BY embedding <-> %s::vector LIMIT 10", (query_vector,))
                    context_text = "\n\n".join([r[0] for r in cur.fetchall()])
                    cur.close(); conn.close()
                model = genai.GenerativeModel(MODEL_NAME)
                prompt = f"Answer in {st.session_state.language}. [Notice Context]:\n{context_text}\n\nQuestion: {query}"
                resp = model.generate_content(prompt)
                st.markdown(resp.text)
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
                st.rerun()

elif st.session_state.current_page == 'programs':
    st.title(curr_lang['menu_program'])
    st.markdown(f"#### {curr_lang['prog_desc']}")
    programs = fetch_external_programs()
    if programs:
        for idx, pg in enumerate(programs):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f'<div class="program-card"><b>{pg["title"]}</b><br><small>📅 {pg["date"]}</small></div>', unsafe_allow_html=True)
            with col2:
                if st.button("🔗 이동", key=f"pg_{idx}", use_container_width=True):
                    log_interaction(pg['title'], pg['link'])
                    st.components.v1.html(f"<script>window.open('{pg['link']}')</script>", height=0)
            st.markdown("<br>", unsafe_allow_html=True)

st.markdown("<br><hr><p style='text-align:center; color:#86868B; font-size:0.8rem;'>© 2026 School Buddy | Integrated Intelligence v1.0</p>", unsafe_allow_html=True)