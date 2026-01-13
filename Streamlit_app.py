import streamlit as st
import sys
import time
import os
import mysql.connector
from mysql.connector import Error
import traceback


try:
    from Retrieval_agent import run_retrieval
    from Preprocessing_agent import run_preprocessing
    from Summarization_agent import run_summarization
    from Comparative_analysis import run_comparative_analysis
    from Gap_identification import run_gap_identification_agent
    from Verification_agent import run_verification
    from report_generation_agent import run_report_generation
except ImportError as e:
    
    st.error(f" CRITICAL ERROR: Could not import an agent function.")
    st.error(f"Details: {e}")
    st.error("Please ensure your 7 agent.py files are in the same directory as this app.")
    st.code("""
- Retrieval_agent.py
- Preprocessing_agent.py
- Summarization_agent.py
- Comparative_analysis.py
- Gap_identification.py
- Verification_agent.py
- Report_generator.py
    """)
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
        st.error(f" DATABASE ERROR: Could not connect to MySQL. Please ensure the database is running and credentials are correct. Details: {e}")
        return None

def clear_database(status_ui):
    """Truncates all data from tables for a fresh run, updating the UI."""
    status_ui.info(" Clearing old data from the database...")
    db_conn = None
    try:
        db_conn = get_db_connection()
        if not db_conn:
            raise ConnectionError("Database connection failed.")

        cursor = db_conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("TRUNCATE TABLE analyses;")
        cursor.execute("TRUNCATE TABLE papers1;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        db_conn.commit()
        cursor.close()
        status_ui.success(" Database cleared successfully.")
        return True
    except Error as e:
        status_ui.error(f" Error while clearing database: {e}")
        return False
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

def run_pipeline(search_topic, status_ui):
    """
    Main orchestrator for the agentic AI research pipeline.
    This function runs all agents sequentially and updates the Streamlit UI.
    """
    try:
        start_time = time.time()

       
        if not clear_database(status_ui):
            return None, 0

        
        status_ui.info(" [1/7] Running Retrieval Agent: Fetching and downloading papers...")
        run_retrieval(search_topic)
        status_ui.success(" [1/7] Retrieval Agent Finished.")

        
        status_ui.info(" [2/7] Running Preprocessing Agent: Extracting text from PDFs...")
        run_preprocessing()
        status_ui.success("[2/7] Preprocessing Agent Finished.")

       
        status_ui.info(" [3/7] Running Summarization Agent: Summarizing extracted text...")
        run_summarization()
        status_ui.success(" [3/7] Summarization Agent Finished.")

        
        status_ui.info(" [4/7] Running Comparative Analysis Agent: Creating comparative table...")
        run_comparative_analysis()
        status_ui.success(" [4/7] Comparative Analysis Agent Finished.")

        
        status_ui.info(" [5/7] Running Gap Identification Agent: Identifying research gaps...")
        run_gap_identification_agent()
        status_ui.success(" [5/7] Gap Identification Agent Finished.")

       
        status_ui.info(" [6/7] Running Verification Agent: Verifying claims...")
        run_verification()
        status_ui.success(" [6/7] Verification Agent Finished.")

        status_ui.info(" [7/7] Running Report Generation Agent: Compiling final PDF report...")
        run_report_generation(search_topic)
        status_ui.success(" [7/7] Report Generation Agent Finished.")

        total_time = time.time() - start_time

        topic_slug = search_topic.replace(' ', '_').lower()
        report_filename = f"{topic_slug}_research_report.pdf"
        report_path = os.path.join('reports', report_filename)

        return report_path, total_time

    except Exception as e:
        
        st.error(f" An unexpected error occurred during the pipeline execution.")
        st.error(f"Error Details: {e}")
        st.error("Traceback:")
        st.code(traceback.format_exc())
        return None, 0



st.set_page_config(page_title="Agentic AI Research Pipeline", layout="wide")

st.title(" Agentic AI Research Pipeline")
st.markdown("Enter a research topic below to start the automated pipeline. The system will use a team of 7 AI agents to retrieve, process, analyze, and compile a comprehensive research report.")

if 'pipeline_running' not in st.session_state:
    st.session_state.pipeline_running = False
if 'report_path' not in st.session_state:
    st.session_state.report_path = None
if 'total_time' not in st.session_state:
    st.session_state.total_time = 0


with st.form("research_form"):
    search_topic = st.text_input(
        "**Enter your research topic:**",
        placeholder="e.g., 'The impact of AI on climate change'",
        help="The topic you provide will be used to search for academic papers and generate the final report."
    )
    submitted = st.form_submit_button("Start Research Pipeline", type="primary")

if submitted and not st.session_state.pipeline_running:
    if not search_topic.strip():
        st.warning(" Please enter a research topic.")
    else:
        st.session_state.pipeline_running = True
        st.session_state.report_path = None 
        
       
        st.markdown("---")
        st.subheader("Pipeline Progress")
        
        
        status_container = st.container()
        
        with st.spinner("Initializing pipeline... Please wait."):
            report_path, total_time = run_pipeline(search_topic, status_container)
        
        
        if report_path: 
            st.session_state.report_path = report_path
            st.session_state.total_time = total_time
        
        st.session_state.pipeline_running = False
        
        st.rerun()


if st.session_state.report_path:
    st.markdown("---")
    st.subheader(" Pipeline Complete!")
    st.success(f"The research pipeline finished successfully in {st.session_state.total_time:.2f} seconds.")
    
    report_path = st.session_state.report_path
    
   
    if os.path.exists(report_path):
        with open(report_path, "rb") as file:
            st.download_button(
                label=" Download Final Report (PDF)",
                data=file,
                file_name=os.path.basename(report_path),
                mime="application/pdf",
                type="primary"
            )
        st.info(f"Your report has been saved to the `{report_path}` directory.")
    else:
        
        st.error(f"Could not find the generated report at the expected path: `{report_path}`. Please check the 'reports' folder and the console for errors.")