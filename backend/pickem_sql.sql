CREATE DATABASE IF NOT EXISTS pickem_db;
USE pickem_db;

DROP TABLE IF EXISTS User;
DROP TABLE IF EXISTS Team;
DROP TABLE IF EXISTS LeaderBoard;
DROP TABLE IF EXISTS Pickem_DATA;
-- ---------------- USER ----------------
CREATE TABLE IF NOT EXISTS User (
    User_id INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL
);

-- ---------------- TEAM ----------------
CREATE TABLE IF NOT EXISTS Team (
    Team_id INT AUTO_INCREMENT PRIMARY KEY,
    Teamname VARCHAR(100) NOT NULL,
    Shortname VARCHAR(20) NOT NULL UNIQUE,
    Region VARCHAR(100)
);

-- ---------------- LEADERBOARD ----------------
CREATE TABLE IF NOT EXISTS LeaderBoard (
    User_id INT PRIMARY KEY,
    Username VARCHAR(100) NOT NULL,
    Score INT DEFAULT 0,
    Ranking INT DEFAULT NULL,
    FOREIGN KEY (User_id) REFERENCES User(User_id)
        ON DELETE CASCADE
);

-- ---------------- PICKEM_DATA ----------------
CREATE TABLE IF NOT EXISTS Pickem_DATA (
    Pickem_id INT AUTO_INCREMENT PRIMARY KEY,
    Match_id VARCHAR(50) NOT NULL,
    User_id INT NOT NULL,
    Predict_Winner VARCHAR(20),
    Predict_Score VARCHAR(20),
    FOREIGN KEY (User_id) REFERENCES User(User_id)
        ON DELETE CASCADE
);