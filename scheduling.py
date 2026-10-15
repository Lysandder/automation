from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from asyncio import to_thread
from aiohttp import web
import requests
import main
import bot

sess = main.get_auth_session()
main.human_delay()


def get_session():
    global sess
    if sess is not None and main.get_user_id(sess=sess) is not None:
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

    await to_thread(print, "Finished the main job")


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
    await bot.dp.start_polling(bot.bot, handle_signals=False)
    # await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main_module_func())
