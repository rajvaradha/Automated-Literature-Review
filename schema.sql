-- Select the database to use first
USE agentic_ai_db;

-- Create the initial table structure
CREATE TABLE papers1 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    authors TEXT,
    publication_year INT,
    source VARCHAR(50),
    source_url VARCHAR(512) UNIQUE,
    abstract TEXT,
    retrieved_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(512),
    full_text LONGTEXT,
    summary TEXT
);
