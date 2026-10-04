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

            if card_copy_number and str(card_copy_number).isdigit():
                card_dicts_list.append({
                    "rank": card_rank,
                    "copy_number": int(str(card_copy_number)),
                    "manga_name": card_manga_name,
                    "card_image": card_image
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
def manage_responses(sess: requests.Session, response: requests.Response):
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
            print("Error with getting additional_info")
            return
    # SCROLL
    # elif response_dict.get("scroll") is True:
    #     scroll_rank: str = response_dict["rank"]
    #     is_scroll_blessed: bool = bool(response_dict["is_blessed"])
    return True


# for calendar card
def manage_calendar_card(sess: requests.Session, response: str):
    human_delay(15.12, 20.3)
    card_info = get_card_notification(sess=sess)
    human_delay(8.4, 15.3)
    if card_info:
        additional_info = get_card_info(sess=sess, card_name=card_info["card_name"], card_id=card_info["card_id"])
        human_delay(8.4, 15.3)
        card_info.update(additional_info) if additional_info else print("Error with getting additional_info for a calendar")
        card_info["wishlist_page_count"] = get_wishlist_page_count(sess=sess, card_id=card_info["card_id"])

        postgresql_response = postgresql.add_card(**card_info)
        print(f"{card_info['card_name']} - Calendar Card to cards_queue", end=' ')
        print("Successful" if postgresql_response else "Failed")


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
        print(f"[AUTH DEBUG] Login Page Status Code: {login_page.status_code}")
        print(f"[AUTH DEBUG] Login Page Preview:\n{login_page.text[:400]}")
    except Exception as e:
        print(f"[AUTH DEBUG] Exception fetching login page: {e}")
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
        calendar_response_dict = calendar_response.json()
        if calendar_response_dict.get("message") == "Вы успешно забрали награду, приходите завтра":
            print(reward)
            print("Claimed calendar gift")
            if "Card_" in reward:
                manage_calendar_card(sess=sess, response=reward)
            return reward # coins | scroll_g | card_g
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
    successfull_watches = 0
    got_scroll = False
    for i in range(total_ads_count):
        human_delay(42.34, 56.08)
        ads_response = sess.post(url=f"{info.TRANSACTIONS_URL}/ads", headers=ajax_headers(referer_url=info.TRANSACTIONS_URL))

        ads_response_dict = ads_response.json()
        if ads_response_dict.get("success"):
            successfull_watches += 1
            gained_diamonds += diamonds_per_ad
            print(f"Watched AD number {i + 1} / {total_ads_count}")
        elif not ads_response_dict.get("success"):
            print("Already Watched Today")
            break

    # MAKE A DYNAMIC CHECKING from notifications
    if successfull_watches == total_ads_count:
        got_scroll = True

    return {
        "total_ads_count": total_ads_count,
        "diamonds_per_ad": diamonds_per_ad,
        "successfull_watches": successfull_watches,
        "gained_diamonds": gained_diamonds,
        "got_scroll": got_scroll
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
    # sess.post(
    #     url=f"{info.MINE_URL}/exchange",
    #     data={
    #         "diamonds": ores_after // 100
    #     },
    #     headers=ajax_headers(referer_url=info.MINE_URL, content_type="application/x-www-form-urlencoded")
    # )

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


def read_chapters(sess: requests.Session):
    print("Reading chapters")
    transactions_page = sess.get(url=info.TRANSACTIONS_URL)
    soup = BeautifulSoup(transactions_page.text, "html.parser")

    if soup.select_one(".wallet-panel__drop-state.wallet-panel__drop-state--wait"):
        print("Reloading")
        return

    text_div = soup.select_one(".wallet-panel__drop-text")
    text = text_div.text
    number_read, number_total = [int(n) for n in re.findall(r'\d+', text)]
    if number_read >= number_total:
        print("Done for today")
        return

    index = postgresql.get_index()
    links = postgresql.get_chapter_links(index)
    chapters_read = 0

    for link in links:
        current_chapter_page = sess.get(url=link)
        human_delay()
        current_chapter_json = re.search(r'window\.current_chapter\s*=\s*(\{.*?\});', current_chapter_page.text)
        if current_chapter_json is None:
            return

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

        print(f"Read chapter {links.index(link) + 1} / {len(links)}")
        if link != links[-1]:
            human_delay(150.3, 202.43) # not working sometimes, just checking if caused by waiting time
        else:
            human_delay()

        manage_result = manage_responses(sess=sess, response=reading_response)
        if manage_result is False:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(bot.error_message(text=f"No reward in chapter {links.index(link) + 1} / {len(links)}"))
            except RuntimeError as e:
                asyncio.run(bot.error_message(text=str(e)))
        
        chapters_read += 1

    if chapters_read != 0:
        postgresql.set_index(chapters_read=chapters_read)


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
        print(mine(sess))
        # human_delay()
        # leave_comments(sess)
        # human_delay()
        # read_chapters(sess) # don't forget about candies
        
