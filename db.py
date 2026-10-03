import linecache

total_chapters_to_read = 2


def get_index():
    with open("index.txt", 'r') as file:
        index = int(file.read())
    return index


def set_index():
    current_index = get_index()
    with open("index.txt", 'w') as file:
        file.write(str(current_index + total_chapters_to_read))


def get_links(index):
    links = []
    for i in range(total_chapters_to_read):
        links.append(linecache.getline("chapters.txt", index + i).strip())
    return links


def write_response(response_text: str):
    with open("response_log.txt", 'a', encoding="utf-8") as file:
        file.write('\n')
        file.write(response_text)


""" добавить в 'не нужно'
https://mangabuff.ru/cards/offers
"card_id": "193059"
"type": "1"
type 0 это список желаемого, 1 - не нужного
to undo just send the same request again


cards ulocked for trade
https://mangabuff.ru/users/995688/cards?lock=0

https://mangabuff.ru/search/cards?user_id=995688&q=Пистолет
https://mangabuff.ru/search/cards?user_id=995688&offset=160&q=genshin
https://mangabuff.ru/search/cards?user_id=239203&offset=320&q=Genshin


print(text.encode('utf-8').decode('unicode-escape'))
"""


"""
        # db.write_response(f"{response.headers.get("Date")} {response_dict['name']} LINK:{info.ORIGIN}/cards/{response_dict['id']}/users WISHLIST:{card_info["wishlist_page_count"]}")
        # db.write_response(str(card_info))
    # SCROLL
    elif response_dict.get("scroll") is True:
        scroll_rank: str = response_dict["rank"]
        is_scroll_blessed: bool = bool(response_dict["is_blessed"])
        # db.write_response(f"{response.headers.get("Date")} Sroll {scroll_rank} {'Blessed' if is_scroll_blessed else 'Not Blessed'}")


"""
