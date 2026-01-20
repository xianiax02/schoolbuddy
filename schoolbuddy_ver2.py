import os
import io
import time
import json
import boto3
import psycopg2
import streamlit as st
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# LangChain 및 AWS Bedrock 연동
from langchain_aws import BedrockEmbeddings

load_dotenv()

# --- [1] 서비스 초기화 ---
GENAI_API_KEY = "AIzaSyDb5XkJtwn9fsmMdY5CVeX76ke0wUh5cUc"
genai.configure(api_key=GENAI_API_KEY)
MODEL_NAME = 'models/gemini-2.5-flash'

@st.cache_resource
def init_resources():
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
            port='5432', 
            connect_timeout=5
        )
    except Exception as e:
        st.error(f"DB 연결 실패: {e}")
        return None

bedrock, s3 = init_resources()

# --- [2] 실시간 번역 ---
@st.cache_data(show_spinner=False, ttl=3600)
def translate_content(raw_json_str, target_lang):
    if target_lang == "한국어 (Korean)":
        return json.loads(raw_json_str)
    
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = f"Translate this school notice JSON into {target_lang}. Respond ONLY with JSON. Data: {raw_json_str}"
    try:
        response = model.generate_content(prompt)
        res_text = response.text
        json_str = res_text[res_text.find('{'):res_text.rfind('}')+1]
        return json.loads(json_str)
    except:
        return json.loads(raw_json_str)

# --- [3] UI/UX 설정 ---
st.set_page_config(page_title="School Buddy", page_icon="🎒", layout="wide")

if 'language' not in st.session_state:
    st.session_state.language = '한국어 (Korean)'

lang_pack = {
    "한국어 (Korean)": {"title": "🏠 학교 소식 대시보드", "date": "날짜", "sidebar_upload": "새 공지 등록", "upload_label": "PDF/이미지 선택", "chat_placeholder": "학교 생활에 대해 물어보세요...", "btn_analyze": "🚀 분석 및 DB 저장"},
    "English": {"title": "🏠 School Dashboard", "date": "Date", "sidebar_upload": "Upload Notice", "upload_label": "Select PDF/Image", "chat_placeholder": "Ask about school life...", "btn_analyze": "🚀 Analyze & Save"},
    "Tiếng Việt": {"title": "🏠 Bảng tin nhà trường", "date": "Ngày", "sidebar_upload": "Đăng ký thông báo", "upload_label": "Chọn PDF/Hình ảnh", "chat_placeholder": "Hỏi về cuộc sống học đường...", "btn_analyze": "🚀 Phân tích & Lưu"},
    "中文": {"title": "🏠 学校仪表板", "date": "日期", "sidebar_upload": "注册通知", "upload_label": "选择 PDF/图像", "chat_placeholder": "询问学校生活...", "btn_analyze": "🚀 분석 및 DB 저장"}
}
curr_lang = lang_pack.get(st.session_state.language, lang_pack["한국어 (Korean)"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; background-color: #0E1117 !important; color: #E0E0E0 !important; }
[data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D !important; }
.notice-card { background-color: #1D1D1F !important; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.2rem; border-left: 5px solid #FF9800; }
</style>
""", unsafe_allow_html=True)

if 'messages' not in st.session_state: st.session_state.messages = []
if 'current_page' not in st.session_state: st.session_state.current_page = 'dashboard'

# --- [4] 사이드바: 인제션 (S3 + RDS Vector DB) ---
with st.sidebar:
    st.markdown("<div style='text-align: center;'><h1>🎒</h1><h2>School Buddy</h2></div>", unsafe_allow_html=True)
    selected_lang = st.selectbox("🌐 Language", options=list(lang_pack.keys()), index=list(lang_pack.keys()).index(st.session_state.language))
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()
    
    st.markdown("---")
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.current_page = 'dashboard'
    if st.button("💬 AI Chat", use_container_width=True): st.session_state.current_page = 'chat'
    
    st.markdown("---")
    st.markdown(f"### 📄 {curr_lang['sidebar_upload']}")
    uploaded_file = st.file_uploader(curr_lang['upload_label'], type=['pdf', 'jpg', 'png', 'jpeg'], label_visibility="collapsed")
    
    if st.button(curr_lang['btn_analyze'], use_container_width=True, type="primary"):
        if uploaded_file:
            with st.spinner("AI 분석 및 벡터 저장 중..."):
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"raw/{file_name}", Body=file_bytes)
                
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    prompt = "Analyze this school notice. Respond in JSON ONLY. Fields: title, summary(2 sentences), details:{date: 'YYYY-MM-DD'}"
                    
                    if file_name.lower().endswith(('pdf')):
                        import pypdf
                        pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                        full_text = "".join([p.extract_text() for p in pdf_reader.pages])
                        response = model.generate_content(f"{prompt}\n\nContent: {full_text[:5000]}")
                    else:
                        img_data = {'mime_type': 'image/jpeg', 'data': file_bytes}
                        response = model.generate_content([prompt, img_data])
                    
                    json_str = response.text[response.text.find('{'):response.text.rfind('}')+1]
                    s3.put_object(Bucket=os.getenv('BUCKET_NAME'), Key=f"analysis/{file_name}.json", Body=json_str)
                    
                    # 벡터 임베딩 생성 (Bedrock Titan)
                    analysis_data = json.loads(json_str)
                    # 검색 정확도를 높이기 위해 제목과 요약을 합쳐서 벡터화 
                    text_to_embed = f"공지 제목: {analysis_data.get('title')}\n요약: {analysis_data.get('summary')}"
                    embeddings_model = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-text-v1")
                    vector = embeddings_model.embed_query(text_to_embed)
                    
                    # RDS에 벡터 데이터 저장
                    conn = get_db_conn()
                    if conn:
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO documents (content, embedding, metadata) VALUES (%s, %s, %s)",
                            (text_to_embed, vector, json.dumps({"source": file_name, "date": analysis_data.get('details', {}).get('date')}))
                        )
                        conn.commit()
                        cur.close(); conn.close()
                    
                    st.success("✅ RAG 지식 베이스 등록 완료!")
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- [5] 대시보드 ---
if st.session_state.current_page == 'dashboard':
    st.title(curr_lang["title"])
    try:
        response = s3.list_objects_v2(Bucket=os.getenv('BUCKET_NAME'), Prefix='analysis/')
        if 'Contents' in response:
            sorted_files = sorted([f for f in response['Contents'] if f['Key'] != 'analysis/'], key=lambda x: x['LastModified'], reverse=True)
            for obj in sorted_files[:5]:
                file_obj = s3.get_object(Bucket=os.getenv('BUCKET_NAME'), Key=obj['Key'])
                display_data = translate_content(file_obj['Body'].read().decode('utf-8'), st.session_state.language)
                st.markdown(f'<div class="notice-card"><h4>📄 {display_data.get("title")}</h4><p>{display_data.get("summary")}</p><small>📅 {display_data.get("details", {}).get("date")}</small></div>', unsafe_allow_html=True)
    except: st.error("Data Error")

# --- [6] AI 채팅: 시맨틱 검색 최적화 ---
elif st.session_state.current_page == 'chat':
    st.title("💬 AI School Assistant")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if query := st.chat_input(curr_lang['chat_placeholder']):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"): st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("지식 베이스를 심층 분석하고 있습니다..."):
                # 1. 질문 임베딩
                embeddings_model = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-text-v1")
                query_vector = embeddings_model.embed_query(query)
                
                # 2. 벡터 검색 강화 (Top-K = 15) 
                conn = get_db_conn()
                context_text = ""
                if conn:
                    cur = conn.cursor()
                    # 15개의 문맥을 가져와서 이름 누락 방지 
                    cur.execute("SELECT content FROM documents ORDER BY embedding <-> %s::vector LIMIT 15", (query_vector,))
                    rows = cur.fetchall()
                    # 검색 결과가 많을 때 LLM이 헷갈리지 않게 순서 정렬 
                    context_text = "\n\n".join([f"공지 내용: {r[0]}" for r in rows])
                    cur.close(); conn.close()

                # 3. 답변 생성: 가이드라인 강화 
                model = genai.GenerativeModel(MODEL_NAME)
                prompt = f"""
                당신은 학교 도우미입니다. 답변 언어는 {st.session_state.language}입니다.
                아래 제공된 [공지사항] 내용에만 근거하여 질문에 답하세요. 
                
                **답변 가이드**:
                1. 문서 내에 구체적인 앱 이름이나 소프트웨어 명칭이 '제목'이나 '본문'에 포함되어 있는지 철저히 확인하세요.
                2. 질문에서 예시로 든 이름이 아닌, 실제 [공지사항] 텍스트 안에 존재하는 고유 명사를 답하세요.
                3. 만약 공지사항에서 두 가지 주요 소프트웨어를 소개하고 있다면, 그 이름을 반드시 명시하세요.
                
                [공지사항]:
                {context_text}
                
                질문: {query}
                """
                resp = model.generate_content(prompt)
                st.markdown(resp.text)
                st.session_state.messages.append({"role": "assistant", "content": resp.text})

st.markdown("<br><hr><p style='text-align:center; color:#86868B; font-size:0.8rem;'>© 2026 School Buddy | Full RAG Integration</p>", unsafe_allow_html=True)