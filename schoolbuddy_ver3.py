import os
import io
import time
import json
import boto3
import psycopg2
import requests
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# LangChain 및 AWS 연동
from langchain_aws import ChatBedrock, BedrockEmbeddings
from langchain_core.messages import HumanMessage

load_dotenv()

# --- [1] 서비스 초기화 ---
GENAI_API_KEY = "AIzaSyDb5XkJtwn9fsmMdY5CVeX76ke0wUh5cUc"
genai.configure(api_key=GENAI_API_KEY)
MODEL_NAME = 'models/gemini-2.5-flash'

@st.cache_resource
def init_aws():
    region = "us-west-2" 
    bedrock = boto3.client("bedrock-runtime", region_name=region)
    s3 = boto3.client('s3', region_name=region)
    return bedrock, s3

def get_db_conn():
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST'), database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'),
            port='5432', connect_timeout=3
        )
    except: return None

# --- [마케팅 데이터 로그 저장 함수] ---
def log_interaction(title, link):
    conn = get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO program_logs (user_lang, program_title, program_link) VALUES (%s, %s, %s)",
                (st.session_state.language, title, link)
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            st.error(f"Log Error: {e}")

# --- [실시간 번역 함수] ---
@st.cache_data(show_spinner=False, ttl=3600)
def translate_content(raw_json_str, target_lang):
    if target_lang == "한국어 (Korean)":
        return json.loads(raw_json_str)
    
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"Translate the following school notice JSON into {target_lang}. Respond ONLY with JSON. Fields: title, summary. Data: {raw_json_str}"
    try:
        response = model.generate_content(prompt)
        res_text = response.text
        json_str = res_text[res_text.find('{'):res_text.rfind('}')+1]
        return json.loads(json_str)
    except:
        return json.loads(raw_json_str)


# --- [2] UI/UX 설정 ---
# 1. 최상단으로 이동
st.set_page_config(page_title="School Buddy", page_icon="🎒", layout="wide")

# 2. 크롤링 함수 수정
@st.cache_data(ttl=3600)
def fetch_external_programs():
    url = "https://www.liveinkorea.kr/web/lay1/bbs/S1T10C27/A/4/list.do"
    programs = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 보내주신 HTML의 핵심 컨테이너 선택자
        items = soup.select(".tbl_type1_wrap dl.tbl_list_type1")
        
        for dl in items[:6]:
            # 2. 제목 추출: dt > a > span.title
            title_tag = dl.select_one("dt a span.title")
            # 3. 링크 추출: dt > a
            link_tag = dl.select_one("dt a")
            
            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                href = link_tag.get('href', '')
                # 상대 경로를 절대 경로로 변환
                link = "https://www.liveinkorea.kr/web/lay1/bbs/S1T10C27/A/4/" + href if not href.startswith('http') else href
                
                # 4. 날짜 추출: dd > ul.date_search > li (두 번째 li에 날짜가 있음)
                date = "N/A"
                date_items = dl.select("dd ul.date_search li")
                if len(date_items) >= 2:
                    # 텍스트 중 "2026-xx-xx" 패턴만 추출
                    import re
                    raw_date_text = date_items[1].get_text(strip=True)
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}.*', raw_date_text)
                    if date_match:
                        date = date_match.group()
                
                programs.append({
                    "title": title,
                    "link": link,
                    "date": date
                })
        
        return programs

    except Exception as e:
        st.error(f"데이터를 읽어오는 중 오류가 발생했습니다: {e}")
        return []

if 'language' not in st.session_state:
    st.session_state.language = '한국어 (Korean)'

lang_pack = {
    "한국어 (Korean)": {
        "title": "🏠 학교 소식 대시보드", "monitor_h3": "AI 가정통신문 분석", "monitor_p": "최근 소식을 확인하세요.",
        "status": "작동중", "recent": "📬 최근 소식", "no_data": "공지사항이 없습니다.",
        "date": "날짜", "sidebar_upload": "새 공지 등록", "upload_label": "PDF/이미지",
        "menu_program": "🌟 맞춤 프로그램 추천", "prog_desc": "다누리 지원센터의 최신 프로그램을 추천해 드립니다."
    },
    "English": {
        "title": "🏠 News Dashboard", "monitor_h3": "AI Document Analysis", "monitor_p": "Check recent updates.",
        "status": "Active", "recent": "📬 Recent News", "no_data": "No notices found.",
        "date": "Date", "sidebar_upload": "Upload Notice", "upload_label": "PDF/Image",
        "menu_program": "🌟 Program Recommendations", "prog_desc": "Recommended programs from Danuri Center."
    },
    "Tiếng Việt": {
        "title": "🏠 Bảng tin nhà trường", "monitor_h3": "Phân tích AI", "monitor_p": "Kiểm tra cập nhật mới nhất.",
        "status": "Đang hoạt động", "recent": "📬 Tin tức mới", "no_data": "Không có thông báo.",
        "date": "Ngày", "sidebar_upload": "Đăng ký thông báo", "upload_label": "PDF/Hình ảnh",
        "menu_program": "🌟 Đề xuất chương trình", "prog_desc": "Các chương trình mới nhất từ Trung tâm Danuri."
    },
    "中文": {
        "title": "🏠 学校仪表板", "monitor_h3": "AI 通信分析", "monitor_p": "查看最新更新。",
        "status": "运行中", "recent": "📬 最新消息", "no_data": "没有公告。",
        "date": "日期", "sidebar_upload": "注册通知", "upload_label": "PDF/图像",
        "menu_program": "🌟 项目推荐", "prog_desc": "来自 Danuri 中心的最新项目推荐。"
    }
}

curr_lang = lang_pack.get(st.session_state.language, lang_pack["한국어 (Korean)"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; background-color: #0E1117 !important; color: #E0E0E0 !important; }
[data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D !important; }
.notice-card { background-color: #1D1D1F !important; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.2rem; border-left: 5px solid #FF9800; }
.program-card { background-color: #1D1D1F !important; border-radius: 16px; padding: 1.2rem; border-left: 5px solid #4CAF50; transition: 0.3s; }
.mcp-monitor { background: rgba(46, 125, 50, 0.1); border-radius: 16px; padding: 1.2rem; display: flex; align-items: center; gap: 1rem; border: 1px solid #2E7D32; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

bedrock, s3 = init_aws()
if 'messages' not in st.session_state: st.session_state.messages = []
if 'current_page' not in st.session_state: st.session_state.current_page = 'dashboard'

# --- [3] 사이드바 ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><h1>🎒</h1><h2>School Buddy</h2></div>", unsafe_allow_html=True)
    lang_list = list(lang_pack.keys())
    selected_lang = st.selectbox("🌐 Language", options=lang_list, index=lang_list.index(st.session_state.language))
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()
    
    st.markdown("---")
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.current_page = 'dashboard'
    if st.button("💬 AI Chat", use_container_width=True): st.session_state.current_page = 'chat'
    if st.button(f"{curr_lang['menu_program']}", use_container_width=True): st.session_state.current_page = 'programs'
    
    st.markdown("---")
    st.markdown(f"### 📄 {curr_lang['sidebar_upload']}")
    uploaded_file = st.file_uploader(curr_lang['upload_label'], type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    if st.button("🚀 Analyze", use_container_width=True):
        if uploaded_file:
            with st.spinner("AI 분석 중..."):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                file_ext = file_name.split('.')[-1].lower()
                s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"raw/{file_name}", Body=file_bytes)
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    prompt = "Analyze this school notice and respond in JSON ONLY. Fields: title, summary(2 sentences), details(date)"
                    if file_ext in ['jpg', 'jpeg', 'png']:
                        img_data = {'mime_type': f'image/{file_ext.replace("jpg", "jpeg")}', 'data': file_bytes}
                        response = model.generate_content([prompt, img_data])
                    else:
                        import pypdf
                        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                        full_text = "".join([p.extract_text() for p in pdf_reader.pages])
                        response = model.generate_content(f"{prompt}\n\nContent: {full_text[:5000]}")
                    
                    res_text = response.text
                    json_str = res_text[res_text.find('{'):res_text.rfind('}')+1]
                    s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"analysis/{file_name}.json", Body=json_str)
                    st.success("등록 성공!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- [4] 메인 페이지 로직 ---

# A. 대시보드
if st.session_state.current_page == 'dashboard':
    st.title(curr_lang["title"])
    st.markdown(f'<div class="mcp-monitor">🔍 <b>{curr_lang["monitor_h3"]}</b>: {curr_lang["monitor_p"]} <span style="margin-left:auto;">● {curr_lang["status"]}</span></div>', unsafe_allow_html=True)
    
    try:
        response = s3.list_objects_v2(Bucket=os.getenv('BUCKET_NAME'), Prefix='analysis/')
        if 'Contents' in response:
            sorted_files = sorted([f for f in response['Contents'] if f['Key'] != 'analysis/'], key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_files[:3]:
                file_obj = s3.get_object(Bucket=os.getenv('BUCKET_NAME'), Key=obj['Key'])
                raw_json_str = file_obj['Body'].read().decode('utf-8')
                display_data = translate_content(raw_json_str, st.session_state.language)

                st.markdown(f"""
                <div class="notice-card">
                    <h4>📄 {display_data.get('title')}</h4>
                    <p>{display_data.get('summary')}</p>
                    <div style="font-size:0.85rem; color:#86868B;">📅 {curr_lang['date']}: <b>{display_data.get('details', {}).get('date')}</b></div>
                </div>
                """, unsafe_allow_html=True)
        else: st.info(curr_lang["no_data"])
    except: st.error("S3 Data Error")

# B. AI 채팅
elif st.session_state.current_page == 'chat':
    st.title("💬 AI Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if query := st.chat_input("Ask about school..."):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.markdown(query)
        with st.chat_message("assistant"):
            model = genai.GenerativeModel(MODEL_NAME)
            resp = model.generate_content(f"Answer in {st.session_state.language}. Context: school notice. Question: {query}")
            st.markdown(resp.text)
            st.session_state.messages.append({"role": "assistant", "content": resp.text})
            st.rerun()

# C. 프로그램 추천 (신규 기능)
elif st.session_state.current_page == 'programs':
    st.title(curr_lang['menu_program'])
    st.markdown(f"#### {curr_lang['prog_desc']}")
    programs = fetch_external_programs()
    
    if programs:
        for idx, pg in enumerate(programs):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div class="program-card">
                    <div style="font-weight:700; font-size:1.1rem;">{pg['title']}</div>
                    <div style="color:#86868B; font-size:0.85rem; margin-top:5px;">📅 {pg['date']}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.write("") 
                # [상세보기] 대신 바로 [링크 열기] 버튼 하나만 배치
                if st.button("🔗 프로그램 보기", key=f"pg_{idx}", use_container_width=True):
                    # 1. DB 로그 저장
                    log_interaction(pg['title'], pg['link'])
                    
                    # 2. JavaScript를 사용하여 새 창 열기
                    js = f"window.open('{pg['link']}')"
                    st.components.v1.html(f"<script>{js}</script>", height=0)
                    
                    st.success("로그 기록 후 페이지로 이동합니다.")
            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    else:
        st.warning("데이터를 불러오는 중이거나 목록이 없습니다.")

st.markdown("<br><hr><p style='text-align:center; color:#86868B; font-size:0.8rem;'>© 2026 School Buddy | Marketing Data Enabled</p>", unsafe_allow_html=True)