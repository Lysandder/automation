from datetime import datetime
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
import random
import time
from itertools import islice
import flask
import psycopg2
import subprocess
import sys
import traceback
import functools
import shutil

import os
from dotenv import load_dotenv
load_dotenv(".env")
PROFILE_URL = os.getenv("PROFILE_URL")
LOGIN_URL = os.getenv("LOGIN_URL")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
DECK_URL = os.getenv("DECK_URL")
TRANSACTIONS_URL = os.getenv("ADS_URL")
SHOJOS_URL = os.getenv("SHOJOS_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
MINE_URL = os.getenv("MINE_URL")


def print_cyan(text: str):
    print(f"\033[96m{text}\033[0m")


def print_red(text: str):
    print(f"\033[91m{text}\033[0m")


# Check of env variables
REQUIRED_ENV_VARS = ["PROFILE_URL", "LOGIN_URL", "EMAIL", "PASSWORD",
                     "DECK_URL", "ADS_URL", "SHOJOS_URL", "DATABASE_URL", "MINE_URL"]

for key in REQUIRED_ENV_VARS:
    val = os.getenv(key)
    if not val:
        print_red(f"[ENV ERROR] Missing env var: {key}")

WORDS_LIST = ["Good", "Bad", "New", "Else"]


def safe_goto(page, url, label=""):
    try:
        page.goto(url)
    except Exception as e:
        print_red(
            f"[GOTO ERROR] title='{page.title()}' url='{page.url}': \n{e}")


def safe_click(page, selector, label=""):
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.click(selector)
    except Exception as e:
        print_red(f"[CLICK ERROR] {label or selector}: {e}")
        raise


def safe_fill(page, selector, value, label=""):
    try:
        page.wait_for_selector(selector, timeout=10000)
        page.fill(selector, value)
    except Exception as e:
        print_red(f"[FILL ERROR] {label or selector}: {e}")
        raise


def log_job(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        print_cyan(f"[JOB START] {fn.__name__} at {datetime.now()}")
        try:
            result = fn(*args, **kwargs)
            print_cyan(f"[JOB OK] {fn.__name__} at {datetime.now()}")
            return result
        except Exception as e:
            print_red(f"[JOB FAILED] {fn.__name__}: {e}")
            print_red(traceback.format_exc())
    return wrapper


executors = {
    'default': ThreadPoolExecutor(max_workers=1)  # only 1 job runs at a time
}

app = flask.Flask(__name__)


@app.route("/")
def home():
    return "OK", 200


def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print_red(f"[DB CONNECTION ERROR] {e}")
        raise


def scheduling():
    # SCHEDULING
    scheduler = BackgroundScheduler(
        timezone="Asia/Tashkent", executors=executors)
    start_time = datetime.now()
    minutes = (start_time.minute + 30) % 60
    scheduler.add_job(read_chapters, 'interval', hours=1,
                      next_run_time=start_time, max_instances=1)
    scheduler.add_job(leave_comments, 'cron', hour=3,
                      minute=minutes, max_instances=1)
    scheduler.add_job(watch_ads, 'cron', hour=4,
                      minute=minutes, max_instances=1)
    scheduler.start()

    print_cyan(f"Reading chapters time: {start_time.minute}")
    print_cyan(f"Leave comments time: 3:{minutes}")
    print_cyan(f"Watch ADS time: 4:{minutes}")


def install_chromium():
    #
    # print_cyan("Starting Installing Dependencies...")
    # subprocess.run([
    #     "apt-get", "install", "-y",
    #     "libnss3", "libatk1.0-0", "libatk-bridge2.0-0",
    #     "libcups2", "libdrm2", "libxkbcommon0", "libxcomposite1",
    #     "libxdamage1", "libxfixes3", "libxrandr2", "libgbm1",
    #     "libasound2"
    # ], check=True)
    # subprocess.run(["playwright", "install-deps", "chromium"], check=True)

    print_cyan("Starting Installing Chromium...")
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/project/src/.playwright-browsers"
    subprocess.run(["playwright", "install", "chromium"],
                   check=True, env=env, timeout=300)
    print_cyan("Finished Installing Chromium")

    scheduling()


def check_chromium():
    path = shutil.which("chromium") or shutil.which("chromium-browser")
    print_cyan(f"  [CHROMIUM] which chromium: {path}")
    pw_path = "/opt/render/project/src/.playwright-browsers"
    print_cyan(f"  [CHROMIUM] browsers path exists: {os.path.exists(pw_path)}")
    if os.path.exists(pw_path):
        print_cyan(f"  [CHROMIUM] contents: {os.listdir(pw_path)}")
    else:
        print_cyan("[CHROMIUM] Browsers path does not exist!")
    if not path and not os.path.exists(pw_path):
        print_cyan(
            "[CHROMIUM] Chromium is NOT installed anywhere — jobs will fail!")


def get_index():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM state WHERE key = 'index'")
    index = cur.fetchone()[0]
    cur.close()
    conn.close()
    return index


def set_index(index):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE state SET value = %s WHERE key = 'index'", (index,))
    conn.commit()
    cur.close()
    conn.close()


def get_links(index):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT link FROM chapters
        WHERE id >= %s
        ORDER BY id
        LIMIT 4
    """, (index,))
    links = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return links


def cleanup(browser):
    for page in browser.pages:
        page.close()


def ensure_logged_in(page):
    # page.goto(PROFILE_URL)
    safe_goto(page, PROFILE_URL)

    if "login" in page.url.lower():
        print_cyan("[LOGIN] Not logged in — attempting login...")
        # page.goto(LOGIN_URL)
        safe_goto(page, LOGIN_URL)
        time.sleep(random.randint(3, 7))
        # page.fill(".form__field[type='email']", EMAIL)
        safe_fill(page, ".form__field[type='email']", EMAIL)
        # page.fill(".form__field[type='password']", PASSWORD)
        safe_fill(page, ".form__field[type='password']", PASSWORD)
        # page.click(".login-button")
        safe_click(page, ".login-button")
        page.wait_for_timeout(random.randint(5182, 7382))  # in ms

        if "login" in page.url.lower():
            print_red(
                "[LOGIN FAILED] Still on login page — credentials wrong or blocked?")


def get_browser(p):
    try:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./user_data",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )

        return browser
    except Exception as e:
        print_red(f"  [BROWSER FAIL] Could not launch browser: {e}")
        print_red(traceback.format_exc())
        return


@log_job
def read_chapters():  # 4 with a delay 2.5-3.5 minutes
    with sync_playwright() as p:
        browser = get_browser(p)

        cleanup(browser)
        page = browser.new_page()

        ensure_logged_in(page)
        print_cyan("LOGIN OK")

        # with open("index.txt", 'r') as file:
        #     index = int(file.readline().strip())
        #
        # with open("chapters.txt", 'r') as file:
        #     links = [line.strip()
        #              for line in islice(file, index - 1, index + 3)]

        index = get_index()
        links = get_links(index)

        completed = 0
        for link in links:
            try:
                # page.goto(link)
                safe_goto(page, link)
                time.sleep(random.randint(1, 3))
                js_command = """
                    read_status_send = false; 
                    is_read = true; 
                    loadTime = new Date().getTime() - 11000; 
                    addHistory(); 
                    let items = JSON.parse(localStorage.getItem('history_pool')) || []; 
                    if (items.length > 0) { 
                        $.post("/addHistory?r=702", { items: items }, function (data) { 
                            localStorage.setItem('history_pool', JSON.stringify([]));
                            console.log('Batch sent to server:', data); 
                        });
                    }
                """
                page.evaluate(js_command)
                completed += 1
                print_cyan(f"Read {completed} chapter(s)")
                if link != links[-1]:
                    time.sleep(60)

            except Exception:
                ensure_logged_in(page)

        # with open("index.txt", 'w') as file:
        #     file.write(f"{index}")
        set_index(index + completed)

        browser.close()


@log_job
def leave_comments():  # 10 with a delay 10-30 seconds
    with sync_playwright() as p:
        browser = get_browser(p)

        cleanup(browser)
        page = browser.new_page()

        ensure_logged_in(page)
        print_cyan("Ensured login")

        # page.goto(DECK_URL)
        safe_goto(page, DECK_URL)
        # time.sleep(random.randint(3, 7))
        # page.click(".comments__send-form--mini")
        safe_click(page, ".comments__send-form--mini")

        for i in range(10):
            try:
                # page.fill(".comments__send-form textarea", "Something " + WORDS_LIST[random.randint(0, 3)])
                safe_fill(page, ".comments__send-form textarea",
                          "Something " + WORDS_LIST[random.randint(0, 3)])
                # page.click(".comments__send-btn")
                safe_click(page, ".comments__send-btn")

                print_cyan(f"Left {i + 1} comment(s)")

                delay = random.randint(10, 30)
                time.sleep(delay)
            except Exception:
                ensure_logged_in(page)

        browser.close()


@log_job
def watch_ads():
    with sync_playwright() as p:
        browser = get_browser(p)

        cleanup(browser)
        page = browser.new_page()

        ensure_logged_in(page)
        print_cyan("Ensured login")

        # page.goto(TRANSACTIONS_URL)
        safe_goto(page, TRANSACTIONS_URL)
        time.sleep(random.randint(3, 7))

        for i in range(3):
            try:
                # page.click(".user-quest__watch-ads-btn")
                safe_click(page, ".user-quest__watch-ads-btn")
                time.sleep(35)  # ads last either 20 or 30 seconds
                # page.click("[data-fullscreen-element-name='close-btn']")
                safe_click(page, "[data-fullscreen-element-name='close-btn']")
                print_cyan(f"Watched {i + 1} AD(s)")
                time.sleep(random.randint(2, 4))
            except Exception:
                ensure_logged_in(page)
                # page.goto(TRANSACTIONS_URL)
                safe_goto(page, TRANSACTIONS_URL)

        browser.close()


@log_job
def get_daily_calendar_gift():
    with sync_playwright() as p:
        browser = get_browser(p)

        cleanup(browser)
        page = browser.new_page()

        ensure_logged_in(page)
        print_cyan("Ensured login")

        safe_goto(page, TRANSACTIONS_URL)
        time.sleep(random.randint(3, 7))

        try:
            safe_click(page, ".daily-rewards-btn")
            time.sleep(random.randint(3, 7))
            safe_click(page, ".daily-rewards-item-exp--active")
        except Exception:
            print_red("Calendar Error - Maybe could not find the button")

        browser.close()


@log_job
def mine():
    with sync_playwright() as p:
        browser = get_browser(p)

        cleanup(browser)
        page = browser.new_page()

        ensure_logged_in(page)
        print_cyan("Ensured login")

        safe_goto(page, MINE_URL)
        time.sleep(random.randint(3, 7))

        try:
            js_command = """() => new Promise((resolve) => {
                function autoTap100() {
                    const hitsLeftEl = document.querySelector('[id*="hits"], [class*="hits"]');
                    const raw = hitsLeftEl ? hitsLeftEl.textContent.replace(/,/g, '') : '100';
                    const total = parseInt(raw) || 100;
                    let count = 0;
                    const delay = 300;
                    function sendHit() {
                        if (count >= total) {
                            console.log('Done! Sent ' + total + ' hits.');
                            resolve(total);
                            return;
                        }
                        $.post('/mine/hit', {}, function(res) {
                            count++;
                            console.log(`Hit ${count}/${total} — Ore: ${res.ore}, Hits left: ${res.hits_left}`);
                            setTimeout(sendHit, delay);
                        }).fail(function(err) {
                            count++;
                            const msg = err.responseJSON?.message || 'Unknown error';
                            console.warn(`Hit ${count} failed: ${msg}`);
                            setTimeout(sendHit, delay);
                        });
                    }
                    sendHit();
                }
                autoTap100();
            })"""
            page.evaluate(js_command)
        except Exception as e:
            print_red("ERROR while mining")
            print_red(str(e))

        browser.close()


# def scrape_names():
#     with sync_playwright() as p:
#         browser = p.chromium.launch_persistent_context(
#             user_data_dir="./user_data", headless=True)
#
#         cleanup(browser)
#         page = browser.new_page()
#
#         ensure_logged_in(page)
#
#         page.goto(SHOJOS_URL) # not safe goto
#         time.sleep(random.randint(3, 7))
#
#         next_page_button = page.locator(
#             "li.pagination__button a", has_text="Вперёд")
#
#         while (next_page_button.count() > 0):
#             names_links = page.eval_on_selector_all(
#                 "a.cards__item",
#                 "els => els.map(el => el.href)"
#             )
#             with open("names.txt", 'a') as file:
#                 for link in names_links:
#                     file.write(link + "\n")
#             next_page_button.click() # not safe click
#             time.sleep(random.randint(2, 5))
#
#         browser.close()
#
#
# def scrape_chapters():
#     with sync_playwright() as p:
#         browser = p.chromium.launch_persistent_context(
#             user_data_dir="./user_data", headless=True)
#
#         cleanup(browser)
#         page = browser.new_page()
#
#         ensure_logged_in(page)
#
#         with open("names.txt", "r") as names_file:
#             for line in names_file:
#                 # for line in islice(names_file, 204, None):
#                 page.goto(line.strip()) # not safe goto
#                 time.sleep(random.randint(1, 5))
#
#                 if page.is_disabled("button[data-page='chapters']"):
#                     print_cyan("=" * 100)
#                     print_cyan(line)
#                     print_cyan("=" * 100)
#                     continue
#                 page.click("button[data-page='chapters']") # not safe click
#
#                 chapters_links = page.eval_on_selector_all(
#                     ".chapters__list a.chapters__item",
#                     "els => els.map(el => el.href)"
#                 )
#
#                 with open("chapters.txt", 'a') as file:
#                     for link in chapters_links:
#                         file.write(link + "\n")
#                 time.sleep(random.randint(1, 5))
#
#         browser.close()


# scrape_names()
# scrape_chapters()

# thread = threading.Thread(target=install_chromium, daemon=True)
# thread.start()

# print_cyan("[STARTUP] Checking Chromium before scheduling...")
# check_chromium()
# print_cyan("[STARTUP] Starting scheduler...")
# scheduling()
# print_cyan("[STARTUP] Scheduler started. Flask starting...")

# leave_comments()
# watch_ads()
# get_daily_calendar_gift()
mine()

# if __name__ == "__main__":
port = int(os.environ.get("PORT", 3000))
app.run(host="0.0.0.0", port=port)
