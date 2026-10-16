from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, chat, response_parameters, rich_message
from aiogram.enums import ParseMode
import info
import postgresql
import asyncio
import requests
import html

bot = Bot(token=info.TG_BOT_TOKEN)


async def main_job_message(calendar_results, ads_results, mine_results, comments_results, login_results):
    # total
    total_gained_diamonds = login_results
    total_gained_candies = 0
    
    # Calendar
    if calendar_results is None:
        calendar_text = "None"
    elif calendar_results == "Coins":
        calendar_text = "✔️ Diamonds"
        total_gained_diamonds += 50
    elif "Card" in calendar_results:
        calendar_text = "✔️ Card"
    elif "Scroll" in calendar_results:
        calendar_text = "✔️ Scroll"
    else:
        calendar_text = calendar_results

    # ADs
    ads_text = "None" 
    if ads_results is not None:
        any_candies = False
        if comments_results and comments_results.get("total_candies", 0) > 0:
            any_candies = True
        
        ads_text = f"✔️ {ads_results['successful_watches']}/{ads_results['total_ads_count']}"

        total_gained_diamonds += ads_results["gained_diamonds"]
        if any_candies:
            total_gained_candies += ads_results["successful_watches"] * 2

    # Mine
    mine_text = "None"
    if mine_results is not None:
        mine_text = f"✔️ {mine_results['hits_made']}/{mine_results['max_hits']}"
        total_gained_diamonds += mine_results["ores_after"] // 100

    # Comments
    comments_text = "None"
    if comments_results is not None:
        comments_text = f"✔️ {comments_results['successful_comments']}/{comments_results['comments_left']}/{comments_results['total_comments']}"
        total_gained_diamonds += comments_results["total_diamonds"]
        total_gained_candies += comments_results["total_candies"]

    # text = (
    #     "<b>MAIN DAILY JOB</b>\n\n"
    #     "<b>Login</b>\n"
    #     "└ +20?\n\n"
    #     "<b>Calendar</b>\n"
    #     f"└ {calendar_text}\n\n"
    #     "<b>ADs</b>\n"
    #     f"└ {ads_text}\n\n"
    #     "<b>Mine</b>\n"
    #     f"└ {mine_text}\n\n"
    #     "<b>Comments</b>\n"
    #     f"└ {comments_text}"
    # )
    # await bot.send_message(chat_id=info.ADMIN_TG_USER, text=text, parse_mode=ParseMode.HTML)

    payload = {
        "chat_id": info.ADMIN_TG_USER,
        "rich_message": {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "MAIN DAILY JOB:"
                },
                {
                    "type": "table",
                    "is_bordered": True,
                    # "has_header": True,
                    # "is_striped": True,
                    "cells": [
                        # # Row 1: Header cells
                        # [
                        #     {"text": "JOB", "entities": [{"type": "italic", "offset": 0, "length": 3}]},
                        #     {"text": "RESULT", "entities": [{"type": "italic", "offset": 0, "length": 6}]}
                        # ],
                        # Rows 2+: Data cells
                        [{"text": "Login"}, {"text": f"✔️ +{login_results}"}],
                        [{"text": "Calendar"}, {"text": calendar_text}],
                        [{"text": "ADs"}, {"text": ads_text}],
                        [{"text": "Mine"}, {"text": mine_text}],
                        [{"text": "Comments"}, {"text": comments_text}],
                    ]
                },
                {
                    "type": "paragraph",
                    "text": "TOTAL REWARDS:"
                },
                {
                    "type": "table",
                    "is_bordered": True,
                    # "has_header": True,
                    # "is_striped": True,
                    "cells": [
                        # Row 1: Header cells
                        # [
                        #     {"text": "REWARD", "entities": [{"type": "italic", "offset": 0, "length": 6}]},
                        #     {"text": "AMOUNT", "entities": [{"type": "italic", "offset": 0, "length": 6}]}
                        # ],
                        # Rows 2+: Data cells
                        [{"text": "Diamonds"}, {"text": str(total_gained_diamonds)}],
                        [{"text": "Candies"}, {"text": str(total_gained_candies)}],
                    ]
                }
            ]
        }
    }
    url = f"https://api.telegram.org/bot{info.TG_BOT_TOKEN}/sendRichMessage"
    main_job_response = requests.post(url=url, json=payload)


# def send_card_message(card_info_dict):
#     print(f"{info.ORIGIN}{card_info_dict['image']}")
#     payload = {
#         "chat_id": info.ADMIN_TG_USER,
#         "rich_message": {
#             "blocks": [
#                 {
#                     "type": "image",
#                     "url": f"{info.ORIGIN}{card_info_dict['image']}"
#                 },
#                 {
#                     "type": "table",
#                     "is_bordered": True,
#                     # "has_header": True,
#                     "is_striped": True,
#                     "cells": [
#                         [{"text": "Name"}, {"text": card_info_dict["name"]}],
#                         [{"text": "Rank"}, {"text": card_info_dict["rank"]}],
#                         [{"text": "Copy Number"}, {"text": str(card_info_dict["copy_number"])}],
#                         [{"text": "Wishlist Pages"}, {"text": str(card_info_dict["wishlist_page_count"])}],
#                         [{"text": "Manga Name"}, {"text": card_info_dict["manga_name"]}],
#                     ]
#                 }
#             ]
#         },
#         "reply_markup": {
#             "inline_keyboard": [
#                 [
#                     {"text": "Lock", "callback_data": f"card_action:lock:{card_info_dict['action_id']}:{card_info_dict['id']}"},
#                     {"text": "Unwant", "callback_data": f"card_action:unwant:{card_info_dict['card_id']}:{card_info_dict['id']}"},
#                 ]
#             ]
#         }
#     }
#
#     url = f"https://api.telegram.org/bot{info.TG_BOT_TOKEN}/sendRichMessage"
#     card_message_response = requests.post(url=url, json=payload)
#     print(card_message_response.text)

def send_card_message(card_info_dict) -> bool:
    image_url = f"{info.ORIGIN}{card_info_dict["image"]}"

    caption = (
        f"<b>Name:</b> {html.escape(card_info_dict['name'])}\n"
        f"<b>Rank:</b> {html.escape(card_info_dict['rank'])}\n"
        f"<b>Copy Number:</b> {card_info_dict['copy_number']}\n"
        f"<b>Wishlist Pages:</b> {card_info_dict['wishlist_page_count']}\n"
        f"<b>Manga:</b> {html.escape(card_info_dict['manga_name'])}"
    )

    payload = {
        "chat_id": info.ADMIN_TG_USER,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "Lock (personal)", "callback_data": f"card_action:lock:{card_info_dict['action_id']}:{card_info_dict['id']}"},
                    {"text": "Unwant (useless)", "callback_data": f"card_action:unwant:{card_info_dict['card_id']}:{card_info_dict['id']}"},
                ],
                [
                    {"text": "Nothing (will sell)", "callback_data": f"card_action:nothing:0:{card_info_dict['id']}"},
                    {"text": "Trade Deck (expensive)", "callback_data": f"card_action:trade_deck:{card_info_dict['action_id']}:{card_info_dict['id']}"},
                ]
            ]
        },
    }

    url = f"https://api.telegram.org/bot{info.TG_BOT_TOKEN}/sendPhoto"
    response = requests.post(url=url, json=payload, timeout=30)
    if not response.ok:
        print("sendPhoto failed:", response.status_code, response.text)
        return False
    return True


dp = Dispatcher()
@dp.callback_query(F.data.startswith("card_action:"))
async def handle_card_action_callback(callback: CallbackQuery):
    await callback.answer()
    _, action, id_str, db_id_str = callback.data.split(":")
    general_id = int(id_str)
    db_id = int(db_id_str)
    await process_card_action(action=action, general_id=general_id, db_id=db_id, callback=callback)


async def process_card_action(action: str, general_id: int, db_id: int, callback: CallbackQuery):
    import main
    if action == "nothing":
        success = True
    else:
        action_functions = {
            "lock": main.lock_card,
            "unwant": main.unwant_card,
            "trade_deck": main.add_to_trade_deck,
        }
        success = await asyncio.to_thread(action_functions[action], general_id)

        if not success:
            success = await asyncio.to_thread(action_functions[action], general_id)

    if success:
        await callback.message.delete()
        await asyncio.to_thread(postgresql.set_card_state, state="done", id=db_id)
        await asyncio.to_thread(main.manage_cards_queue)
    else:
        await callback.answer(text="Failed to process card", show_alert=True)


def error_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{info.TG_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url=url,
        json={
            "chat_id": info.ADMIN_TG_USER,
            "text": text[:4000],  # Telegram limit is 4096 characters
        },
        timeout=30,
    )

    if not response.ok:
        print("sendMessage failed:", response.status_code, response.text)
        return False
    return True


# testing
async def main():
    payload = {
        "chat_id": info.ADMIN_TG_USER,
        "rich_message": {
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "🎉 Результаты розыгрыша:\nПобедители:"
                },
                {
                    "type": "table",
                    "is_bordered": True,
                    "has_header": True,
                    "is_striped": True,
                    "cells": [
                        # Row 1: Header cells
                        [{"text": "Место"}, {"text": "Имя"}, {"text": "Юзернейм"}, {"text": "Telegram ID"}],
                        # Rows 2+: Data cells
                        [{"text": "1"}, {"text": "hotline misato"}, {"text": "@hotline_misato"}, {"text": "391026364"}],
                        [{"text": "2"}, {"text": "Arts"}, {"text": "@ArtsWm"}, {"text": "5416518097"}],
                        [{"text": "3"}, {"text": "Люба"}, {"text": "@maguba1"}, {"text": "544331455"}]
                    ]
                }
            ]
        }
    }

    url = f"https://api.telegram.org/bot{info.TG_BOT_TOKEN}/sendRichMessage"

    response = requests.post(url, json=payload)

    print("Status Code:", response.status_code)
    print("Response:", response.json())

if __name__ == "__main__":
    asyncio.run(main())

