Project Documentation: Serverless Lottery API Middleware
1. Project Overview
Goal: Create a free, maintenance-free API to serve Lottery data (Powerball) for Florida and Texas to an iOS application.
Constraint: No database allowed. Must support "Latest Results" and "Historical Results" (e.g., tickets from 5 months ago).
Hosting: Vercel (Serverless Python Functions).

2. Technology Stack
Language: Python 3.9+
Framework: FastAPI (for API endpoints)
Scraping: requests (HTTP), beautifulsoup4 (HTML Parsing), re (Regex).
Infrastructure: Vercel (Serverless Deployment via GitHub integration).
3. Architecture & Data Flow
The "Hybrid Source" Strategy
We discovered that official government websites (e.g., flalottery.com) block cloud server IPs (AWS/Vercel) via WAF/Bot protection. To bypass this without paying for proxies, we implemented a Hybrid Aggregator Strategy:

For Latest Data (Default):

Source: lotteryusa.com
Reason: Reliable "Latest" page, simple HTML structure, friendly to bots.
Logic: Scrapes the specific state page (e.g., /florida/powerball/) and extracts the first row of numbers.
For Historical Data (Date Parameter Provided):

Source: lottery.net
Reason: lotteryusa.com had broken/missing year archives. lottery.net maintains a clean, table-based National Powerball archive.
Logic: Since Powerball numbers are national, we do not need state-specific archives. We scrape lottery.net/powerball/numbers/YYYY.
4. API Endpoints
Base URL
https://[your-vercel-project].vercel.app

GET /api/florida
Parameters:
date (Optional): String in YYYY-MM-DD format.
Behavior:
If date is missing: Returns latest draw from LotteryUSA.
If date is present: Returns historical draw from Lottery.net.
GET /api/texas
Parameters:
date (Optional): String in YYYY-MM-DD format.
Behavior: Same logic as Florida.
5. Key Logic & Parsing Rules (The "V9" Script)
A. Date Parsing
The API accepts YYYY-MM-DD (Computer format) but the scraping targets use "Human" formats.

Logic: The script generates 4 variations of the date to search for in the HTML text:
"Oct 25" (Abbreviated Month + Day)
"October 25" (Full Month + Day)
"10/25" (Numeric)
"Oct 25" (No zero-padding on day)
B. Number Extraction (Regex)
Lottery websites often clutter data with text like "Powerball: 10" or "PB 10".

Logic: We use a regex helper re.search(r'\d+', text) to extract pure integers from table cells.
Filtering: We reject numbers that contain date-like characters (/ or ,) or text.
C. Data Cleaning
Limit: The scraper forces a limit of 6 numbers (5 White + 1 Red). This prevents capturing "Double Play" numbers or "Power Play" multipliers that often appear in the same table row.
Deduplication: Duplicates are removed while preserving order.
6. How to Deploy / Update
The project is set up with Continuous Deployment (CD).

Edit scraper.py or main.py locally.
Run generic git commands:
bash
git add .
git commit -m "Description of change"
git push
Vercel detects the push to GitHub and automatically redeploys the API within 60 seconds.
7. Current Codebase Reference (V9)
Use this context if asking an AI to fix a bug.

main.py (Entry Point):
Standard FastAPI setup defining routes that call get_florida_data or get_texas_data.

scraper.py (Core Logic):

scrape_latest(state, game): Hits lotteryusa.com. Looks for the first <ul> or <tr> containing >4 digits.
scrape_history(state, game, date_obj): Hits lottery.net/powerball/numbers/YYYY. Scans every <tr> in the table. If a row's text matches one of the date variations, it extracts numbers from <li> or <td> tags.
8. Client Integration (iOS/Swift)
The iOS app uses URLSession to fetch JSON.

Model: LottoResult (Codable).
Mapping: JSON winning_numbers maps to Swift winningNumbers.
Usage: The app checks if a user is looking at a past ticket, formats the date to yyyy-MM-dd, and appends it to the API URL.
Prompt for Future AI Assistance
If you need help in the future, paste this block below into the chat:

"I have a Python FastAPI project hosted on Vercel acting as a lottery scraper.
It uses a hybrid approach: scraping lotteryusa.com for latest results and lottery.net for historical archives (searching by year).
The code parses HTML using BeautifulSoup and Regex.
Currently, the endpoint is returning [DESCRIBE ERROR].
Please analyze the scraper.py logic considering that the source website HTML structure might have changed."

# Serverless Lottery API (Hybrid Architecture)

A free, robust REST API for retrieving Florida Lottery results (Latest & History).

## 🚀 The Architecture: "The Hybrid Model"

Traditional web scraping on serverless clouds (like Vercel/AWS) fails because lottery websites block data center IP addresses (Cloudflare, WAFs, SSL blocks).

To solve this, this project uses a **Hybrid Approach**:

1.  **Historical Data (Local Generation):**
    *   We use a local Python script (`generate_data.py`) running **Playwright** (a real browser automation tool) on a local machine to scrape years of history.
    *   This generates a static database file: `history.json`.
    *   Since this runs locally, it passes "Human Verification" checks and Captchas easily.
    *   This file is uploaded to Vercel.

2.  **Latest Data (Live Scraping):**
    *   For *today's* results, the API uses a lightweight scraper (`scraper.py`) targeting `LotteryUSA`, which has lower security protections and allows serverless traffic.

3.  **The API (Vercel):**
    *   The FastAPI app checks if the user wants a specific date.
    *   **If History:** It reads from `history.json` (0ms latency, 100% reliability).
    *   **If Latest:** It scrapes live.

---

## 🛠 Project Structure

*   **`main.py`**: The FastAPI application entry point. Routes traffic.
*   **`scraper.py`**: Contains the logic to scrape *Latest* results only.
*   **`generate_data.py`**: (Local Utility) The Robot Browser that builds the database.
*   **`history.json`**: The static database containing past results.
*   **`requirements.txt`**: Python dependencies.
*   **`vercel.json`**: Configuration for serverless deployment.

---

## 🎮 Supported Games

| Game Slug | Description | Limit |
| :--- | :--- | :--- |
| `powerball` | National Powerball | 6 Numbers |
| `mega-millions` | National Mega Millions | 6 Numbers |
| `cash4life` | Cash 4 Life | 6 Numbers |
| `florida-lotto` | Florida Lotto | 6 Numbers |
| `jackpot-triple-play` | Jackpot Triple Play | 6 Numbers |
| `fantasy-5` | Fantasy 5 | 5 Numbers |
| `pick-5` | Pick 5 (Evening) | 5 Numbers |
| `pick-4` | Pick 4 (Evening) | 4 Numbers |
| `pick-3` | Pick 3 (Evening) | 3 Numbers |
| `pick-2` | Pick 2 (Evening) | 2 Numbers |

---

## 🔌 API Endpoints

### 1. Get Latest Results
**Request:**
`GET /api/florida/{game}`

**Example:**
`GET /api/florida/powerball`

**Response:**
```json
{
  "state": "FLORIDA",
  "game": "powerball",
  "date_requested": "Latest",
  "source": "lotteryusa.com",
  "winning_numbers": ["10", "20", "30", "40", "50", "05"]
}
