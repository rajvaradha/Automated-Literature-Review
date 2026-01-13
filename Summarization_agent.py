import mysql.connector
from mysql.connector import Error
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import os
import sys
import re
import time

GCP_PROJECT_ID = "" 
GCP_LOCATION = "us-central1" 
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'agentic_ai_db'
}

try:
    if GCP_PROJECT_ID:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    else:
        print(" WARNING: GCP_PROJECT_ID is not set. API calls will fail.")
except Exception as e:
    print(f" Error initializing Vertex AI: {e}")

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f" DATABASE ERROR: {e}")
    return None

def get_papers_to_summarize(connection):
    cursor = connection.cursor(dictionary=True)
    query = """
        SELECT id, title, full_text 
        FROM papers1 
        WHERE full_text IS NOT NULL 
        AND (abstract IS NULL OR abstract NOT LIKE '%Introduction:%'); 
    """
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results

def update_paper_with_summary(connection, paper_id, summary):
    cursor = connection.cursor()
    
    query = "UPDATE papers1 SET abstract = %s WHERE id = %s" 
    
    try:
        cursor.execute(query, (summary, paper_id))
        connection.commit()
        print(f"Successfully saved summary to 'abstract' column for paper ID: {paper_id}") 
    except Error as e:
        print(f"Error updating abstract for paper ID {paper_id}: {e}") 
    finally:
        cursor.close()

def clean_text(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r'[^\x00-\x7F]+', ' ', raw_text) 
    text = re.sub(r'\s+', ' ', text) 
    return text.strip()

def call_gemini_api(prompt, model_name="gemini-2.0-flash-lite-001"): 
    if not GCP_PROJECT_ID:
        print("ERROR: GCP_PROJECT_ID is not set. Cannot call API.")
        return False, "GCP Project ID not configured."
        
    model = GenerativeModel(model_name)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    max_retries = 5
    delay = 15
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt, safety_settings=safety_settings)
            if response.candidates and response.candidates[0].content.parts:
                return True, response.text.strip()
            else:
                reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
                return False, f"Response was blocked or empty. Reason: {reason}"
        except Exception as e:
            if "429" in str(e): 
                print(f"Rate limit hit. Waiting for {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
            else: 
                print(f"An unexpected error occurred with the Vertex AI API: {e}")
                return False, f"An unexpected error occurred: {e}"
                
    return False, "Failed to get response after multiple retries due to rate limiting."

def run_summarization():
    print(f"\n{'='*25} EXECUTING AGENT: Summarization_agent.py {'='*25}")

    db_conn = get_db_connection()
    if not db_conn:
        return

    try:
        papers_to_summarize = get_papers_to_summarize(db_conn)

        if not papers_to_summarize:
            print("No new papers to summarize.")
            return

        print(f"  Found {len(papers_to_summarize)} papers to summarize.")
        for paper in papers_to_summarize:
            print(f"\n Summarizing paper ID: {paper['id']} ('{paper['title'][:50]}...')")
            
            source_text = clean_text(paper['full_text'][:1000000]) 

            prompt = f"""
            As an expert research analyst, your task is to create a comprehensive, structured summary of the following research paper text. 
            Read the text carefully from beginning to end and extract the most important information for each section defined below.
            Be concise yet thorough. Use full sentences and academic language.

            Here is the text:
            ---
            {source_text}
            ---

            Generate a summary with the following exact headings in Markdown bold format:
            Introduction: (Briefly state the problem, context, and paper's main goal)
            Methodology: (Describe the key methods, techniques, algorithms, and experimental setup)
            Datasets: (Identify the specific datasets used, including size or source if mentioned)
            Results: (Summarize the main quantitative or qualitative findings reported)
            Discussion/Limitations: (Briefly mention any discussion points or limitations acknowledged by the authors)
            Conclusion: (State the main conclusion and key takeaway of the paper)
            """
            
            success, summary = call_gemini_api(prompt)

            if success:
                preview_summary = summary.replace('\n', ' ') 
                print(f"Generated Summary Preview: {preview_summary[:150]}...")
                update_paper_with_summary(db_conn, paper['id'], summary) 
            else:
                print(f"Skipping database update for paper ID {paper['id']}. Reason: {summary}") 

    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

if __name__ == 'main':
    try:
        print("Initializing Summarization Agent for standalone run...")
        run_summarization()
    except Exception as e:
        print(f" An unexpected error occurred: {e}")
    finally:
        print("\nAgent run finished.")