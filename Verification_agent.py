import mysql.connector
from mysql.connector import Error
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
import os
import sys
import time
import re
import json

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

def get_analysis_to_verify(connection, analysis_type):
    cursor = connection.cursor(dictionary=True)
    query = "SELECT content FROM analyses WHERE analysis_type = %s ORDER BY created_at DESC LIMIT 1"
    cursor.execute(query, (analysis_type,))
    result = cursor.fetchone()
    cursor.close()
    return result['content'] if result else None

def get_all_summaries(connection):
    cursor = connection.cursor(dictionary=True)
    query = "SELECT id, title, abstract as summary FROM papers1 WHERE abstract IS NOT NULL AND abstract != ''"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results

def save_verification_result(connection, analysis_type, content):
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
        print(f"Error saving verification result to the database: {e}")
    finally:
        cursor.close()

def call_gemini_api(prompt, model_name="gemini-2.0-flash-lite-001"):
    if not GCP_PROJECT_ID:
        print("     ERROR: GCP_PROJECT_ID is not set. Cannot call API.")
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
                return False, f"Response was blocked. Reason: {reason}"
        except Exception as e:
            if "429" in str(e): 
                print(f"     Rate limit hit. Waiting for {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"     Vertex AI API Error: {e}")
                return False, f"Vertex AI API Error: {e}"
                
    return False, "Failed to get response after multiple retries due to rate limiting."

def run_verification(): 
    print(" Starting Verification Process...")
    
    db_conn = get_db_connection()
    if not db_conn:
        print(" Could not establish a database connection. Verification agent is skipping its run.")
        return
    
    try:
        all_summaries = get_all_summaries(db_conn)
        if not all_summaries:
            print(" No source summaries found in the database for verification. Skipping.")
            return
            
        print(f"     Found {len(all_summaries)} source summaries to use as context.")
        summaries_text = "\n\n".join([f"### Paper ID {s['id']} ({s['title']}):\n{s['summary']}" for s in all_summaries])

        print("\n     --- Verifying Gap Analysis ---")
        gap_analysis_content = get_analysis_to_verify(db_conn, "Research Gap Analysis")
        
        if not gap_analysis_content:
            print("     No 'Research Gap Analysis' found to verify. Skipping this step.")
        else:
            gap_verification_prompt = f"""
            You are a meticulous fact-checker reviewing an AI-generated 'Research Gap Analysis'.
            Your task is to assess how well the claims made in the analysis are supported by the provided 'Source Summaries'.

            Instructions:
            1. Read the 'Research Gap Analysis' carefully.
            2. Read all the provided 'Source Summaries'.
            3. Determine how well the identified gaps logically follow from the limitations and disadvantages mentioned in the source summaries.
            4. Provide a numeric Confidence Score as a percentage.
            5. Provide a brief Justification for your score.

            --- START OF RESEARCH GAP ANALYSIS ---
            {gap_analysis_content}
            --- END OF RESEARCH GAP ANALYSIS ---

            --- START OF SOURCE SUMMARIES ---
            {summaries_text}
            --- END OF SOURCE SUMMARIES ---

            Verification Report:
            Confidence Score: [Your score as a percentage]
            Justification: [Your detailed explanation here]
            """

            print("     Calling AI to verify Gap Analysis...")
            success, gap_report = call_gemini_api(gap_verification_prompt)

            if success:
                print("     Gap Analysis verification report generated successfully.")
                save_verification_result(db_conn, "Verification Report (Gap Analysis)", gap_report)
            else:
                print(f"     Failed to generate Gap Analysis verification report. Reason: {gap_report}")

        print("\n     --- Verifying Future Research Proposal ---")
        proposal_content = get_analysis_to_verify(db_conn, "Future Research Proposal")

        if not proposal_content:
            print("     No 'Future Research Proposal' found to verify. Skipping this step.")
        else:
            proposal_verification_prompt = f"""
            You are a research committee reviewer.
            Your task is to assess how relevant the 'Future Research Proposal' is, based on the gaps identified in the 'Source Summaries'.

            Instructions:
            1. Read the 'Future Research Proposal' carefully.
            2. Read all the 'Source Summaries' to understand their limitations.
            3. Determine how well the proposal's objectives (e.g., its Rationale and Methodology) directly address the gaps and limitations evident in the source summaries.
            4. Provide a numeric Relevance Score as a percentage.
            5. Provide a brief Justification for your score.

            --- START OF FUTURE RESEARCH PROPOSAL ---
            {proposal_content}
            --- END OF FUTURE RESEARCH PROPOSAL ---

            --- START OF SOURCE SUMMARIES ---
            {summaries_text}
            --- END OF SOURCE SUMMARIES ---

            Verification Report:
            Relevance Score: [Your score as a percentage"]
            Justification: [Your detailed explanation here]
            """

            print("     Calling AI to verify Future Proposal...")
            success, proposal_report = call_gemini_api(proposal_verification_prompt)

            if success:
                print("     Future Proposal verification report generated successfully.")
                save_verification_result(db_conn, "Verification Report (Future Proposal)", proposal_report)
            else:
                print(f"     Failed to generate Future Proposal verification report. Reason: {proposal_report}")

    except Exception as e:
        print(f" An unexpected error occurred during verification: {e}")
        
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            print("\n     Closed verification agent's database connection.")

if __name__ == '__main__':
    try:
        print(f"\n{'='*25} EXECUTING AGENT: Verification_agent.py {'='*25}")
        run_verification() 
    except Exception as e:
        print(f" An unexpected error occurred: {e}")
    finally:
        print("\n Verification Agent run finished.")