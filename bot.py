from aiogram import Bot
from aiogram.filters import Command
from aiogram.types import Message, chat
from aiogram.enums import ParseMode
import info
import asyncio

bot = Bot(token=info.TG_BOT_TOKEN)


async def main_job_message(calendar_results, ads_results, mine_results, comments_results):
    # Calendar
    calendar_text = "None"
    if calendar_results == "Coins":
        calendar_text = "+50"
    elif calendar_results and '_' in calendar_results:
        calendar_text = calendar_results.replace('_', ' ').title()

    # ADs
    ads_text = "None" 
    if ads_results is not None:
        any_candies = False
        if comments_results and comments_results.get("total_candies", 0) > 0:
            any_candies = True
        ads_text = f"{ads_results['successfull_watches']}/{ads_results['total_ads_count']} +{ads_results['gained_diamonds']} 🍬{(ads_results['successfull_watches'] * 2) if any_candies else 0} {'Scroll' if ads_results['got_scroll'] else 'Already Watched'}"

    # Mine
    mine_text = "None"
    if mine_results is not None:
        mine_text = f"{mine_results['hits_made']}/{mine_results['max_hits']} +{mine_results['ores_made']} (Total {mine_results['ores_after']})"

    # Comments
    comments_text = "None"
    if comments_results is not None:
        comments_text = f"{comments_results['successful_comments']}/{comments_results['comments_left']} (Total: {comments_results['total_comments']}) +{comments_results['total_diamonds']} 🍬{comments_results['total_candies']}"

    text = (
        "<b>MAIN DAILY JOB</b>\n\n"
        "<b>Login</b>\n"
        "└ +20?\n\n"
        "<b>Calendar</b>\n"
        f"└ {calendar_text}\n\n"
        "<b>ADs</b>\n"
        f"└ {ads_text}\n\n"
        "<b>Mine</b>\n"
        f"└ {mine_text}\n\n"
        "<b>Comments</b>\n"
        f"└ {comments_text}"
    )

    await bot.send_message(chat_id=info.ADMIN_TG_USER, text=text, parse_mode=ParseMode.HTML)


async def error_message(text: str):
    await bot.send_message(chat_id=info.ADMIN_TG_USER, text=text, parse_mode=ParseMode.HTML)


# testing
async def main():
    text = (
        "<b>MAIN DAILY JOB</b>\n\n"
        "<b>Login</b>\n"
        "└ +20?\n\n"
        "<b>Calendar</b>\n"
        "└ {calendar_text}\n\n"
        "<b>ADs</b>\n"
        "└ {ads_text}\n\n"
        "<b>Mine</b>\n"
        "└ {mine_text}\n\n"
        "<b>Comments</b>\n"
        "└ {comments_text}"
    )
    async with bot:
        await error_message(text=text)

if __name__ == "__main__":
    asyncio.run(main())

