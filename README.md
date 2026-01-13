# Automated-Literature-Review
An autonomous 7-agent AI system that automates literature reviews, identifies research gaps, and verifies claims using Google Gemini.

##  Project Overview
The **Agentic AI Research Agent** is an "autonomous multi-agent system created as an answer to the ‘deluge of information’ issue in academic research." Rather than having to check out and scan through "hundreds of papers by hand,” this "system will undertake the complete process from downloading PDF files to reaching a ‘Final Future Research Proposal.'"
It has a **7-stage pipeline** that exhibits a collaboration of tailored AI agents operating as if they are a research team, led by a central MySQL database

## Key Innovation: Verification Agent
Unlike standard AI tools, this system includes a dedicated agent called the **Verification Agent**. This acts as an internal auditor, cross-referencing the AI's generated "Research Gaps" against the original source summaries for hallucinations and assigns a **Confidence Score**.

## How It Works (The 7-Agent Pipeline)
These agents run sequentially by the system:
1.  **Retrieval Agent:** Obtains papers from arXiv, Semantic Scholar, and CORE APIs.
2.  **Preprocessing Agent:** Uses `PyMuPDF` to extract clean full text from PDFs.
3.  **Summarization Agent:** Utilizes **Google Vertex AI (Gemini)** to produce structural summaries (Introduction, Methodology, Results etc..).
4.  **Comparative Analysis Agent:** Combines all the summaries together into one "Enhanced Literature Survey" matrix.
5.  **Gap Identification Agent:** It reasons over the matrix to identify uncharted zones and suggests a new research paradigm.
6.  **Verification Agent:** Verifies information in the proposal through source data for its validity.
7.  **Report Generation Agent:** A report is written in PDF format using `reportlab`.

   # Tech Stack
* **Language:** Python 3.10
* **LLM:** Google Gemini (via Vertex AI)
* **Orchestration:** Custom Agentic Framework (Sequential Pipeline)
* **Database:** MySQL (Central Workbench)
* **Interface:** Streamlit
* **Libraries:** `fitz` (PyMuPDF), `reportlab`, `mysql-connector-python`, `requests`.

  ##  Repository Structure
```text
├── main.py                     # Central controller for the agent pipeline
├── Streamlit_app.py            # Web Interface (GUI)
├── agents/
│   ├── Retrieval_agent.py      # Connects to Academic APIs
│   ├── Preprocessing_agent.py  # PDF Text Extraction
│   ├── Summarization_agent.py  # Gemini Summarizer
│   ├── Comparative_agent.py    # Generates Comparison Matrix
│   ├── Gap_identification.py   # Identifies Research Gaps
│   ├── Verification_agent.py   # Audits AI outputs
│   └── Report_generator.py     # PDF Report Creator
├── schema.sql                  # Database Setup
├── requirements.txt            # Dependencies
└── reports/                    # Final Output Folder
