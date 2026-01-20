#!/usr/bin/env python3
"""
교육부 가이드 연동 테스트
"""

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
        "다문화가정 지원": ["다문화", "지원", "한국어", "통역"]
    }
    
    relevant_content = []
    for topic, topic_keywords in keywords.items():
        if any(keyword in query_lower for keyword in topic_keywords):
            relevant_content.append(f"[{topic}]\n{guide[topic]}")
    
    return "\n\n".join(relevant_content) if relevant_content else ""

if __name__ == "__main__":
    test_queries = [
        "가정통신문이 뭐예요?",
        "학부모 상담은 언제 하나요?",
        "다문화가정 지원이 있나요?",
        "준비물은 어디서 사나요?"
    ]
    
    print("교육부 가이드 검색 테스트:")
    for query in test_queries:
        print(f"\n질문: {query}")
        result = search_education_content(query)
        if result:
            print(f"답변: {result[:200]}...")
        else:
            print("관련 내용 없음")
