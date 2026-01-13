USE agentic_ai_db;

-- This query selects ONLY the final research proposal from the analyses table
SELECT * FROM analyses 
WHERE analysis_type = 'Detailed Future Research Proposal';

