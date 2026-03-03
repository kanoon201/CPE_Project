CREATE DATABASE IF NOT EXISTS pickem_db;
USE pickem_db;

DROP TABLE IF EXISTS Pickem_DATA;
DROP TABLE IF EXISTS TeamStats;
DROP TABLE IF EXISTS LeaderBoard;
DROP TABLE IF EXISTS Team;
DROP TABLE IF EXISTS User;

-- ---------------- USER ----------------
CREATE TABLE IF NOT EXISTS User (
    User_id INT AUTO_INCREMENT PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    Password VARCHAR(255) NOT NULL
);

-- ---------------- TEAM (master list — ไม่มี W/L/PTS แล้ว) ----------------
CREATE TABLE IF NOT EXISTS Team (
    Team_id INT AUTO_INCREMENT PRIMARY KEY,
    Teamname VARCHAR(100) NOT NULL,
    Shortname VARCHAR(20) NOT NULL UNIQUE,
    Region VARCHAR(100),
    Logo VARCHAR(255)
);

-- ---------------- TEAM STATS (แยกต่อ tournament) ----------------
CREATE TABLE IF NOT EXISTS TeamStats (
    Stat_id INT AUTO_INCREMENT PRIMARY KEY,
    Tournament_id VARCHAR(100) NOT NULL,
    Shortname VARCHAR(20) NOT NULL,
    Wins INT DEFAULT 0,
    Losses INT DEFAULT 0,
    Points INT DEFAULT 0,
    UNIQUE KEY unique_team_tournament (Tournament_id, Shortname)
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

-- ---------------- PICKEM_DATA (เพิ่ม Tournament_id) ----------------
CREATE TABLE IF NOT EXISTS Pickem_DATA (
    Pickem_id INT AUTO_INCREMENT PRIMARY KEY,
    Tournament_id VARCHAR(100) NOT NULL DEFAULT 'vct-2026',
    Match_id VARCHAR(50) NOT NULL,
    User_id INT NOT NULL,
    Predict_Winner VARCHAR(20),
    Predict_Score VARCHAR(20),
    FOREIGN KEY (User_id) REFERENCES User(User_id)
        ON DELETE CASCADE,
    UNIQUE KEY unique_user_match_tournament (Tournament_id, Match_id, User_id)
);

-- ---------------- insert master teams ----------------
INSERT INTO Team (Teamname, Shortname, Region, Logo) VALUES
('NRG',           'NRG',  'United States', 'https://owcdn.net/img/6610f026c1a9e.png'),
('Fnatic',        'FNC',  'Europe',        'https://owcdn.net/img/62a40cc2b5e29.png'),
('DRX',           'DRX',  'South Korea',   'https://owcdn.net/img/63b17ac3a7d00.png'),
('Paper Rex',     'PRX',  'Singapore',     'https://owcdn.net/img/62bbebb185a7e.png'),
('MIBR',          'MIBR', 'Brazil',        'https://owcdn.net/img/632be767b57aa.png'),
('Team Heretics', 'TH',   'Europe',        'https://owcdn.net/img/637b7557a9225.png'),
('G2 Esports',    'G2',   'United States', 'https://owcdn.net/img/633822848a741.png'),
('Full Sense',    'FS',   'Thailand',      'https://owcdn.net/img/6537a7954d915.png');

-- ---------------- seed TeamStats for existing tournament ----------------
INSERT INTO TeamStats (Tournament_id, Shortname, Wins, Losses, Points) VALUES
('vct-2026', 'NRG',  0, 0, 0),
('vct-2026', 'FNC',  0, 0, 0),
('vct-2026', 'DRX',  0, 0, 0),
('vct-2026', 'PRX',  0, 0, 0),
('vct-2026', 'MIBR', 0, 0, 0),
('vct-2026', 'TH',   0, 0, 0),
('vct-2026', 'G2',   0, 0, 0),
('vct-2026', 'FS',   0, 0, 0);

-- ---------------- useful queries ----------------
-- SELECT * FROM User;
-- SELECT * FROM Team;
-- SELECT * FROM TeamStats WHERE Tournament_id = 'vct-2026';
-- SELECT * FROM Pickem_DATA WHERE Tournament_id = 'vct-2026';