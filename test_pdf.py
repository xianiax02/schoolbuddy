#!/usr/bin/env python3
"""
교육부 학부모가이드.pdf 연동 테스트
"""
import pypdf

def load_pdf_guide():
    """교육부 학부모가이드.pdf 파일을 읽어서 텍스트 반환"""
    pdf_path = "교육부 학부모가이드.pdf"
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            pages_with_content = 0
            
            # 처음 100페이지 중 내용이 있는 페이지 찾기
            for i, page in enumerate(pdf_reader.pages[:100]):
                page_text = page.extract_text()
                if page_text and page_text.strip() and len(page_text.strip()) > 50:
                    text += f"[페이지 {i+1}]\n{page_text}\n\n"
                    pages_with_content += 1
                    if pages_with_content >= 10:  # 내용이 있는 10페이지만
                        break
            
            print(f"내용이 있는 페이지 수: {pages_with_content}")
            return text
    except Exception as e:
        return f"PDF 로드 오류: {str(e)}"

def search_pdf_content(query, pdf_content):
    """PDF 내용에서 쿼리와 관련된 부분 검색"""
    if not pdf_content or "PDF 로드 오류" in pdf_content:
        return ""
    
    query_lower = query.lower()
    lines = pdf_content.split('\n')
    relevant_lines = []
    
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in query_lower.split()):
            start = max(0, i-2)
            end = min(len(lines), i+3)
            relevant_lines.extend(lines[start:end])
            relevant_lines.append("---")
    
    return '\n'.join(relevant_lines[:50])

if __name__ == "__main__":
    print("교육부 학부모가이드.pdf 로딩 테스트...")
    pdf_content = load_pdf_guide()
    
    if "PDF 로드 오류" in pdf_content:
        print(f"오류: {pdf_content}")
    else:
        print(f"PDF 로드 성공! 내용 길이: {len(pdf_content)} 문자")
        print("\n첫 500자 미리보기:")
        print(pdf_content[:500])
        
        # 검색 테스트
        test_queries = ["학교", "교육", "학부모", "가정통신문"]
        for test_query in test_queries:
            print(f"\n'{test_query}' 검색 결과:")
            search_result = search_pdf_content(test_query, pdf_content)
            if search_result:
                print(search_result[:200] + "...")
            else:
                print("검색 결과 없음")
