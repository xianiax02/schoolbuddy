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
            with st.status("Analyzing school archives...", expanded=False) as status:
                docs = find_docs(query, bedrock)
                context = "\n\n".join(docs)
                status.update(label="Analysis complete", state="complete")
            
            prompt = f"""You are 'School Buddy', an intelligent assistant.
            [Context]: {context if context else 'No document match'}
            Style: Professional, helpful, concise. 
            Note: Parenthesize English terms. List actions clearly."""
            
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
        """, unsafe_allow_html=True)
    
    st.caption("Information is based on verified Ministry of Education guidelines.")

st.markdown("---")
st.caption("School Buddy. Designed for families. © 2026")