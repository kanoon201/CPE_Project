# PICK'EM — Valorant Esports Prediction

ระบบเว็บแอปพลิเคชันสำหรับทายผลการแข่งขัน Valorant Esports แบบ Double Elimination Bracket ผู้ใช้สามารถทายผลแมตช์, ดูอันดับคะแนน, และติดตามสถิติทีมได้แบบ Real-time

---

## ฟีเจอร์หลัก

- **ระบบสมัคร / เข้าสู่ระบบ** — Register และ Login ด้วย Username / Password
- **ทายผลแมตช์** — เลือกทีมที่ชนะและสกอร์ของแต่ละแมตช์ใน Bracket
- **Double Elimination Bracket** — แสดง Upper / Lower / Grand Final พร้อม Bracket Propagation อัตโนมัติ
- **Leaderboard** — จัดอันดับผู้ทายผลตามคะแนนสะสม มีระบบ Podium Top 3
- **สถิติทีม** — W/L/PTS แยกตามทัวร์นาเมนต์ อัปเดตอัตโนมัติทุก 15 วินาที
- **หน้า Profile** — ดูประวัติการทายและสถิติส่วนตัวของผู้ใช้แต่ละคน
- **Admin Panel** — จัดการทัวร์นาเมนต์, ทีม, และผลแมตช์

---

## โครงสร้างโปรเจกต์

```
project/
├── backend/
│   ├── app.py                # Flask application หลัก
│   ├── db.py                 # MySQL & MongoDB connection
│   ├── seed_bracket.py       # สร้าง Bracket เริ่มต้น
│   └── requirements.txt
├── frontend/
│   ├── template/
│   │   ├── index.html        # Landing page
│   │   ├── tournaments.html  # หน้าเลือกทัวร์นาเมนต์
│   │   ├── predict.html      # หน้าทายผล
│   │   ├── matches.html      # Bracket viewer
│   │   ├── teams.html        # สถิติทีม
│   │   ├── leaderboard.html  # อันดับคะแนน
│   │   ├── user_profile.html # โปรไฟล์ผู้ใช้
│   │   ├── admin_tournaments.html
│   │   ├── login.html
│   │   └── register.html
│   └── static/
│       ├── styles.css          # Global styles + Navbar + Match cards
│       ├── landing.css         # Landing page / Hero section
│       ├── login-page.css      # Login & Register page
│       ├── predict.css         # หน้าทายผล + Admin panel
│       ├── bracket_styles.css  # Bracket viewer (matches.html)
│       ├── leaderboard.css     # Leaderboard + Podium
│       └── teams.css           # Teams standings table
└── database/
    └── pickem_database.sql   # MySQL Schema + Seed data
```

## การติดตั้งและรันโปรเจกต์

### 1. Clone Repository

```bash
git clone <repository-url>
cd project
```

### 2. ติดตั้ง Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. ตั้งค่า MySQL

```bash
mysql -u root -p < database/pickem_database.sql
```

### 4. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` หรือ export ตัวแปรดังนี้:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=pickem_db
MYSQL_PORT=3306

MONGO_URI=mongodb://localhost:27017
MONGO_DB=pickem_db
```

### 5. รัน Application

```bash
cd backend
python app.py
```

เปิด Browser ที่ `http://localhost:5001`

---

## ฐานข้อมูล

ระบบใช้ฐานข้อมูล **2 ประเภท** ทำงานร่วมกัน:

### MySQL — ข้อมูลเชิงสัมพันธ์
| ตาราง | หน้าที่ |
|-------|---------|
| `User` | บัญชีผู้ใช้ |
| `Team` | ทะเบียนทีมทั้งหมด |
| `TeamStats` | สถิติ W/L/PTS แยกตามทัวร์นาเมนต์ |
| `LeaderBoard` | คะแนนและอันดับผู้ใช้ |
| `Pickem_DATA` | ข้อมูลการทายแมตช์ของผู้ใช้ |

### MongoDB — ข้อมูล Bracket
| Collection | หน้าที่ |
|------------|---------|
| `tournaments` | Metadata ทัวร์นาเมนต์ + รายชื่อทีม |
| `tournaments` (matches) | โครงสร้าง Bracket และผลแมตช์แต่ละคู่ |

---

## ระบบคะแนน

คะแนนคำนวณตามรอบและความแม่นยำของการทาย:

| รอบ | คะแนนทายถูกทีม | คะแนนทายถูกทั้งทีมและสกอร์ |
|-----|---------------|--------------------------|
| Upper/Lower Quarterfinals | 5 | 10 |
| Upper/Lower Semifinals | 7.5 | 15 |
| Lower Round 3 | 12.5 | 25 |
| Upper/Lower Final | 15 | 30 |
| Grand Final | 20 | 40 |

---

## บัญชี Admin

ชื่อผู้ใช้สำหรับ Admin คือ **`ADMIN`** (ต้องสร้างผ่าน Register หน้าเว็บ)

Admin สามารถ:
- สร้าง / ลบ / เปิด-ปิด ทัวร์นาเมนต์
- เพิ่ม / แก้ไข / ลบ ทีม
- บันทึกผลแมตช์และ Bracket จะอัปเดตอัตโนมัติ

---

## API Endpoints

| Method | Path | หน้าที่ |
|--------|------|---------|
| GET | `/` | Landing page |
| GET | `/tournaments` | รายการทัวร์นาเมนต์ |
| GET | `/predict` | หน้าทายผล |
| POST | `/submit_prediction` | บันทึกการทาย |
| GET | `/matches` | Bracket viewer |
| GET | `/teams` | สถิติทีม |
| GET | `/teams/data` | API สถิติทีม (JSON) |
| GET | `/leaderboard` | อันดับคะแนน |
| GET | `/user/<username>` | โปรไฟล์ผู้ใช้ |
| GET | `/api/matches` | API ข้อมูลแมตช์ (JSON) |
| POST | `/admin/create_tournament` | สร้างทัวร์นาเมนต์ |
| POST | `/admin/update_match` | อัปเดตผลแมตช์ |
| POST | `/admin/set_active_tournament` | เปิด/ปิด ทัวร์นาเมนต์ |