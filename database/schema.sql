CREATE DATABASE IF NOT EXISTS bankdb;

USE bankdb;

CREATE TABLE customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    balance DECIMAL(12,2) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100),
    address VARCHAR(255),
    branch VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);