# Project System Prompt: schoolbuddy

## 1. Project Overview
- **Project Name:** schoolbuddy (Intelligent Assistant for Multicultural Parents)
- **Mission:** To bridge the information gap and educational divide for multicultural families in Korea. 
- **Core Strategy:** Go beyond "Simple Translation" to provide "Cultural Interpretation." We translate Korean school culture into the parents' native languages to help children adapt smoothly to school life.

## 2. Tech Stack
- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** React Native (Mobile App) / Next.js (Admin Dashboard)
- **AI / LLM:** Gemini API (Vision & Pro models)
- **Orchestration:** LangChain (LCEL)
- **Database:** PostgreSQL with `pgvector` extension
- **Monitoring/Automation:** Playwright (Python)
- **Infrastructure:** AWS Lambda (Triggers), Vercel (Hosting)

## 3. Core Functional Logic
### A. School Monitoring Loop
- Periodically crawl school websites using **Playwright**.
- Detect new announcements by comparing Post IDs in the database.
- Trigger an AWS Lambda function to process new images/PDFs via Gemini API.

### B. Vision-based Context Analysis
- Extract text from school newsletters (images/PDFs) using **Gemini Vision**.
- **Data Normalization:** Convert unstructured text into a structured JSON:
  ```json
  {
    "title": "String",
    "date": "YYYY-MM-DD",
    "cultural_context": "What idioms are hard for foreign parents",
    "main_text": "What should parents do"
  }

## 2. Detailed Service Workflow (User Journey)

### Phase 1: School Registration & Setup
1. **User Input:** The parent enters their child's school website URL in the app.
2. **System Action:** The backend validates the URL, saves the school profile, and performs an initial scan of the website structure.

### Phase 2: Automated Monitoring & Smart Summary
1. **Detection:** The system monitors the school's "Announcements" board. When a new post is detected:
   - The system navigates to the post and identifies image files (JPEG/PNG) containing newsletters.
2. **Analysis:** **Gemini Vision** reads the image using a specialized prompt designed for multicultural parents.
   - It doesn't just translate; it simplifies terms and adds cultural context (e.g., explaining 'School Banking' or 'Emergency Contact').
3. **Delivery:** - The simplified, translated content is uploaded to the **User Dashboard**.
   - A **Push Notification** is sent to the parent: "A new announcement has been posted! Here is what you need to prepare."

### Phase 3: On-demand Crawling & Dashboard Population
1. **Trigger:** The user clicks the **"Sync/Crawl"** button on the dashboard.
2. **Action:** The system crawls existing newsletters and various website tabs (e.g., School Meals, Academic Calendar).
3. **Result:** All historical and tab-specific data are translated and categorized into organized tabs on the **Dashboard** for easy access.

## 3. Tech Stack & Integration
- **Backend:** FastAPI (Handling triggers and data processing).
- **Automation:** Playwright (Monitoring school boards and extracting JPEGs).
- **Vision AI:** Gemini Pro Vision (Text extraction + Cultural simplification).
- **Push Service:** Firebase Cloud Messaging (FCM) or similar for real-time alerts.
- **Database:** PostgreSQL (Storing school URLs, post IDs, and translated content).

## 4. Specific Prompting Instructions for Gemini
- When summarizing newsletters, always include:
  1. **Core Info:** Title, Date, Location.
  2. **Must-Haves:** List of items the child needs to bring.
  3. **Cultural Tip:** A friendly explanation of the "why" behind the school activity.
  4. **Ease of Language:** Use 1st-grade level vocabulary for non-native speakers.

## 5. Coding Guidelines
- **Scraper:** Ensure Playwright can handle different school website layouts (Standardize selectors).
- **Concurrency:** Handle multiple school monitoring tasks efficiently using async Python.
- **UI/UX:** The dashboard should be tab-based (Announcements, Meals, Calendar, Guide).