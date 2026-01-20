import streamlit as st
import os
from datetime import datetime
from pathlib import Path

# --- 1. 기본 설정 및 경로 ---
# 업로드된 파일이 저장될 폴더 (DB 대신 사용)
UPLOAD_DIR = Path("school_notices")
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="서울행복초등학교", page_icon="🏫", layout="centered")

# --- 2. 디자인 (CSS) ---
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .notice-item {
        padding: 15px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 헤더 영역 ---
st.markdown("""
    <div class="main-header">
        <h1 style="color: #1565C0; margin-bottom: 0;">🏫 서울행복초등학교</h1>
        <p style="color: #666;">우리 아이들의 행복한 배움터</p>
    </div>
""", unsafe_allow_html=True)

# --- 4. 메뉴 구성 (탭) ---
tab_list, tab_upload = st.tabs(["📢 공지사항 목록", "✍️ 공지 등록하기"])

# --- 탭 1: 공지사항 목록 ---
with tab_list:
    st.subheader("최신 공지사항")
    
    # 폴더 내 PDF 파일 가져오기 (최신순)
    notices = sorted(
        [f for f in UPLOAD_DIR.glob("*.pdf")],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if not notices:
        st.info("등록된 공지사항이 없습니다.")
    else:
        for pdf in notices:
            col1, col2 = st.columns([4, 1])
            with col1:
                # 파일명과 등록 날짜 표시
                date_str = datetime.fromtimestamp(pdf.stat().st_mtime).strftime('%Y-%m-%d')
                st.markdown(f"**{pdf.name}**")
                st.caption(f"📅 등록일: {date_str}")
            with col2:
                with open(pdf, "rb") as f:
                    st.download_button("보기", f, file_name=pdf.name, key=str(pdf))
            st.markdown("---")

# --- 탭 2: 공지 등록하기 ---
with tab_upload:
    st.subheader("새 공지 작성")
    st.write("가정통신문이나 안내문을 PDF 파일로 업로드해 주세요.")
    
    uploaded_file = st.file_uploader("파일을 선택하세요", type=['pdf'], label_visibility="collapsed")
    
    if uploaded_file is not None:
        # 파일 정보 미리보기
        st.info(f"선택된 파일: {uploaded_file.name}")
        
        # 게시 버튼
        if st.button("🚀 공지 게시하기", type="primary"):
            # 1. 파일 저장
            file_path = UPLOAD_DIR / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 2. 효과 알림
            st.success("🎉 게시 완료!")
            st.balloons()
            
            # 3. 알림 후 목록 갱신을 위해 잠시 대기 (선택 사항)
            st.info("잠시 후 목록에 반영됩니다.")

# --- 하단 정보 ---
st.markdown("""
    <div style="text-align: center; color: #999; margin-top: 5rem; font-size: 0.8rem;">
        서울행복초등학교 행정실 | School Buddy 연동 시스템
    </div>
""", unsafe_allow_html=True)