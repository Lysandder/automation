import os
from dotenv import load_dotenv

load_dotenv(".env")

ORIGIN = os.environ["ORIGIN"]
EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
LOGIN_URL = os.environ["LOGIN_URL"]
PROFILE_URL = os.environ["PROFILE_URL"]
DECK_URL = os.environ["DECK_URL"]
TRANSACTIONS_URL = os.environ["TRANSACTIONS_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]
MINE_URL = os.environ["MINE_URL"]
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
ADMIN_TG_USER = os.environ["ADMIN_TG_USER"]
PROXY_URL = os.environ["PROXY_URL"]
SHOJOS_URL = os.environ["SHOJOS_URL"]

