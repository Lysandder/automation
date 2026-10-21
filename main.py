import info
import postgresql
import bot

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import socketio
import asyncio

import time
import random
import re # soup.find for finding patterns in html, re module or regular expressions (regex) for patterns in a string
import json


def human_delay(min_sec: float = 2.0, max_sec: float = 6.0):
    time.sleep(random.uniform(min_sec, max_sec))


def sync_csrf_token(sess: requests.Session) -> bool:
    main_page = sess.get(url=info.ORIGIN)
    soup = BeautifulSoup(main_page.text, "html.parser")
    csrf_meta = soup.find("meta", {"name": "csrf-token"})
    csrf_token = csrf_meta.get("content") if csrf_meta else None
    if not csrf_token:
        return False
    sess.headers["X-CSRF-TOKEN"] = str(csrf_token)
    return True


def ajax_headers(referer_url: str, origin_url: str | None = None, content_type: str | None = None) -> dict:
    headers = {
        "Referer": referer_url,
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if origin_url:
        headers["Origin"] = origin_url
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def get_user_id(sess: requests.Session) -> int | None:
    main_page = sess.get(url=info.ORIGIN)
    soup = BeautifulSoup(main_page.text, "html.parser")

    # <script> tag that contains the user_id
    script_tag = soup.find("script", string=re.compile(r"window\.user_id\s*="))
    if script_tag:
        match = re.search(r"window\.user_id\s*=\s*(\d+);", str(script_tag.string))
        if match:
            user_id = int(match.group(1))
            return user_id
    return


def get_card_notification(sess: requests.Session):
    notifications_page = sess.get(url=f"{info.ORIGIN}/notifications")
    soup = BeautifulSoup(notifications_page.text, "html.parser")
    # control_header = soup.find("div", class_="notifications__header-controls")
    # if control_header:
    #     card_notification = control_header.find_next_sibling("div", class_="notifications__item--not-read")
    # if not control_header or not card_notification:
    card_notification = soup.select_one(".notifications__item--not-read")

    if not card_notification:
        print("No unread notification found.")
        return

    # checking if href=products - it is a card
    image_a_tag = card_notification.select_one("a.notifications__image")
    image_href = image_a_tag.get("href") if image_a_tag else None
    if image_href != "/products":
        print("This is not a card notification")
        return

    notification_content = card_notification.select_one("div.notifications__name").get_text(strip=True)
    card_name = re.search(r",\s*(?P<card_name>.+?)\s*[--\-]", notification_content).group("card_name")

    card_link = card_notification.select_one("div.notifications__name a").get("href")
    card_id = int(re.search(r"card=(\d+)", card_link).group(1))

    return {
        "card_name": card_name,
        "card_id": card_id
    }


def get_card_info(sess: requests.Session, card_id: int, card_name: str) -> dict | None:
    user_id = get_user_id(sess=sess)
    human_delay()

    # Searching all cards of a user with that name
    all_search_cards_list: list = []
    total_cards: int = 0

    offset = 0
    limit = 160

    while True:
        params = {
            "user_id": user_id,
            "q": card_name,
            "offset": offset,
        }
        search_cards = sess.get(url=f"{info.ORIGIN}/search/cards", params=params)
        human_delay(4.2, 6.5)
        try:
            search_cards_dict = search_cards.json()
        except Exception as e:
            print(e)
            print("Error during turning a card search page into a dict")
            return
        content = search_cards_dict.get("content", "")
        count = search_cards_dict.get("count", 0)
        all_search_cards_list.append(content)
        total_cards += count

        if count < limit:
            break

        offset += limit

    all_search_cards_html: str = "".join(all_search_cards_list)


    # Selecting all cards with that card id
    soup = BeautifulSoup(all_search_cards_html, "html.parser")
    wrappers = soup.select(f".manga-cards__item-wrapper:has(.manga-cards__item[data-card-id='{card_id}'])")
    
    if len(wrappers) == 0:
        print(f"No cards by the name '{card_name}' were found")
        return

    card_divs = [str(div) for div in wrappers]

    
    # Get the needed info about each of the cards
    card_dicts_list = []
    for card_div in card_divs:
        soup = BeautifulSoup(card_div, "html.parser")

        wrapper = soup.find("div", class_="manga-cards__item-wrapper")
        item = soup.find("div", class_="manga-cards__item")


        if wrapper and item:
            card_rank = wrapper.get("data-rank")
            card_copy_number = item.get("data-copy-number")
            card_manga_name = item.get("data-manga-name")
            card_image = item.select_one("div.manga-cards__image").get("data-src")
            card_action_id = item.select_one("div.card-actions").get("data-card-user-id")

            if card_copy_number and str(card_copy_number).isdigit():
                card_dicts_list.append({
                    "rank": card_rank,
                    "copy_number": int(str(card_copy_number)),
                    "manga_name": card_manga_name,
                    "card_image": card_image,
                    "action_id": int(card_action_id),
                })
        else:
            print("Error during getting information about each searched cards with the same id")
            return


    # Getting the latest one of them by the copy number
    latest_copy_number = -1
    latest_card_info = {}
    for card_dict in card_dicts_list:
        if card_dict["copy_number"] > latest_copy_number:
            latest_copy_number = card_dict["copy_number"]
            latest_card_info = card_dict

    return latest_card_info


def get_wishlist_page_count(sess: requests.Session, card_id: int) -> int:
    card_wishlist_page = sess.get(url=f"{info.ORIGIN}/cards/{card_id}/offers/want")

    soup = BeautifulSoup(card_wishlist_page.text, "html.parser")
    pagination_links = soup.select("ul.pagination li.pagination__button a")

    if not pagination_links:
        return 1

    page_numbers = [int(a.text.strip()) for a in pagination_links if a.text.strip().isdigit()]
    
    return max(page_numbers) if page_numbers else 1


# for reading chapters
def manage_responses(sess: requests.Session, response: requests.Response, chapter_link: str):
    try:
        response_dict = response.json()
    except (json.JSONDecodeError, ValueError):
        print("Response was not JSON")
        return False

    # CARD
    if response_dict.get("id") and response_dict.get("name") and response_dict.get("image"):
        card_info = {
            "card_name": response_dict["name"],
            "card_id": response_dict["id"],
            # "card_image": response_dict["image"],
            "wishlist_page_count": get_wishlist_page_count(sess=sess, card_id=response_dict["id"])
        }
        human_delay()
        additional_info = get_card_info(sess=sess, card_id=card_info["card_id"], card_name=card_info["card_name"])
        if additional_info:
            card_info.update(additional_info)
            postgresql_response = postgresql.add_card(**card_info)
            print(f"{card_info['card_name']} - Read Chapters Card to cards_queue", end=' ')
            print("Successful" if postgresql_response else "Failed")
        else:
            print("Error with getting additional_info for chapter reading response")
        return "card"

    # SCROLL
    elif response_dict.get("scroll") is True:
        # scroll_rank: str = response_dict["rank"]
        # is_scroll_blessed: bool = bool(response_dict["is_blessed"])
        return "scroll"

    # CANDY
    elif response_dict.get("type") == "candy":
        token = response_dict["token"]
        candy_response = sess.post(
            url=f"{info.ORIGIN}/halloween/takeCandy?r=822",
            data={
                "token": token,
            },
            headers=ajax_headers(referer_url=chapter_link)
        )
        human_delay(65.3, 72.3)
        if candy_response.status_code != 200:
            print("Failed to get a candy")
        else:
            print("Successfully got a candy")
        return "candy"


# for calendar card
def manage_calendar_card(sess: requests.Session, response: str):
    human_delay(15.12, 20.3)
    card_info = get_card_notification(sess=sess)
    human_delay(8.4, 15.3)
    if card_info:
        card_info["wishlist_page_count"] = get_wishlist_page_count(sess=sess, card_id=card_info["card_id"])
        additional_info = get_card_info(sess=sess, card_name=card_info["card_name"], card_id=card_info["card_id"])
        human_delay(8.4, 15.3)
        if additional_info:
            card_info.update(additional_info)
            postgresql_response = postgresql.add_card(**card_info)
            print(f"{card_info['card_name']} - Calendar Card to cards_queue", end=' ')
            print("Successful" if postgresql_response else "Failed")
        else:
            print("Error with getting additional_info for a calendar")
            return


def get_login_reward(sess: requests.Session) -> int:
    print("Checking login reward")
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)
    human_delay(10.3, 15.2)
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)
    human_delay()
    
    soup = BeautifulSoup(transactions_page.text, "html.parser")
    reward = int(soup.select_one("div.user-transactions__amount.user-transactions__amount--plus").text.replace('+', ''))
    print(f"Checked login reward +{reward}")
    return reward


def get_auth_session() -> requests.Session | None:
    print("Logging In")
    sess = requests.Session()

    # proxy
    sess.proxies.update({
        "http": info.PROXY_URL,
        "https": info.PROXY_URL
    })

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    # BASE headers
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    })

    # fetching the csrp token
    try:
        login_page = sess.get(
            url=info.LOGIN_URL,
            headers={
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        # print(f"[AUTH DEBUG] Login Page Status Code: {login_page.status_code}")
        # print(f"[AUTH DEBUG] Login Page Preview:\n{login_page.text[:400]}")
    except Exception as e:
        print(f"[AUTH ERROR] Exception fetching login page: {e}")
        return None

    human_delay()
    soup = BeautifulSoup(login_page.text, "html.parser")

    csrf_token = (
        soup.find("input", {"name": "_token"}) or
        soup.find("input", {"name": "csrf_token"}) or
        soup.find("meta", {"name": "csrf-token"})
    )

    # handling None
    if csrf_token is None:
        # raise ValueError("Could not find CSRF token on the login page.")
        print("Could not find CSRF token on the login page.")
        return

    token_value = csrf_token.get("value") or csrf_token.get("content")

    if not token_value:
        # raise ValueError("CSRF token tag was found, but value/content is empty.")
        print("CSRF token tag was found, but value/content is empty.")
        return

    token_value: str = str(token_value)

    # all post request will contain that token by default
    sess.headers.update({"X-CSRF-TOKEN": token_value})

    try:
        response = sess.post(
            url=info.LOGIN_URL,
            data={
                "_token": token_value,
                "email": info.EMAIL,
                "password": info.PASSWORD,
            },
            headers=ajax_headers(referer_url=info.LOGIN_URL, origin_url=info.ORIGIN, content_type="application/x-www-form-urlencoded"),
        )
    except Exception as e:
        print(e)
        print("Error with the authentication request")
        return

    if response.status_code != 200:
        # raise PermissionError(f"Login failed with status {response.status_code}")
        print(f"Login failed with status {response.status_code}")
        return

    print("Logged In")
    return sess


def lock_card(action_id):
    import scheduling
    sess = scheduling.get_session()
    if sess is None:
        sess = get_auth_session()
    user_id = get_user_id(sess=sess)
    lock_response = sess.post(
        url=f"{info.ORIGIN}/trades/lockCard/{action_id}",
        headers=ajax_headers(referer_url=f"{info.ORIGIN}/users/{user_id}/cards")
    )
    if lock_response.json().get("is_lock"):
        return True
    return False


def unwant_card(card_id):
    import scheduling
    sess = scheduling.get_session()
    if sess is None:
        sess = get_auth_session()
    user_id = get_user_id(sess=sess)
    unwant_response = sess.post(
        url=f"{info.ORIGIN}/cards/offers",
        data={
            "card_id": card_id,
            "type": 1
        },
        headers=ajax_headers(referer_url=f"{info.ORIGIN}/users/{user_id}/cards")
    )
    if unwant_response.json().get("is_created"):
        return True
    return False


def add_to_trade_deck(action_id):
    import scheduling
    sess = scheduling.get_session()
    if sess is None:
        sess = get_auth_session()
    user_id = get_user_id(sess=sess)
    add_to_trade_deck_response = sess.post(
        url=f"{info.ORIGIN}/decks/{info.TRADE_DECK_ID}/addCard",
        data={
            "cardId": action_id
        },
        headers=ajax_headers(referer_url=f"{info.ORIGIN}/users/{user_id}/cards")
    )
    if add_to_trade_deck_response.json().get("is_added"):
        return True
    return False


def manage_cards_queue():
    if postgresql.is_active_card():
        print("There is an active card already")
        return None
    pending_card = postgresql.get_pending_card_info()
    if pending_card is None: # meaning no pending cards left
        print("No pending cards left")
        return None
    postgresql_response = postgresql.set_card_state(state="active", id=pending_card["id"])
    if not postgresql_response:
        print("ERROR during setting a card active")
        return
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(bot.send_card_message(pending_card), loop)
        # bot.send_card_message(card_info_dict=pending_card)
    except RuntimeError:
        bot.send_card_message(pending_card)


def claim_calendar_gift(sess: requests.Session) -> str | None:
    print("Claiming calendar gift")
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)

    soup = BeautifulSoup(transactions_page.text, "html.parser")
    active_card = soup.select_one(".daily-rewards-item:has(.daily-rewards-item-exp--active)")

    reward = "Unknown"
    if active_card:
        image_div = active_card.select_one(".daily-rewards-item-image")
        if image_div is None:
            return
        for div_class in image_div.get("class", []):
            if "daily-rewards-item-image--" in div_class:
                reward = div_class.split("daily-rewards-item-image--")[-1]
                break

        day = active_card["data-day"]
        human_delay()
        calendar_response = sess.post(url=f"{info.TRANSACTIONS_URL}/claim/{day}", headers=ajax_headers(referer_url=info.TRANSACTIONS_URL))
        # print(f"TEST Calendar Response: {calendar_response.text}")
        calendar_response_dict = calendar_response.json()
        if calendar_response_dict.get("message") == "Вы успешно забрали награду, приходите завтра":
            print(reward)
            print("Claimed calendar gift")
            if "Card_" in reward:
                manage_calendar_card(sess=sess, response=reward)
            return reward # Coins | Scroll_g | Card_g
        elif calendar_response_dict.get("message") == "Вы уже получали награду сегодня, приходите завтра":
            print("Already Claimed")
            return "Already Claimed"
        else:
            print("")
        return


def watch_ads(sess: requests.Session) -> dict | None:  # 3 times
    print("Watching ADs")
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)
    soup = BeautifulSoup(transactions_page.text, "html.parser")
    ads_button_div = soup.select_one(".wallet-panel__action--ads")
    if ads_button_div is None:
        print("Didn't find the ads button div")
        return
    # total_ads_count = int(str(ads_button_div["data-count"]))
    
    span = ads_button_div.find("span")
    if span is None:
        print("Didn't find the span with text")
        return
    span_content: str = span.text
    try:
        # separating number of available watches and diampnds
        count_by_diamonds = span_content.split(' ')[-1]
        temp_list = count_by_diamonds.split('x')
    except Exception as e:
        print(e)
        print("Error in split() during watching ads")
        return
    # if int(temp_list[0]) == total_ads_count:
    #     diamonds_per_ad = int(temp_list[1])
    # else:
    #     diamonds_per_ad = int(temp_list[0])

    # temporarily by the text on button, for some reason data-count is 0 for 2 days in a row, maybe it's too early & it didn't restart
    total_ads_count = int(temp_list[0])
    diamonds_per_ad = int(temp_list[1])

    # print(f"data-count = {int(str(ads_button_div["data-count"]))}")
    # print(f"total_ads_count = {total_ads_count}")
    # print(f"3by7 1 = {temp_list[0]}")
    # print(f"3by7 1 type = {type(temp_list[0])}")
    # print(f"3by7 2 = {temp_list[1]}")
    # print(f"3by7 2 type = {type(temp_list[1])}")
    # print(f"diamonds per ad = {diamonds_per_ad}")

    gained_diamonds = 0
    successful_watches = 0
    got_scroll = False
    for i in range(total_ads_count):
        human_delay(42.34, 56.08)
        ads_response = sess.post(url=f"{info.TRANSACTIONS_URL}/ads", headers=ajax_headers(referer_url=info.TRANSACTIONS_URL))
        # print(f"TEST ADs Response: {ads_response.text}")

        ads_response_dict = ads_response.json()
        if ads_response_dict.get("success"):
            successful_watches += 1
            gained_diamonds += diamonds_per_ad
            print(f"Watched AD number {i + 1} / {total_ads_count}")
        elif not ads_response_dict.get("success"):
            print("Already Watched Today")
            break

    # MAKE A DYNAMIC CHECKING from notifications
    if successful_watches == total_ads_count:
        got_scroll = True

    return {
        "total_ads_count": total_ads_count,
        "diamonds_per_ad": diamonds_per_ad,
        "successful_watches": successful_watches,
        "gained_diamonds": gained_diamonds,
        "got_scroll": got_scroll,
    }


def mine(sess: requests.Session) -> dict | None:
    print("Mining")
    mine_page = sess.get(url=info.MINE_URL)
    human_delay()
    soup = BeautifulSoup(mine_page.text, "html.parser")
    hits_tag = soup.find("span", class_="main-mine__game-hits-left")
    if not hits_tag:
        return

    max_hits = int(soup.select_one(".main-mine__game-panel")["data-max-hit"])
    ores_before = int(soup.select_one("span.main-mine__header_score-count.js-score").get_text().replace(' ', ''))

    hits_left = int(hits_tag.text.strip())
    if hits_left <= 0:
        # message: "Лимит ударов на сегодня исчерпан"
        print("No hits available.")
        return {
            "ores_before": ores_before,
            "ores_after": ores_before,
            "ores_made": 0,
            "max_hits": max_hits,
            "hits_made": 0 
        }


    ores_after = 0
    hits_made = 0

    for i in range(hits_left):
        mine_response = sess.post(url=f"{info.MINE_URL}/hit", headers=ajax_headers(referer_url=info.MINE_URL))
        # print(f"TEST Mine Response: {mine_response.text}")
        print(f"Mine Hit Number {i + 1} / {hits_left}")

        mine_response_dict = mine_response.json()

        hits_made += 1
        ores_after = mine_response_dict.get("ore")

        if mine_response_dict.get("hits_left") == 0:
            print("No hits left, stopping")
            break

        human_delay(0.8, 1.2)
    human_delay()

    ores_made = ores_after - ores_before

    # converting ores to diamonds
    sess.post(
        url=f"{info.MINE_URL}/exchange",
        data={
            "diamonds": ores_after // 100
        },
        headers=ajax_headers(referer_url=info.MINE_URL, content_type="application/x-www-form-urlencoded")
    )

    print(f"Ores made today: {ores_made}")

    return {
        "ores_before": ores_before,
        "ores_after": ores_after,
        "ores_made": ores_made,
        "max_hits": max_hits,
        "hits_made": hits_made
    }

def leave_comments(sess: requests.Session) -> dict | None:
    print("Leaving Comments")
    # checking number of comments left
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)
    human_delay()
    soup = BeautifulSoup(transactions_page.text, "html.parser")

    comment_span = soup.find("span", string=re.compile(r"Комментарии"))
    if comment_span is None:
        return
    b_tag = comment_span.find_next_sibling("b")
    if b_tag is None:
        return
    # separating 4/10 by slash
    current_str, total_str = b_tag.text.strip().split("/")
    comments_left = int(total_str) - int(current_str)

    total_diamonds = 0
    total_candies = 0
    successful_comments = 0

    words_list = ["New", "Else", "Good", "Bad", "Nice", "Cool", "Great", "Fresh", "Solid"]
    for i in range(comments_left):
        comments_response = sess.post(
            url=f"{info.ORIGIN}/comments",
            data={
                "text": f"Something {random.choice(words_list)}",
                "commentable_id": "563640",
                "commentable_type": "Deck",
                "parent_id": "",
                "gif_image": "",
                "sticker_id": "",
                "is_trade": "0",
                "is_raffle": "0",
            },
            headers=ajax_headers(referer_url=info.DECK_URL)
        )
        # print(f"TEST Comments Response: {comments_response.text}")

        print(f"Left comment number {i + 1} / {comments_left}")

        response_dict = comments_response.json()
        reward_dict = response_dict.get("reward")
        diamonds = reward_dict.get("diamonds", 0)
        candies = reward_dict.get("candies", 0)

        total_diamonds += diamonds
        total_candies += candies

        if diamonds != 0:
            successful_comments += 1

        if (i != comments_left - 1):
            human_delay(32.38, 62.06)
        else:
            human_delay()

    if comments_left <= 0:
        print("No comments available today")
    return {
        "total_diamonds": total_diamonds,
        "total_candies": total_candies,
        "comments_left": comments_left,
        "total_comments": int(total_str),
        "successful_comments": successful_comments
    }


def read_chapters(sess: requests.Session, any_candies: bool = False):
    print("Reading chapters")

    chapters_read = 0
    successful_reads = 0
    got_scroll = False

    candies_left = True
    cards_left = True

    while True:
        if any_candies:
            available_candies = True
            event_page = sess.get(url=f"{info.ORIGIN}/event/pack")
            human_delay()
            event_soup = BeautifulSoup(event_page.text, "html.parser")
            encountered_today = int(event_soup.select_one("div.event-page__stat-value:not(.js-event-balance)").text)
            if encountered_today >= 35:
                available_candies = False
        else:
            available_candies = False

        available_cards = True
        transactions_page = sess.get(url=info.TRANSACTIONS_URL)
        human_delay()
        soup = BeautifulSoup(transactions_page.text, "html.parser")
        if soup.select_one(".wallet-panel__drop-state.wallet-panel__drop-state--wait"):
            print("Card (& scroll) Reloading")
            available_cards = False
        text_div = soup.select_one(".wallet-panel__drop-text")
        text = text_div.text
        number_read, number_total = [int(n) for n in re.findall(r'\d+', text)]
        if number_read >= number_total:
            print("Collected all cards today")
            available_cards = False
            if not available_candies:
                return {"done": True}

        if any_candies and (not available_candies) and (not available_cards):
            break
        elif (not available_candies) and (not available_cards) and got_scroll:
            break
        elif (not available_candies) and (not available_cards) and (chapters_read >= 5):
            break

        index = postgresql.get_index()
        link = postgresql.get_chapter_link(index + chapters_read)
        current_chapter_page = sess.get(url=link)
        # print(f"LINK {link} STATUS CODE {current_chapter_page.status_code}")
        human_delay(4.3, 8.6)
        if current_chapter_page.status_code == 404:
            print(f"NOT FOUND: {link}")
            chapters_read += 1
            postgresql.set_index(chapters_read=1)
            continue
        current_chapter_json = re.search(r'window\.current_chapter\s*=\s*(\{.*?\});', current_chapter_page.text)
        if current_chapter_json is None:
            print(f"None: {link}")
            chapters_read += 1
            postgresql.set_index(chapters_read=1)
            continue

        chapter_data = json.loads(current_chapter_json.group(1))
        manga_id = str(chapter_data["id"])
        chapter_id = str(chapter_data["chapter_id"])

        reading_response = sess.post(
            url=f"{info.ORIGIN}/addHistory?r=702",
            data={
                "items[0][manga_id]": manga_id,
                "items[0][chapter_id]": chapter_id,
            },
            headers=ajax_headers(referer_url=link)
        )
        # print(f"TEST Reading Response: {reading_response.text}")
        chapters_read += 1
        successful_reads += 1
        manage_result = manage_responses(sess=sess, response=reading_response, chapter_link=link)
        if manage_result is False:
            print(f"No reward in chapter {successful_reads}")
        else:
            print(f"Read chapter with reward {successful_reads}")
            if manage_result == "scroll":
                got_scroll = True
                
        postgresql.set_index(chapters_read=1)
        human_delay(270.2, 330.43)

    print(f"Total chapters read+skipped: {chapters_read}")

    manage_cards_queue()

    return {
        "done": False,
    }


# def claim_chat_diamond(sess: requests.Session):
#     print("Claiming chat diamond")
#
#     chat_page = sess.get(url=f"{info.ORIGIN}/chat")
#     soup = BeautifulSoup(chat_page.text, "html.parser")
#     reload_div = soup.select_one(".chat-arena__coin-progress")
#     if reload_div is None:
#         return
#     match = re.search(r"height:\s*([\d.]+%?)", str(reload_div["style"]))
#     if match:
#         height_val = match.group(1)  # Output: '100%'
#         print(height_val)
#         print(type(height_val))
#
#     sio = socketio.Client(http_session=sess, logger=True, engineio_logger=True)
#
#     @sio.on("connect")
#     def on_connect():
#         print("[Socket.IO] Successfully connected!")
#
#     @sio.on("connect_error")
#     def on_connect_error(data):
#         print(f"[Socket.IO] Connection error details: {data}")
#
#     try:
#         sio.connect(
#             url=info.ORIGIN,
#             headers=ajax_headers(referer_url=f"{info.ORIGIN}/chat", origin_url=info.ORIGIN),
#             transports=["polling"],
#             socketio_path="socket.io",
#             wait_timeout=10
#         )
#         sio.emit('addCoins')
#         sio.sleep(2)
#     except Exception as e:
#         print(e)
#         print("Error during claiming a chat diamond")
#     finally:
#         if sio.connected:
#             sio.disconnect()


if __name__ == "__main__":
    sess = get_auth_session()
    if sess:
        human_delay()
        # claim_calendar_gift(sess)
        # human_delay()
        # watch_ads(sess)
        # human_delay()
        # mine(sess)
        # human_delay()
        # leave_comments(sess)
        # human_delay()
        # read_chapters(sess) # don't forget about candies
        # manage_cards_queue()
        
