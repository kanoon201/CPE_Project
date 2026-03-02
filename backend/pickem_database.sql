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
    Region VARCHAR(100),
    Logo VARCHAR(255),
    
    Wins INT DEFAULT 0,
    Losses INT DEFAULT 0,
    Points INT DEFAULT 0
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
ALTER TABLE Pickem_DATA
ADD UNIQUE KEY unique_user_match (Match_id, User_id);


-- ---------------- Quray output ----------------
SELECT * FROM User;
SELECT * FROM Team;
SELECT * FROM LeaderBoard;
SELECT * FROM Pickem_DATA;
SELECT Teamname, Logo FROM Team;

-- ---------------- Quray delete data ----------------
TRUNCATE TABLE Pickem_DATA;
TRUNCATE TABLE Team;

-- ---------------- insert teams data----------------
INSERT INTO Team
(Teamname, Shortname, Region, Logo, Wins, Losses, Points)
VALUES
('NRG', 'NRG', 'United States', 'https://owcdn.net/img/6610f026c1a9e.png', 0, 0, 0),
('Fnatic', 'FNC', 'Europe','https://owcdn.net/img/62a40cc2b5e29.png', 0, 0, 0),
('DRX', 'DRX', 'South Korea','https://owcdn.net/img/63b17ac3a7d00.png', 0, 0, 0),
('Paper Rex', 'PRX', 'Singapore','https://owcdn.net/img/62bbebb185a7e.png', 0, 0, 0),
('MIBR', 'MIBR', 'Brazil','https://owcdn.net/img/632be767b57aa.png', 0, 0, 0),
('Team Heretics', 'TH', 'Europe','https://owcdn.net/img/637b7557a9225.png', 0, 0, 0),
('G2 Esports', 'G2', 'United States','https://owcdn.net/img/633822848a741.png', 0, 0, 0),
('Full Sense', 'FS', 'Thailand','https://owcdn.net/img/6537a7954d915.png', 0, 0, 0);
