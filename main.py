import sys
import time
import os
import mysql.connector
from mysql.connector import Error


try:
    
    from Retrieval_agent import run_retrieval
    from Preprocessing_agent import run_preprocessing
    from Summarization_agent import run_summarization
    from Comparative_analysis import run_comparative_analysis
    from Gap_identification import run_gap_identification_agent
    from Verification_agent import run_verification
    from report_generation_agent import run_report_generation
except ImportError as e:
    print(f" CRITICAL ERROR: Could not import an agent function.")
    print(f"Details: {e}")
    print("\nPlease ensure your 7 agent .py files are in the same directory as main.py:")
    print(" - Retrieval_agent.py")
    print(" - Preprocessing_agent.py")
    print(" - Summarization_agent.py")
    print(" - Comparative_analysis.py") 
    print(" - Gap_identification.py")
    print(" - Verification_agent.py")
    print(" - Report_generator.py")
    sys.exit(1)


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
        print(f" DATABASE ERROR (Main): {e}")
        return None

def clear_database():
    """Truncates all data from papers1 and analyses tables for a fresh run."""
    print(" Clearing old data from the database...")
    db_conn = None
    try:
        db_conn = get_db_connection()
        if not db_conn:
            print("Could not connect to database to clear it. Aborting.")
            return False 
        
        cursor = db_conn.cursor()
        
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        print("   - Truncating 'papers1' table...")
        cursor.execute("TRUNCATE TABLE papers1;")
        
        print("   - Truncating 'analyses' table...")
        cursor.execute("TRUNCATE TABLE analyses;")
        
        
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        db_conn.commit()
        cursor.close()
        
        print(" Database cleared successfully.")
        return True 
        
    except Error as e:
        print(f" Error while clearing database: {e}")
        return False 
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()



def print_header(title):
    """Prints a formatted header to clearly mark the start of an agent's task."""
    print("\n" + "="*80)
    print(f" STARTING AGENT: {title}")
    print("="*80)

def print_footer(title):
    """Prints a formatted footer to clearly mark the end of an agent's task."""
    print("\n" + "-"*80)
    print(f" FINISHED AGENT: {title}")
    print("-"*80)

def main():
    """
    Main orchestrator for the complete agentic AI research pipeline.
    This script runs all agents in a sequential, logical order.
    """
    print("="*80)
    print(" Agentic AI Research Pipeline Initializing...")
    print("="*80)

    
    if not clear_database():
        print(" Halting pipeline due to database clearing failure.")
        return
    

    
    print("⚠ IMPORTANT: Before you begin, ensure you have filled in your GCP_PROJECT_ID")
    print("   and database password in ALL relevant agent scripts.")
    print("   Also, ensure you are using the CORRECTED Summarization_agent.py.")
    print("-"*80)

   
    try:
        search_topic = input("➡ Enter the research topic for the pipeline: ")
        if not search_topic.strip():
            print(" Search topic cannot be empty. Exiting.")
            return
    except (KeyboardInterrupt, EOFError):
        print("\n\nAborted by user. Exiting.")
        return

    start_time = time.time()
    
    try:
      
        print_header("1. Retrieval Agent")
        run_retrieval(search_topic)
        print_footer("1. Retrieval Agent")
        
        
        print_header("2. Preprocessing Agent")
        run_preprocessing()
        print_footer("2. Preprocessing Agent")

        
        print_header("3. Summarization Agent")
        run_summarization()
        print_footer("3. Summarization Agent")

        
        print_header("4. Comparative Analysis Agent")
        run_comparative_analysis()
        print_footer("4. Comparative Analysis Agent")

        
        print_header("5. Gap Identification Agent")
        run_gap_identification_agent()
        print_footer("5. Gap Identification Agent")

        
        print_header("6. Verification Agent")
        run_verification()
        print_footer("6. Verification Agent")

        
        print_header("7. Report Generation Agent")
        run_report_generation(search_topic)
        print_footer("7. Report Generation Agent")

    except Exception as e:
        print(f"\n{'!'*80}")
        print(f" AN UNEXPECTED ERROR OCCURRED: {e}")
        print("   The pipeline execution has been halted.")
        print(f"{'!'*80}")
    finally:
        end_time = time.time()
        total_time = end_time - start_time
        print("\n" + "="*80)
        print(f" PIPELINE RUN FINISHED in {total_time:.2f} seconds.")
       
        print(f"   Check the '{os.path.join('reports')}' folder for the final PDF report.")
        print("   Downloaded papers are in the 'downloads' folder.")
        print("="*80)


if __name__ == "__main__":
    main()

