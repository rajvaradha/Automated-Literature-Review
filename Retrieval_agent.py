import mysql.connector
from mysql.connector import Error
import requests
import xml.etree.ElementTree as ET
import time
import os
import sys
import re 
import random 
import json 

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'agentic_ai_db'
}
DOWNLOADS_DIR = 'downloads'

LIMIT_ARXIV = 50     
LIMIT_SEMANTIC = 25  
LIMIT_CORE = 25       

CORE_API_KEY = "YOUR_CORE_API_KEY" 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f" DATABASE ERROR: {e}")
        return None

def safe_to_int(value):
    if value is None: return None
    if isinstance(value, str):
        match = re.search(r'\d{4}', value)
        if match: value = match.group(0)
        else: return None
    try: return int(str(value)[:4])
    except (ValueError, TypeError): return None

def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name[:150] 

def download_pdf(pdf_url, filename, source):
    if not pdf_url:
        print(f"    ({source}) No PDF URL provided. Skipping download.")
        return None

    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    filepath = os.path.join(DOWNLOADS_DIR, sanitize_filename(filename))
    if os.path.exists(filepath):
         base, ext = os.path.splitext(filename)
         filename = f"{base}_{int(time.time())}{ext}"
         filepath = os.path.join(DOWNLOADS_DIR, sanitize_filename(filename))

    max_retries = 3
    delay = 5

    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(3, 6))
            
            with requests.Session() as s:
                response = s.get(pdf_url, stream=True, timeout=30, allow_redirects=True, headers=HEADERS) 
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()

                is_likely_pdf = (
                    "application/pdf" in content_type or
                    ("application/octet-stream" in content_type and filename.lower().endswith('.pdf'))
                )

                if is_likely_pdf:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"    ({source}) Downloaded: {filename}")
                    try:
                        if os.path.getsize(filepath) < 1024:
                            print(f"    ({source}) WARNING: Downloaded file size < 1KB. Possible error page.")
                    except OSError as e:
                        print(f"    ({source}) WARNING: Could not get file size after download: {e}")
                    return filepath
                else:
                    print(f"    ({source}) Link content type ('{content_type}') not PDF/octet-stream. Skipping.")
                    return None
        except requests.exceptions.Timeout:
            print(f"    ({source}) Attempt {attempt + 1}/{max_retries} timed out for {filename}.")
        except requests.exceptions.RequestException as e:
            print(f"    ({source}) Attempt {attempt + 1}/{max_retries} failed for {filename}. Reason: {e}")

        if attempt < max_retries - 1:
            print(f"        Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2
        else:
            print(f"    ({source}) All retries failed for {filename}.")
            return None
    return None

def save_paper_to_db(connection, paper_details):
    cursor = connection.cursor()
    query = """
        INSERT INTO papers1 (title, authors, publication_year, source, source_url, abstract, file_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE title=VALUES(title);
    """
    try:
        authors_str = ', '.join(paper_details.get('authors', [])) if isinstance(paper_details.get('authors'), list) else paper_details.get('authors', '')
        abstract_short = paper_details.get('abstract', '')[:65530]

        cursor.execute(query, (
            paper_details['title'],
            authors_str,
            paper_details.get('year'),
            paper_details['source'],
            paper_details['url'],
            abstract_short,
            paper_details.get('file_path')
        ))
        connection.commit()
        print(f" ({paper_details['source']}) Saved metadata: {paper_details['title'][:60]}...")
    except Error as e:
        print(f"Error saving paper to DB: {e}")
    finally:
        cursor.close()


def retrieve_papers_from_arxiv(db_conn, query, total_results):
    print(f"\n  Searching arXiv API for {total_results} papers on: '{query}'...")
    base_url = 'http://export.arxiv.org/api/query?'
    search_query = f'search_query=all:{query.replace(" ", "+")}&start=0&max_results={int(total_results * 1.5)}'

    papers_processed = 0
    try:
        time.sleep(random.uniform(2, 4))
        
        response = requests.get(base_url + search_query, timeout=30, headers=HEADERS)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        atom_ns = '{http://www.w3.org/2005/Atom}'

        for entry in root.findall(f'{atom_ns}entry'):
            if papers_processed >= total_results: break
            url = entry.find(f'{atom_ns}id').text
            pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
            record_id_part = url.split('/abs/')[-1].replace('/', '_')
            title_part = sanitize_filename(entry.find(f'{atom_ns}title').text.strip())[:50]
            filename = f"arXiv_{record_id_part}_{title_part}.pdf"

            file_path = download_pdf(pdf_url, filename, 'arXiv')
            if file_path:
                paper_details = {
                    'title': entry.find(f'{atom_ns}title').text.strip(),
                    'url': url,
                    'authors': [a.find(f'{atom_ns}name').text for a in entry.findall(f'{atom_ns}author')],
                    'abstract': entry.find(f'{atom_ns}summary').text.strip(),
                    'year': safe_to_int(entry.find(f'{atom_ns}published').text),
                    'source': 'arXiv',
                    'file_path': file_path
                }
                save_paper_to_db(db_conn, paper_details)
                papers_processed += 1
        print(f"\n  (arXiv) Successfully processed {papers_processed} papers.")
    except (requests.exceptions.RequestException, ET.ParseError) as e: 
        print(f"   (arXiv) Error processing arXiv batch: {e}")


def retrieve_papers_from_semantic_scholar(db_conn, query, total_results):
    print(f"\n  Searching Semantic Scholar for {total_results} downloadable papers on: '{query}'...")
    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    papers_found = 0
    offset = 0
    max_offset = 100 

    while papers_found < total_results and offset < max_offset:
        params = {
            "query": query, "limit": 10, "offset": offset,
            "fields": "title,authors,year,abstract,url,isOpenAccess,openAccessPdf,paperId"
        }
        response = None
        try:
            print(f"    (Semantic Scholar) Requesting papers, offset: {offset}...")
            time.sleep(random.uniform(3, 6)) 
            response = requests.get(api_url, params=params, timeout=30, headers=HEADERS)
            response.raise_for_status()
            
            data = response.json().get('data', [])
            if not data:
                print("    (Semantic Scholar) No more results found from the API.")
                break

            for paper in data:
                if papers_found >= total_results: break

                open_access_pdf_info = paper.get('openAccessPdf')
                if paper.get('isOpenAccess') and open_access_pdf_info and open_access_pdf_info.get('url'):
                    pdf_url = open_access_pdf_info['url']
                    paper_id = paper.get('paperId', 'unknown_id')
                    title_part = sanitize_filename(paper.get('title', 'NoTitle'))[:50]
                    filename = f"SemanticScholar_{paper_id[:10]}_{title_part}.pdf"

                    file_path = download_pdf(pdf_url, filename, 'Semantic Scholar')
                    if file_path:
                        authors_list = [
                            author.get('name', 'Unknown Author') 
                            for author in paper.get('authors', []) 
                            if author and author.get('name')
                        ]
                        if not authors_list:
                            authors_list = ['Unknown Author']
                            
                        paper_details = {
                            'title': paper.get('title'), 'url': paper.get('url'),
                            'authors': authors_list,
                            'abstract': paper.get('abstract'), 'year': paper.get('year'),
                            'source': 'Semantic Scholar', 'file_path': file_path
                        }
                        save_paper_to_db(db_conn, paper_details)
                        papers_found += 1
                        
        except requests.exceptions.RequestException as e:
            print(f"     (Semantic Scholar) Error processing batch: {e}")
            status_code = getattr(e.response, 'status_code', None)
            if status_code == 429:
                wait_time = random.uniform(60, 120)
                print(f"    (Semantic Scholar) Rate limit hit (429). Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
        except json.JSONDecodeError as e:
            print(f"     (Semantic Scholar) JSON Error: {e}")
        except Exception as e:
            print(f"     (Semantic Scholar) Error: {e}")
            break
         
        offset += 10 
        
    print(f"\n  (Semantic Scholar) Successfully processed {papers_found} papers.")


def retrieve_papers_from_core(db_conn, query, total_results):
    print(f"\n  Searching CORE API for {total_results} papers on: '{query}'...")
    search_url = "https://api.core.ac.uk/v3/search/works"

    req_headers = HEADERS.copy()
    
    if CORE_API_KEY and CORE_API_KEY != "YOUR_CORE_API_KEY":
        req_headers["Authorization"] = f"Bearer {CORE_API_KEY}"
        print("    (CORE) Using API Key.")
    else:
        print("    (CORE) No API Key provided. Using public access.")

    payload = {
        "q": query,
        "limit": total_results * 3, 
        "scroll": False
    }

    papers_processed = 0
    response = None
    try:
        print("    (CORE) Requesting results...")
        time.sleep(random.uniform(3, 6))
        
        response = requests.post(search_url, json=payload, headers=req_headers, timeout=45)
        response.raise_for_status()
        data = response.json()

        results = data.get('results', [])
        print(f"    (CORE) Found {len(results)} potential records.")

        if not results:
            print("    (CORE) No matching records found.")
            return

        for work in results:
            if papers_processed >= total_results:
                break

            title = work.get('title', 'No Title Available')
            pdf_url = work.get('downloadUrl')

            if not pdf_url:
                continue

            core_id_val = work.get('id')
            core_id = str(core_id_val) if core_id_val is not None else str(random.randint(100000, 999999))
            title_part = sanitize_filename(title)[:50]
            filename = f"CORE_{core_id}_{title_part}.pdf"

            file_path = download_pdf(pdf_url, filename, 'CORE')

            if file_path:
                authors_list = work.get('authors', [])
                abstract = work.get('abstract', 'No Abstract Available')
                year = safe_to_int(work.get('yearPublished') or work.get('publishedDate'))
                source_url = f"https://core.ac.uk/work/{core_id}" if core_id_val is not None else work.get('doiUrl', '')

                paper_details = {
                    'title': title,
                    'url': source_url,
                    'authors': authors_list,
                    'abstract': abstract,
                    'year': year,
                    'source': 'CORE',
                    'file_path': file_path
                }
                save_paper_to_db(db_conn, paper_details)
                papers_processed += 1

    except requests.exceptions.RequestException as e:
        print(f"   (CORE) Error during API request: {e}")
        if response is not None:
            print(f"     Response content: {response.text[:500]}")
    except Exception as e:
        print(f"   (CORE) An unexpected error occurred: {e}")

    print(f"\n  (CORE) Successfully processed {papers_processed} papers with download URLs.")


def run_retrieval(search_topic):
    print(f"\n{'='*25} EXECUTING AGENT: retrieval_agent.py {'='*25}")
    db_conn = get_db_connection()
    
    if not db_conn:
        return

    try:
        if not os.path.exists(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR)
            print(f"Created directory: {DOWNLOADS_DIR}")

        try:
            retrieve_papers_from_arxiv(db_conn, search_topic, total_results=LIMIT_ARXIV)
        except Exception as e:
            print(f" (arXiv) A critical error occurred: {e}")

        try:
            retrieve_papers_from_semantic_scholar(db_conn, search_topic, total_results=LIMIT_SEMANTIC)
        except Exception as e:
            print(f" (Semantic Scholar) A critical error occurred: {e}")

        try:
            retrieve_papers_from_core(db_conn, search_topic, total_results=LIMIT_CORE)
        except Exception as e:
            print(f" (CORE) A critical error occurred: {e}")
        
        print("\nRetrieval process completed for all specified sources.")
        
    except Exception as e:
        print(f" A general error occurred in run_retrieval: {e}")
        
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()
            print("\nDatabase connection closed by retrieval agent.")


if __name__ == '__main__': 
    try:
        if not os.path.exists(DOWNLOADS_DIR):
            os.makedirs(DOWNLOADS_DIR)
            print(f"Created directory: {DOWNLOADS_DIR}")

        topic = input("Enter the research topic for standalone run: ")
        run_retrieval(topic)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("\nAgent run finished.")