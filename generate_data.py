import json
import re
import time
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
# Map to LotteryCorner URLs
GAME_MAP = {
    "pick-3": "fl/pick-3",
    "pick-4": "fl/pick-4",
    "pick-5": "fl/pick-5",
    "pick-2": "fl/pick-2",
    "fantasy-5": "fl/fantasy-5",
    "florida-lotto": "fl/florida-lotto",
    "jackpot-triple-play": "fl/jackpot-triple-play",
    "cash4life": "fl/cash4life",
    "powerball": "fl/powerball",
    "mega-millions": "fl/mega-millions"
}

YEARS_TO_SCRAPE = [2024, 2023]

def run():
    full_database = {}

    with sync_playwright() as p:
        print("🤖 LAUNCHING BROWSER...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # --- THE HUMAN HANDSHAKE ---
        print("\n🛑 STEP 1: Opening LotteryCorner...")
        page.goto("https://www.lotterycorner.com/fl", timeout=60000)
        
        print("👉 Look at the browser.")
        print("👉 If you see a Cloudflare check, CLICK IT.")
        print("👉 Wait until you see the Florida Lottery page.")
        
        input("\n✅ When the site is loaded, press ENTER here to start scraping...")

        print("\n🚀 SCRAPING STARTED!...")

        for game_slug, url_part in GAME_MAP.items():
            print(f"------------------------------------------------")
            print(f"📥 Processing {game_slug}...")
            
            game_data = {}
            
            for year in YEARS_TO_SCRAPE:
                url = f"https://www.lotterycorner.com/{url_part}/winning-numbers/{year}"
                print(f"   Browsing {year}...", end=" ", flush=True)
                
                try:
                    page.goto(url, timeout=30000)
                    
                    # LotteryCorner uses a simple table
                    # Wait for table rows
                    try:
                        page.wait_for_selector("tbody tr", timeout=5000)
                    except:
                        print(" (No data table found)")
                        continue

                    rows = page.query_selector_all("tbody tr")
                    draws_found = 0
                    
                    for row in rows:
                        # 1. Get Date Text (usually in the first TD or just text)
                        row_text = row.inner_text()
                        
                        # Date Format: "Thu, Oct 26, 2023"
                        date_match = re.search(r'([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})', row_text)
                        
                        if date_match:
                            m, d, y = date_match.groups()
                            try:
                                dt = time.strptime(f"{m} {d} {y}", "%b %d %Y")
                                iso_date = time.strftime("%Y-%m-%d", dt)
                                
                                # 2. Get Numbers
                                # LotteryCorner puts numbers in <ul><li> or <span class="ball">
                                # We grab specifically from list items to avoid grabbing the date digits
                                ball_elements = row.query_selector_all("li")
                                
                                # If no li, try spans
                                if not ball_elements:
                                    ball_elements = row.query_selector_all("span.ball")
                                
                                current_nums = []
                                for ball in ball_elements:
                                    num_text = ball.inner_text().strip()
                                    if num_text.isdigit():
                                        current_nums.append(num_text)
                                
                                if current_nums:
                                    # Config Limits
                                    limit = 6
                                    if "pick" in game_slug: limit = int(game_slug.split("-")[-1])
                                    if "fantasy" in game_slug: limit = 5
                                    if "pick-2" in game_slug: limit = 2
                                    
                                    valid_nums = current_nums[:limit]
                                    
                                    # LotteryCorner lists Evening first (top of page). 
                                    # If we already have this date, skip (keep the first/latest one)
                                    if iso_date not in game_data:
                                        game_data[iso_date] = valid_nums
                                        draws_found += 1
                            except:
                                continue
                                
                    print(f"✅ Found {draws_found}")
                    
                except Exception as e:
                    print(f"❌ Error: {e}")
                
                time.sleep(0.5)

            full_database[game_slug] = game_data
            print(f"   🎉 Total History for {game_slug}: {len(game_data)} days")

        browser.close()

    # SAVE TO FILE
    with open("history.json", "w") as f:
        json.dump(full_database, f)
    
    print("\n================================================")
    print("✨ DONE! 'history.json' created.")
    print("👉 NEXT STEP: git add . && git commit -m 'Add DB' && git push")
    print("================================================")

if __name__ == "__main__":
    run()
