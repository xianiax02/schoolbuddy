import streamlit as st
import boto3
from botocore.exceptions import ClientError

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="다문화가정 도우미", page_icon="🤝")

# --- 앱 제목 ---
st.title("🤝 다문화가정 도우미")
st.subheader("한국 생활의 궁금한 점을 쉽게 물어보세요. 친절하게 도와드릴게요!")

# --- 자주 묻는 질문 버튼들 ---
st.write("#### 🔍 자주 묻는 질문")
col_faq1, col_faq2, col_faq3 = st.columns(3)

with col_faq1:
    if st.button("📚 학교 관련"):
        st.session_state.quick_question = "가정통신문이 뭔가요?"
    if st.button("🏥 의료/건강"):
        st.session_state.quick_question = "아이 예방접종은 언제 받나요?"

with col_faq2:
    if st.button("📋 행정절차"):
        st.session_state.quick_question = "외국인등록증을 갱신하려면 어떻게 해야 하나요?"
    if st.button("💰 복지/지원"):
        st.session_state.quick_question = "다문화가족지원센터에서 어떤 도움을 받을 수 있나요?"

with col_faq3:
    if st.button("⚖️ 법률 상담"):
        st.session_state.quick_question = "이혼할 때 아이 양육권은 어떻게 되나요?"
    if st.button("🏠 생활 정보"):
        st.session_state.quick_question = "한국에서 집을 구할 때 주의할 점이 있나요?"

st.write("---")

# --- 입력 폼과 결과를 두 개의 컬럼으로 구성 ---
col1, col2 = st.columns([1, 1])

with col1:
    # --- 질문 입력 섹션 ---
    st.write("#### 💬 궁금한 것을 물어보세요")
    
    # 빠른 질문이 선택된 경우 자동으로 채우기
    default_question = ""
    if hasattr(st.session_state, 'quick_question'):
        default_question = st.session_state.quick_question
        del st.session_state.quick_question
    
    user_question = st.text_area(
        "**질문을 입력해주세요**",
        value=default_question,
        placeholder="예: 아이가 학교에서 가정통신문을 가져왔는데 뭔지 모르겠어요...",
        height=200
    )
    
    # 상황 정보 (선택사항)
    st.write("**추가 정보 (선택사항)**")
    situation_info = st.text_area(
        "상황을 더 자세히 알려주시면 더 정확한 답변을 드릴 수 있어요",
        placeholder="예: 초등학교 1학년 아이가 있고, 한국에 온 지 2년 되었어요",
        height=100
    )


# --- Bedrock 클라이언트 생성 함수 ---
@st.cache_resource
def get_bedrock_client():
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return client


# --- 스트리밍 응답을 처리하는 생성기 함수 ---
def generate_response(prompt):
    """
    Bedrock API를 호출하고 스트리밍 응답의 텍스트 청크를 반환하는 생성기 함수.
    """
    client = get_bedrock_client()
    model_id = "amazon.nova-lite-v1:0"

    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]

    try:
        streaming_response = client.converse_stream(
            modelId=model_id,
            messages=conversation,
            inferenceConfig={"maxTokens": 4096, "temperature": 0.7, "topP": 0.9},
        )

        for chunk in streaming_response["stream"]:
            if "contentBlockDelta" in chunk:
                yield chunk["contentBlockDelta"]["delta"]["text"]

    except ClientError as e:
        st.error(f"AWS 오류가 발생했습니다: {e.response['Error']['Message']}")
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")


with col2:
    # --- 답변 출력 섹션 ---
    st.write("#### 💡 답변")

    if st.button("🤝 답변 받기", type="primary"):
        if not user_question.strip():
            st.error("❌ 질문을 입력해 주세요!")
        else:
            # --- AI 프롬프트 생성 ---
            system_prompt = """
당신은 한국에 거주하는 결혼이주여성과 다문화가정을 돕는 친절하고 전문적인 상담사입니다. 제공된 '2025년 공교육 진입 안내(우리아이 학교보내기)' 자료를 바탕으로, 이주배경 학부모가 한국 학교 시스템을 완벽히 이해하고 자녀를 지원할 수 있도록 돕습니다.

**역할과 목표:**
- 한국 생활과 학교 문화가 낯선 결혼이주여성들을 위해 PDF 속의 복잡한 교육 용어와 행정 절차를 누락 없이 상세하면서도 따뜻하고 공감적인 어조로 친절하게 설명
- 한국 공교육 시스템과 제도를 학부모의 눈높이에서 실용적이고 정확하게 설명하며, 어려운 한자어나 행정 용어를 일상적인 표현으로 바꾸어 누구나 쉽게 이해할 수 있도록 설명
- 단순한 정보 전달에 그치지 않고 학부모가 학교 서류 제출이나 입학 준비 등 실제 상황에서 당장 무엇을 어떻게 해야 하는지 구체적인 행동 방법을 명확히 제시

**답변 스타일:**
1. 쉬운 한국어 사용 ('취학', '배부', '수행' 등 어려운 한자어 대신 '학교에 가다', '나눠주다', '활동하다'와 같은 쉬운 동사 위주로 설명하고 필요하면 영어나 베트남어 병기)
2. 복잡한 절차는 단계별로 번호를 매겨서 설명
3. 구체적인 연락처나 웹사이트 정보 제공
3. 어려운 학교 용어 뒤에는 반드시 괄호로 영어 병기 (예: 가정통신문(School Newsletter))
4. 공감과 격려의 메시지 포함

**주요 지원 분야:**
- 자녀 교육 (학교 시스템, 가정통신문, 학부모 참여)
- 의료/건강 (병원 이용, 예방접종, 건강보험)
- 행정절차 (외국인등록증, 비자, 각종 신청)
- 법률/복지 (이혼, 양육권, 지원 제도)
- 일상생활 (주거, 쇼핑, 문화 적응)

**답변 형식:**
질문받은 모든 학교 용어나 제도는 반드시 아래의 **'3단계 설명법'**이 포함되도록 작성하세요. 각 단계는 줄바꿈이나 기호를 사용하여 명확히 구분되어야 합니다.

- ① 무슨 뜻인가요?: 이 용어가 일상생활에서 어떤 의미인지 아주 쉽게 풀어서 설명
- ② 왜 중요한가요?: 이 내용이 아이의 학교 생활(성적, 출석, 적응 등)에 왜 중요한지 이유를 설명
- ③ 부모님은 무엇을 해야 하나요?: 부모님이 서류를 제출하거나 학교에 방문하는 등 지금 당장 또는 앞으로 해야 할 행동을 구체적으로 안내

"""

            full_prompt = f"{system_prompt}\n\n질문: {user_question}"
            if situation_info.strip():
                full_prompt += f"\n\n상황 정보: {situation_info}"
            
            full_prompt += "\n\n위 질문에 대해 친절하고 이해하기 쉽게 답변해 주세요."

            # --- Bedrock API 호출 및 실시간 출력 ---
            st.info("🤖 답변을 준비하고 있어요...")

            response_placeholder = st.empty()
            full_response = response_placeholder.write_stream(
                generate_response(full_prompt)
            )

# --- 하단 정보 박스 ---
st.write("---")

# --- 유용한 연락처 정보 ---
st.write("#### 📞 유용한 연락처")
col_contact1, col_contact2, col_contact3 = st.columns(3)

with col_contact1:
    st.info("""
    **다문화가족지원센터**
    📞 1577-5432
    🌐 www.liveinkorea.kr
    """)

with col_contact2:
    st.info("""
    **외국인종합안내센터**
    📞 1345 (24시간)
    🗣️ 20개 언어 지원
    """)

with col_contact3:
    st.info("""
    **법무부 출입국**
    📞 1345
    🌐 www.immigration.go.kr
    """)

st.success("""
💝 **언제든지 궁금한 것이 있으면 물어보세요!** 
한국 생활이 어려우실 텐데, 조금이라도 도움이 되었으면 좋겠어요. 
혼자 고민하지 마시고 언제든 다시 찾아와 주세요. 🤗
""")
