from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, chat
from aiogram.enums import ParseMode
import info
import asyncio

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
        
        if ads_results["successful_watches"] == ads_results["total_ads_count"]:
            ads_text = "✔️"
        else:
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
        if comments_results["successful_comments"] == comments_results["total_comments"]:
            comments_text = "✔️"
        else:
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
                        [{"text": "Login"}, {"text": "✔️"}],
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

if __name__ == "__main__":
    asyncio.run(main())

