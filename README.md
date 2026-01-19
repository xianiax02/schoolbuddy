# 다문화가정 도우미 🤝

한국 생활에 어려움을 겪는 결혼이주여성과 다문화가정을 위한 AI 기반 상담 챗봇입니다.

## 🎯 주요 기능

- **친근한 한국어 인터페이스**: 쉬운 한국어로 소통하는 사용자 친화적 인터페이스
- **다국어 지원**: 어려운 용어는 영어나 베트남어 병기로 이해도 향상
- **전문 분야별 상담**: 자녀교육, 의료/건강, 행정절차, 법률/복지 등 생활 전반 지원
- **실시간 AI 상담**: AWS Bedrock의 Amazon Nova Lite 모델을 활용한 즉시 답변
- **자주 묻는 질문**: 빠른 접근을 위한 카테고리별 FAQ 버튼
- **단계별 안내**: 복잡한 절차를 번호를 매겨 쉽게 설명

## 🛠️ 기술 스택

- **Frontend**: Streamlit (Python 웹 프레임워크)
- **AI Service**: AWS Bedrock (Amazon Nova Lite v1.0)
- **Cloud**: AWS (us-east-1 리전)
- **Language**: Python 3.8+

## 📋 사전 요구사항

1. **Python 3.8 이상**
2. **AWS 계정 및 자격 증명 설정**
   - AWS CLI 설정 또는 환경 변수 설정
   - Bedrock 서비스 액세스 권한 필요
3. **AWS Bedrock 모델 액세스**
   - Amazon Nova Lite 모델에 대한 액세스 권한 필요

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. AWS 자격 증명 설정

다음 중 하나의 방법으로 AWS 자격 증명을 설정하세요:

**방법 1: AWS CLI 사용**

```bash
aws configure
```

**방법 2: 환경 변수 설정**

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 3. 애플리케이션 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하여 애플리케이션을 사용할 수 있습니다.

## 💡 사용 방법

### STEP 1: 질문하기

1. **자주 묻는 질문 버튼 클릭**: 학교, 의료, 행정, 복지, 법률, 생활 관련 버튼 중 선택
2. **직접 질문 입력**: 궁금한 것을 자유롭게 한국어로 작성
3. **상황 정보 추가**: 더 정확한 답변을 위해 개인 상황 설명 (선택사항)

### STEP 2: AI 답변 확인

- "🤝 답변 받기" 버튼을 클릭
- AI가 실시간으로 친절하고 이해하기 쉬운 답변 생성
- 어려운 용어는 영어 병기, 복잡한 절차는 단계별 설명

## 📝 질문 예시

**학교 관련**: "가정통신문이 뭔가요? 어떻게 읽어야 하나요?"

**의료 관련**: "아이가 열이 나는데 병원에 어떻게 예약하나요?"

**행정 관련**: "외국인등록증 갱신 시기가 언제인가요?"

**복지 관련**: "다문화가족지원센터에서 어떤 프로그램이 있나요?"

## 🔧 주요 구성 요소

### 핵심 함수

- `get_bedrock_client()`: AWS Bedrock 클라이언트 초기화 및 캐싱
- `generate_response()`: 스트리밍 응답 처리 제너레이터

### AI 모델 설정

- **모델**: amazon.nova-lite-v1:0
- **최대 토큰**: 4096
- **Temperature**: 0.7
- **Top P**: 0.9

## ⚠️ 주의사항

1. **AWS 비용**: Bedrock API 사용 시 비용이 발생할 수 있습니다
2. **리전 설정**: 현재 us-east-1 리전으로 고정되어 있습니다
3. **모델 액세스**: Amazon Nova Lite 모델에 대한 액세스 권한이 필요합니다
4. **네트워크**: 안정적인 인터넷 연결이 필요합니다

## 🐛 문제 해결

### 일반적인 오류

**AWS 자격 증명 오류**

```
AWS 오류가 발생했습니다: The security token included in the request is invalid
```

→ AWS 자격 증명을 다시 설정하세요

**모델 액세스 오류**

```
AWS 오류가 발생했습니다: Access denied to model
```

→ AWS 콘솔에서 Bedrock 모델 액세스 권한을 확인하세요

**네트워크 연결 오류**

```
오류가 발생했습니다: Connection timeout
```

→ 인터넷 연결을 확인하고 다시 시도하세요

## 📄 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈로 등록해 주세요.

---

💡 **Tip**: 궁금한 것이 있으면 언제든지 물어보세요. 한국 생활이 더 편해지도록 도와드릴게요!
