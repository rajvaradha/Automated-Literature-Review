import mysql.connector
from mysql.connector import Error
import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import re
import time 

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '', 
    'database': 'agentic_ai_db'
}

REPORTS_DIR = 'reports' 

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f" DATABASE ERROR: {e}")
    return None

def get_analysis_from_db(connection, analysis_type):
    cursor = connection.cursor(dictionary=True)
    query = "SELECT content FROM analyses WHERE analysis_type = %s ORDER BY created_at DESC LIMIT 1"
    cursor.execute(query, (analysis_type,))
    result = cursor.fetchone()
    cursor.close() 
    return result['content'] if result else None

def parse_markdown_table(markdown_text):
    if not markdown_text: return [[]]
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(name='BodyText', parent=styles['BodyText'], spaceAfter=6, leading=14)
    header_style = ParagraphStyle(name='Header', parent=styles['h4'], alignment=1, textColor=colors.whitesmoke) 

    markdown_text = re.sub(r'^markdown\n|$', '', markdown_text.strip())
    lines = markdown_text.strip().split('\n')

    valid_lines = [line for line in lines if line.strip() and '|' in line and not re.match(r'^\s*\|?([-:]+\|)+[-:]+\|?\s*$', line.strip())]

    if not valid_lines: return [[]]

    header_line = valid_lines[0]
    data_lines = valid_lines[1:]

    header_cells_raw = [h.strip() for h in header_line.strip('|').split('|')]
    header = [Paragraph(h, header_style) for h in header_cells_raw]

    if not header: return [[]]

    data = []
    for line in data_lines:
        row_cells_raw = [cell.strip() for cell in line.strip('|').split('|')]
        if len(row_cells_raw) == len(header):
            wrapped_row = [Paragraph(cell, body_style) for cell in row_cells_raw]
            data.append(wrapped_row)
        else:
            print(f" Warning: Skipping malformed table row (expected {len(header)} cells, found {len(row_cells_raw)}): {line}")

    if not data: return [header] 

    return [header] + data


def parse_structured_text(text):
    if not text: return []
    styles = getSampleStyleSheet()
    h3_style = ParagraphStyle(name='H3_bold', parent=styles['h3'], spaceAfter=6)
    body_style = ParagraphStyle(name='BodyText', parent=styles['BodyText'], spaceAfter=6, leading=14)
    bold_body_style = ParagraphStyle(name='BoldBody', parent=body_style, fontName='Helvetica-Bold')

    story = []
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)

    paragraphs = re.split(r'\n\s*\n+', text.strip())

    for para_text in paragraphs:
        cleaned_para = para_text.strip()
        if not cleaned_para: continue

        if cleaned_para.startswith('<b>') and cleaned_para.endswith('</b>') and '\n' not in cleaned_para and len(cleaned_para) < 100:
             if re.match(r'<b>\d+\.\s+.*?</b>', cleaned_para) or cleaned_para.count(':') == 1:
                 heading_text = cleaned_para.replace('<b>', '').replace('</b>', '')
                 story.append(Paragraph(heading_text, styles['h2'])) 
             else:
                 heading_text = cleaned_para.replace('<b>', '').replace('</b>', '')
                 story.append(Paragraph(heading_text, h3_style)) 
             story.append(Spacer(1, 0.1 * inch))
        
        elif cleaned_para.startswith('<b>Overall Confidence Score:</b>') or cleaned_para.startswith('<b>Confidence Score:</b>') or cleaned_para.startswith('<b>Relevance Score:</b>'):
             story.append(Paragraph(cleaned_para, bold_body_style))
             story.append(Spacer(1, 0.1 * inch))
        else:
             story.append(Paragraph(cleaned_para, body_style))
             story.append(Spacer(1, 0.1 * inch)) 

    return story

def generate_pdf_report(topic, survey_md, gap_text, proposal_text, gap_verification_content, proposal_verification_content):
    safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic)[:50].strip().replace(" ", "_") or "report"
    
    filepath = os.path.join(REPORTS_DIR, f"{safe_topic}_research_report.pdf") 

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=1.0*inch, bottomMargin=1.0*inch)
    styles = getSampleStyleSheet()
    story = []

    print(f" Generating PDF report: {filepath}")

    story.append(Paragraph(f"AI-Generated Research Report", styles['h1']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"Topic: {topic.title()}", styles['h2']))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(PageBreak())

    story.append(Paragraph("1. Enhanced Literature Survey", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))
    if survey_md:
        table_data = parse_markdown_table(survey_md)
        if len(table_data) > 0 and len(table_data[0]) > 0:
            available_width = doc.width
            num_cols = len(table_data[0])
            col_widths = [available_width / num_cols] * num_cols

            table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign='CENTER')
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F81BD')), 
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),       
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),                    
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),                     
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),         
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),                  
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#DCE6F1')), 
                ('GRID', (0, 0), (-1, -1), 1, colors.darkgrey),          
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ])
            table.setStyle(style)
            story.append(table)
        else: 
             story.append(Paragraph("Could not parse literature survey table. Displaying raw content:", styles['Italic']))
             story.extend(parse_structured_text(survey_md)) 
    else:
        story.append(Paragraph("Literature survey data not found.", styles['Italic']))
    story.append(PageBreak())

    story.append(Paragraph("2. Research Gap Analysis", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))
    if gap_text:
        story.extend(parse_structured_text(gap_text))
    else:
        story.append(Paragraph("Research gap analysis not generated or found.", styles['Italic']))
    story.append(PageBreak())

    story.append(Paragraph("3. Verification Report (Gap Analysis)", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))
    if gap_verification_content:
        story.extend(parse_structured_text(gap_verification_content))
    else:
        story.append(Paragraph("Verification report for Gap Analysis not generated or found.", styles['Italic']))
    story.append(PageBreak())

    story.append(Paragraph("4. Future Research Proposal", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))
    if proposal_text:
        story.extend(parse_structured_text(proposal_text))
    else:
        story.append(Paragraph("Future research proposal not generated or found.", styles['Italic']))
    story.append(PageBreak()) 

    story.append(Paragraph("5. Verification Report (Future Proposal)", styles['h2']))
    story.append(Spacer(1, 0.1 * inch))
    if proposal_verification_content:
        story.extend(parse_structured_text(proposal_verification_content))
    else:
        story.append(Paragraph("Verification report for Future Proposal not generated or found.", styles['Italic']))

    try:
        doc.build(story)
        print(f" Successfully created report: {filepath}")
        return filepath 
    except Exception as e:
        print(f" Error building PDF: {e}")
        return None


def run_report_generation(topic):
    print(f"\n{'='*25} EXECUTING AGENT: report_generator.py {'='*25}")

    db_conn = get_db_connection()
    if not db_conn:
        return

    try:
        survey_content = get_analysis_from_db(db_conn, "Enhanced Literature Survey")
        gap_content = get_analysis_from_db(db_conn, "Research Gap Analysis")
        proposal_content = get_analysis_from_db(db_conn, "Future Research Proposal")
        
        gap_verification_content = get_analysis_from_db(db_conn, "Verification Report (Gap Analysis)")
        proposal_verification_content = get_analysis_from_db(db_conn, "Verification Report (Future Proposal)")

        if survey_content or gap_content or proposal_content: 
            print(" Successfully fetched analysis sections from the database.")
            
            generate_pdf_report(topic, survey_content, gap_content, proposal_content, 
                                gap_verification_content, proposal_verification_content)
        else:
            print(" CRITICAL: Could not find essential analysis data. Report generation skipped.")

    except Exception as e:
         print(f" An unexpected error occurred during report generation: {e}")
    finally:
        if db_conn and db_conn.is_connected():
            db_conn.close()

if __name__ == '__main__':
    try:
        topic_arg = input(" Enter the research topic for the report: ") if len(sys.argv) < 2 else sys.argv[1]

        if not os.path.exists(REPORTS_DIR):
            os.makedirs(REPORTS_DIR)
            print(f"Created directory: {REPORTS_DIR}")

        run_report_generation(topic_arg)
    except Exception as e:
        print(f" AN UNEXPECTED ERROR OCCURRED: {e}")
    finally:
        print("\n Agent run finished.")