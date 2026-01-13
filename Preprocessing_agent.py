import mysql.connector
from mysql.connector import Error
import fitz  
import os
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'agentic_ai_db'
}
DOWNLOADS_DIR = 'downloads'


def get_db_connection():
    """Establishes and returns a new database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"DATABASE ERROR: {e}")
        return None

def get_papers_without_full_text(connection):
    """Fetches papers that have a file path but no extracted full text."""
    cursor = connection.cursor(dictionary=True)
    query = "SELECT id, file_path FROM papers1 WHERE file_path IS NOT NULL AND full_text IS NULL"
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results

def update_paper_with_full_text(connection, paper_id, full_text):
    """Updates a paper record with the extracted full text."""
    cursor = connection.cursor()
    query = "UPDATE papers1 SET full_text = %s WHERE id = %s"
    try:
        cursor.execute(query, (full_text, paper_id))
        connection.commit()
        print(f" Successfully saved full text for paper ID: {paper_id}")
    except Error as e:
        print(f" Error updating paper ID {paper_id}: {e}")
    finally:
        cursor.close()


def extract_text_from_pdf(filepath):
    """Extracts all text content from a given PDF file."""
    try:
        doc = fitz.open(filepath)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as e:
        print(f"    Error reading PDF {os.path.basename(filepath)}: {e}")
        return None


def run_preprocessing(): 
    """Main entry point for the preprocessing agent."""
    print(f"\n{'='*25} EXECUTING AGENT: Preprocessing_agent.py {'='*25}")
    
    db_conn = get_db_connection()
    if not db_conn:
        return

    try:
        papers_to_process = get_papers_without_full_text(db_conn)
        
        if not papers_to_process:
            print("No new papers to preprocess.")
            return

        print(f"Found {len(papers_to_process)} papers to preprocess.")
        for paper in papers_to_process:
            print(f"\nProcessing paper ID: {paper['id']} | File: '{paper['file_path']}'")
            
            full_text = extract_text_from_pdf(paper['file_path'])
            
            if full_text:
                print(f"Extracted {len(full_text)} characters.")
                
                update_conn = get_db_connection()
                if update_conn:
                    update_paper_with_full_text(update_conn, paper['id'], full_text)
                    update_conn.close()
            else:
                print("No text could be extracted.")
        
        print(f"\n SUCCESS: Agent 'Preprocessing_agent.py' completed.")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()



if __name__ == '_main_':
    try:
        run_preprocessing()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("\nAgent run finished.")