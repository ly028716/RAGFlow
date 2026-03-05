-- MySQL initialization script
-- This script is automatically executed when MySQL container starts for the first time

-- Set character set and collation
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Create database if not exists (already handled by docker-compose, but kept for reference)
-- CREATE DATABASE IF NOT EXISTS ragflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE ragflow;

-- Grant privileges (if needed)
-- GRANT ALL PRIVILEGES ON ragflow.* TO 'ragflow_user'@'%';
-- FLUSH PRIVILEGES;

-- Log initialization
SELECT 'Database initialization script executed successfully' AS message;
