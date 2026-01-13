import mysql.connector
from mysql.connector import Error
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import os
import sys


GCP_PROJECT_ID = ""  
GCP_LOCATION = "us-central1"
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'agentic_ai_db'
}


def get_db_connection():
    """Establishes and returns a new database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"DATABASE ERROR: {e}")
        return None

def get_all_summaries(connection):
    """Fetches up to 100 available paper abstracts from the database."""
    cursor = connection.cursor(dictionary=True)
    query = "SELECT title, publication_year, abstract as summary FROM papers1 WHERE abstract IS NOT NULL LIMIT 100"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results

def save_analysis_to_db(connection, analysis_type, content):
    """Saves or updates an analysis in the 'analyses' table."""
    cursor = connection.cursor()
    try:
        query = """
            INSERT INTO analyses (analysis_type, content) 
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE content=VALUES(content);
        """
        cursor.execute(query, (analysis_type, content))
        connection.commit()
        print(f" Successfully saved '{analysis_type}' to the database.")
    except Error as e:
        print(f" Error saving analysis to the database: {e}")
    finally:
        cursor.close()


def call_gemini_api(prompt, model_name="gemini-2.0-flash-lite-001"):
    """Calls the Gemini API and returns the response text."""
    try:
        model = GenerativeModel(model_name)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        response = model.generate_content(prompt, safety_settings=safety_settings)
        if response.candidates and response.candidates[0].content.parts:
            return response.text.strip()
        else:
            reason = response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN"
            print(f" Response was blocked. Reason: {reason}")
            return None
    except Exception as e:
        print(f" Vertex AI API Error: {e}")
        return None


def run_comparative_analysis():
    """The main entry point for the comparative analysis agent."""
    print(f"\n{'='*25} EXECUTING AGENT: Comparative_agent.py {'='*25}")
    
    db_conn = get_db_connection()
    if not db_conn:
        return

    try:
        all_summaries = get_all_summaries(db_conn)
        if not all_summaries or len(all_summaries) < 2:
            print(" Not enough summaries in the database. Please run retrieval and summarization first.")
            return

        print(f"Found {len(all_summaries)} summaries to analyze.")
        
        combined_text = ""
        for i, summary_data in enumerate(all_summaries):
            combined_text += f"--- PAPER {i+1} ---\n"
            combined_text += f"TITLE: {summary_data['title']}\n"
            combined_text += f"YEAR: {summary_data['publication_year']}\n"
            combined_text += f"SUMMARY:\n{summary_data['summary']}\n\n"

        
        analysis_prompt = f"""
        As a senior research analyst, conduct a critical comparative analysis of the following research paper summaries.
        Your final output MUST be one clean, well-formatted Markdown table. The table must have a row for each paper.

        The table columns are: "Title & Year", "Key Finding", "Advantages", "Disadvantages", and "Limitations".

        For each paper, you must:
        1.  *Title & Year*: Extract the exact title and publication year.
        2.  *Key Finding*: Write a 2-3 sentence summary of the paper's main methodology and most important conclusion. Use full sentences.
        3.  *Advantages*: In full sentences, describe the primary strengths of the proposed approach.
        4.  *Disadvantages*: Critically analyze the summary and infer potential disadvantages. For example, if a method is complex, it might be computationally expensive. If a new technique is proposed, it might lack established benchmarks. Do not just state 'Not explicitly mentioned'.
        5.  *Limitations*: Critically analyze the summary and infer potential limitations. For example, if a study only uses one dataset, is tested in a simulated environment, or has a small sample size, mention that as a limitation.

        Do not include any text or explanations before or after the single Markdown table.

        --- START OF SUMMARIES ---
        {combined_text}
        --- END OF SUMMARIES ---
        """
        print(" Generating new Comparative Analysis table...")
        analysis_table = call_gemini_api(analysis_prompt)
        
        if analysis_table:
            print("\n Comparative Analysis table generated successfully.")
            save_analysis_to_db(db_conn, "Enhanced Literature Survey", analysis_table)
        else:
            print("\n Failed to generate Comparative Analysis.")
              
        print(f"\n SUCCESS: Agent 'Comparative_agent.py' completed.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()


if __name__ == '_main_':
    try:
        print("Initializing Comparative Analysis Agent for standalone run...")
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        run_comparative_analysis()
    except Exception as e:
        print(f" An unexpected error occurred: {e}")
    finally:
        print("\nAgent run finished.")