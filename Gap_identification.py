import mysql.connector
from mysql.connector import Error
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import os
import sys
import time


GCP_PROJECT_ID = ""  
GCP_LOCATION = "us-central1"            
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'agentic_ai_db'
}


vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)


def get_db_connection():
    """Establishes and returns a new database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f" DATABASE ERROR: {e}")
    return None

def get_analysis_from_db(connection, analysis_type):
    """Fetches the most recent analysis of a specific type from the database."""
    cursor = connection.cursor(dictionary=True)
    query = "SELECT content FROM analyses WHERE analysis_type = %s ORDER BY created_at DESC LIMIT 1"
    cursor.execute(query, (analysis_type,))
    result = cursor.fetchone()
    cursor.close()
    return result['content'] if result else None

def save_final_analysis(connection, analysis_type, content):
    """Saves or updates a final analysis in the 'analyses' table."""
    cursor = connection.cursor()
    
    query = """
        INSERT INTO analyses (analysis_type, content) 
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE content=VALUES(content);
    """
    try:
        cursor.execute(query, (analysis_type, content))
        connection.commit()
        print(f" Successfully saved '{analysis_type}' to the database.")
    except Error as e:
        print(f"Error saving final analysis to the database: {e}")
    finally:
        cursor.close()


def call_gemini_api(prompt, model_name="gemini-2.0-flash-lite-001"):
    """Calls the Gemini API with a given prompt and robust error handling."""
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
                return False, f"Response was blocked. Reason: {reason}"
        except Exception as e:
            if "429" in str(e):
                print(f"Rate limit hit. Waiting for {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
            else:
                return False, f"Vertex AI API Error: {e}"
                
    return False, "Failed to get response after multiple retries due to rate limiting."


def run_gap_identification_agent():
    """The main entry point for the gap identification and proposal agent."""
    print(f"\n{'='*25} EXECUTING AGENT: Gap_identification.py {'='*25}")
    
    db_conn = get_db_connection()
    if not db_conn:
        return

    try:
     
        literature_survey = get_analysis_from_db(db_conn, "Enhanced Literature Survey")
        if not literature_survey:
            print(" Could not find an 'Enhanced Literature Survey' in the database. Please run the comparative analysis agent first.")
            return

        print(" Found a Literature Survey to analyze.")

        
        print(" Synthesizing survey to identify the research gap...")
        gap_prompt = f"""
        Based on the following literature survey, provide a detailed analysis of the most significant research gap or underexplored area. 
        Focus on what is missing from the current research. This section should be around 500 words.

        --- LITERATURE SURVEY ---
        {literature_survey}
        --- END SURVEY ---
        """
        success, gap_analysis = call_gemini_api(gap_prompt)
        
        if not success:
            print(f" Failed to generate Research Gap Analysis. Reason: {gap_analysis}")
            return
        
        print(" Research Gap Analysis generated successfully.")
        save_final_analysis(db_conn, "Research Gap Analysis", gap_analysis)

        
        print(" Using the gap analysis to generate a detailed future research proposal...")
        proposal_prompt = f"""
        As a world-class research strategist, your task is to write a detailed and well-structured research proposal that directly addresses the following "Identified Research Gap".
        The total length of your entire response should be approximately 5000 words.
        Your proposal must have the following six exact headings:
        Title:
        Rationale:
        Methodology:
        Data Requirements:
        Potential Challenges:
        Novel Contributions and Potential Impact:

        --- IDENTIFIED RESEARCH GAP ---
        {gap_analysis}
        --- END GAP ---
        """
        success, future_proposal = call_gemini_api(proposal_prompt)

        if not success:
            print(f" Failed to generate Future Research Proposal. Reason: {future_proposal}")
            return
            
        print(" Future Research Proposal generated successfully.")
        save_final_analysis(db_conn, "Future Research Proposal", future_proposal)

        print(f"\n SUCCESS: Agent 'Gap_identification.py' completed.")

    except Exception as e:
        print(f" An unexpected error occurred in the gap identification agent: {e}")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()


if __name__ == 'main':
    try:
        print(" Initializing Gap Identification Agent for standalone run...")
        run_gap_identification_agent()
    except Exception as e:
        print(f" An unexpected error occurred: {e}")
    finally:
        print("\nAgent run finished.")