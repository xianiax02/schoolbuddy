import streamlit as st
import os
import io
import json
import boto3
import psycopg2
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings

# 환경 변수 로드
load_dotenv()

# --- 1. 서비스 초기화 (로직 유지) ---
GENAI_API_KEY = os.getenv('GENAI_API_KEY')
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
            port='5432', connect_timeout=3
        )
    except: return None

bedrock, s3 = init_resources()
UPLOAD_DIR = Path("school_notices")
UPLOAD_DIR.mkdir(exist_ok=True)

# --- 2. 페이지 설정 및 디자인 (UI/UX 개편) ---
st.set_page_config(page_title="서울행복초 관리 시스템", page_icon="🏫", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    
    /* Main Header */
    .main-header {
        background: linear-gradient(135deg, #1A237E 0%, #283593 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Card Style */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f1f3f9;
        border-radius: 10px 10px 0 0;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #1A237E !important; color: white !important; }
    
    /* Info Box */
    .status-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1A237E;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 사이드바 (시스템 상태) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2602/2602414.png", width=80)
    st.title("Admin Panel")
    st.info("서울행복초등학교\n가정통신문 통합 관리 시스템")
    
    st.divider()
    st.subheader("🌐 시스템 연결 상태")
    
    # DB 체크
    conn = get_db_conn()
    if conn:
        st.success("✅ Database Connected")
        conn.close()
    else:
        st.error("❌ Database Offline")
        
    # AWS 체크
    try:
        s3.list_buckets()
        st.success("✅ AWS S3 Linked")
    except:
        st.error("❌ AWS Connection Failed")
        
    st.divider()
    st.caption(f"Last Login: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 4. 메인 콘텐츠 ---
st.markdown("""
    <div class="main-header">
        <h1 style='margin:0; color:white;'>🏫 서울행복초등학교 관리자 포털</h1>
        <p style='opacity:0.8;'>가정통신문 데이터베이스 관리 시스템</p>
    </div>
""", unsafe_allow_html=True)

tab_list, tab_upload = st.tabs(["📂 공지사항 보관함", "📤 신규 공지 등록"])

# [탭 1: 공지사항 목록]
with tab_list:
    st.markdown("### 📝 게시된 가정통신문 현황")
    st.caption("파일 목록")
    
    try:
        bucket_name = os.getenv('BUCKET_NAME')
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='raw/')
        
        if 'Contents' in response:
            # 테이블 헤더
            cols = st.columns([0.1, 0.5, 0.2, 0.2])
            cols[0].write("**번호**")
            cols[1].write("**파일명**")
            cols[2].write("**등록일자**")
            cols[3].write("**상태**")
            st.divider()
            
            for idx, obj in enumerate(sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)):
                if obj['Key'] == 'raw/': continue
                file_name = obj['Key'].replace('raw/', '')
                date_str = obj['LastModified'].strftime('%Y-%m-%d')
                
                with st.container():
                    c1, c2, c3, c4 = st.columns([0.1, 0.5, 0.2, 0.2])
                    c1.write(f"{idx}")
                    c2.write(f"📄 **{file_name}**")
                    c3.write(date_str)
                    c4.markdown("`분석완료` ✅")
                    st.divider()
        else:
            st.info("현재 등록된 공지사항이 없습니다.")
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

# [탭 2: 등록 및 Gemini 분석]
with tab_upload:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 파일 업로드")
        st.write("이미지(JPG, PNG) 또는 PDF 파일을 업로드하세요.")
        uploaded_file = st.file_uploader("", type=['pdf', 'jpg', 'jpeg', 'png'])
        
        if uploaded_file:
            st.info(f"선택된 파일: {uploaded_file.name}")
            process_btn = st.button("🚀 서버 전송 및 AI 분석 시작", type="primary", use_container_width=True)

    with col2:
        st.markdown("### 🤖 AI 분석 가이드")
        st.success("""
            **분석 프로세스:**
            1. **S3 원본 저장**: 파일 보안 스토리지 저장
            2. **Gemini 2.5 Flash**: 텍스트 추출 및 요약
            3. **JSON 정제**: 핵심 내용 구조화 (JSON)
            4. **Vector DB**: Titan Embedding을 통한 RAG 연동
        """)

    if uploaded_file and process_btn:
        with st.status("데이터 처리 중...", expanded=True) as status:
            try:
                file_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                file_ext = file_name.split('.')[-1].lower()
                bucket_name = os.getenv('BUCKET_NAME')

                # 1. S3 원본 저장
                st.write("1. 스토리지 업로드 중...")
                s3.put_object(Bucket=bucket_name, Key=f"raw/{file_name}", Body=file_bytes)
                
                # 2. Gemini 모델 분석
                st.write("2. Gemini AI 분석 중 (Vision/NLP)...")
                model = genai.GenerativeModel(MODEL_NAME)
                analysis_content = ""

                if file_ext in ['jpg', 'jpeg', 'png']:
                    img_data = {'mime_type': f'image/{file_ext.replace("jpg", "jpeg")}', 'data': file_bytes}
                    prompt = "이 학교 가정통신문 이미지를 상세히 읽고 JSON 형식으로만 답해줘. 필드: title, summary(2문장), details(date, items:[])"
                    response = model.generate_content([prompt, img_data])
                    analysis_content = response.text
                else:
                    import pypdf
                    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    full_text = "".join([p.extract_text() for p in pdf_reader.pages])
                    prompt = f"이 텍스트를 분석해서 JSON 형식으로만 답해줘. 필드: title, summary(2문장), details(date, items:[])\n\n내용: {full_text[:5000]}"
                    response = model.generate_content(prompt)
                    analysis_content = full_text

                # 3. JSON 정제 및 S3 저장
                st.write("3. 분석 결과 구조화 중...")
                res_text = response.text
                json_str = res_text[res_text.find('{'):res_text.rfind('}')+1]
                s3.put_object(Bucket=bucket_name, Key=f"analysis/{file_name}.json", Body=json_str)

                # 4. 벡터 DB 저장
                st.write("4. 벡터 데이터베이스(RAG) 인덱싱 중...")
                embeddings = BedrockEmbeddings(client=bedrock, model_id="amazon.titan-embed-text-v1")
                vector = embeddings.embed_query(analysis_content[:3000] if analysis_content else "이미지 분석 내용")
                
                conn = get_db_conn()
                if conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO documents (content, embedding, metadata) VALUES (%s, %s, %s)", 
                        (analysis_content[:3000], vector, json.dumps({"source": file_name, "type": file_ext}))
                    )
                    conn.commit()
                    cur.close(); conn.close()

                status.update(label="✅ 모든 처리가 완료되었습니다!", state="complete", expanded=False)
                st.balloons()
                
                # 결과 미리보기 카드
                st.markdown(f"""
                    <div class="status-card">
                        <h4 style='color:#1A237E; margin-top:0;'>✅ 등록 완료</h4>
                        <p><b>파일명:</b> {file_name}</p>
                        <p>이제 학부모용 챗봇에서 해당 공지사항에 대한 질문이 가능합니다.</p>
                    </div>
                """, unsafe_allow_html=True)

            except Exception as e:
                status.update(label="❌ 처리 오류 발생", state="error")
                st.error(f"상세 오류: {e}")

# --- 5. 푸터 ---
st.markdown("---")
st.caption("© 2024 서울행복초등학교 행정실 | AI Assistant Powered by Gemini 2.5 Flash")