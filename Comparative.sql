-- Select the database to make sure you're in the right place
USE agentic_ai_db;

-- Create a new table specifically for storing high-level analysis results
CREATE TABLE analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    analysis_type VARCHAR(255) NOT NULL,
    content MEDIUMTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);