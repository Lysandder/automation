from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from asyncio import to_thread
from aiohttp import web
import requests
import main
import bot

sess = main.get_auth_session()
main.human_delay()


def check_session(sess: requests.Session) -> requests.Session | None:
    user_id = main.get_user_id(sess)
    if user_id is None:
        new_sess = main.get_auth_session()
        main.human_delay()
        if new_sess is None:
            print("Error during authentication for scheduler")
            return
        return new_sess
    return sess


def get_session():
    global sess
    new_sess = check_session(sess)
    if new_sess is None:
        print(f"Error during session checking")
        return
    sess = new_sess
    return sess


# def job_wrapper(function):
#     global sess
#     new_sess = check_session(sess)
#     if new_sess is None:
#         print(f"Error during session checking, skipping {function.__name__}")
#         return
#     sess = new_sess
#     return function(sess)


async def main_job():
    sess = await to_thread(get_session)
    if sess is None:
        sess = await to_thread(main.get_auth_session)

    calendar_results = await to_thread(main.claim_calendar_gift, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    ads_results = await to_thread(main.watch_ads, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    mine_results = await to_thread(main.mine, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    comments_results = await to_thread(main.leave_comments, sess)
    await to_thread(main.human_delay, 12.4, 21.6)

    await bot.main_job_message(
        calendar_results=calendar_results,
        ads_results=ads_results,
        mine_results=mine_results,
        comments_results=comments_results
    )


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


async def main_module_func():
    await uptime_check()

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    scheduler.add_job(
        func=main_job,
        trigger="cron",
        hour=5,
        minute=30
    )


    # Scheduling 10 chapter reads
    #
    # scheduler.add_job(
    #     func=to_thread,
    #     trigger="cron",
    #     hour=9,
    #     minute=41,
    #     args=[main.read_chapters, sess]
    # )


    times = []
    start_min = 6 * 60 # 06:00 AM in minutes from midnight

    for _ in range(10):
        h = start_min // 60
        m = start_min % 60
        times.append((h, m))
        start_min += 75

    for h, m in times:
        scheduler.add_job(
            func=to_thread,
            trigger="cron",
            hour=h,
            minute=m,
            args=[main.read_chapters, sess]
        )

    scheduler.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main_module_func())
