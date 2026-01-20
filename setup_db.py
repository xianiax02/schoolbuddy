import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def create_table():
    try:
        # DB 연결
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port='5432'
        )
        cur = conn.cursor()

        # 테이블 생성 SQL 문
        create_table_query = """
        CREATE TABLE IF NOT EXISTS program_logs (
            id SERIAL PRIMARY KEY,
            user_lang TEXT,
            program_title TEXT,
            program_link TEXT,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cur.execute(create_table_query)
        conn.commit()
        print("✅ 테이블 'program_logs'가 성공적으로 생성되었습니다!")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_table()