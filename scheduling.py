from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from asyncio import to_thread
from aiohttp import web
import requests
import main
import bot
import datetime

sess = main.get_auth_session()
main.human_delay()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")


def get_session():
    global sess
    if (
        sess is not None 
        and main.get_user_id(sess=sess) is not None
        and main.sync_csrf_token(sess)
    ):
        return sess
    new_sess = main.get_auth_session()
    if new_sess is None:
        print(f"Authentication failed, scheduling->get_session")
        return
    main.human_delay()
    globals()["sess"] = new_sess
    return new_sess 


# def job_wrapper(function):
#     global sess
#     new_sess = check_session(sess)
#     if new_sess is None:
#         print(f"Error during session checking, skipping {function.__name__}")
#         return
#     sess = new_sess
#     return function(sess)


def schedule_read(minutes: int, any_candies: bool = False):
    run_at = datetime.datetime.now(scheduler.timezone) + datetime.timedelta(minutes=minutes)
    if run_at.hour >= 22:
        print("Past 22:00, stopping chapter reads for today")
        return
    scheduler.add_job(
        func=read_chapters_job,
        args=[any_candies],
        trigger="date",
        run_date=run_at,
        id="read_chapters",
        replace_existing=True
    )


async def run_main_job_func(func, *args):
    try:
        return await to_thread(func, *args)
    except Exception as e:
        print(f"ERROR during main job {func.__name__},\n{e}")
        return None


async def main_job():
    sess = await run_main_job_func(get_session)
    if sess is None:
        sess = await run_main_job_func(main.get_auth_session)
        if sess is None:
            print("Some kind of stupid errors during authentication, scheduling->main_job")
            return

    login_results = await run_main_job_func(main.get_login_reward, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    calendar_results = await run_main_job_func(main.claim_calendar_gift, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    ads_results = await run_main_job_func(main.watch_ads, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    mine_results = await run_main_job_func(main.mine, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    comments_results = await run_main_job_func(main.leave_comments, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    try:
        await bot.main_job_message(
            calendar_results=calendar_results,
            ads_results=ads_results,
            mine_results=mine_results,
            comments_results=comments_results,
            login_results=login_results,
        )
    except Exception as e:
        print(f"Failed main job, {e}")

    # any_candies = True if comments_results and (comments_results.get("total_candies", 0) > 0) else False
    any_candies = True
    await to_thread(print, "Finished the main job")

    schedule_read(minutes=10, any_candies=any_candies)
    print("Scheduled reading in 10 minutes")

async def health_check(request):
    return web.Response(text="OK", status=200)


async def uptime_check():
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


async def read_chapters_job(any_candies: bool = False):
    sess = await run_main_job_func(get_session)
    if sess is None:
        sess = await run_main_job_func(main.get_auth_session)
    if sess is None:
        print("Some kind of stupid errors during authentication, scheduling->read_chapters_job")
        schedule_read(minutes=10, any_candies=any_candies)
        print("Rescheduled reading to 10 minutes later")
        return
    reading_result = await run_main_job_func(main.read_chapters, sess, any_candies)
    if reading_result is None:
        print("main.read_chapters returned None")
        schedule_read(minutes=10, any_candies=any_candies)
        print("Rescheduled reading to 10 minutes later")
        return
    elif reading_result.get("done"):
        await to_thread(print, "Got all cards for today")
    else:
        schedule_read(minutes=75, any_candies=any_candies)
        print("Scheduled reading in 75 minutes")


async def main_module_func():
    await uptime_check()

    scheduler.add_job(
        func=main_job,
        trigger="cron",
        hour=7,
        minute=30
    )

    now = datetime.datetime.now(scheduler.timezone)
    if now.time() >= datetime.time(7, 30):
        print("Started after 07:30, starting chapter reads")
        await main_job()

    scheduler.start()
    await bot.dp.start_polling(bot.bot, handle_signals=False)
    # await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main_module_func())

