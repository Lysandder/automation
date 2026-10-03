# def scrape_names():
#     with sync_playwright() as p:
#         browser = p.chromium.launch_persistent_context(
#             user_data_dir="./user_data", headless=True)
#
#         cleanup(browser)
#         page = browser.new_page()
#
#         ensure_logged_in(page)
#
#         page.goto(SHOJOS_URL) # not safe goto
#         time.sleep(random.randint(3, 7))
#
#         next_page_button = page.locator(
#             "li.pagination__button a", has_text="Вперёд")
#
#         while (next_page_button.count() > 0):
#             names_links = page.eval_on_selector_all(
#                 "a.cards__item",
#                 "els => els.map(el => el.href)"
#             )
#             with open("names.txt", 'a') as file:
#                 for link in names_links:
#                     file.write(link + "\n")
#             next_page_button.click() # not safe click
#             time.sleep(random.randint(2, 5))
#
#         browser.close()
#
#
# def scrape_chapters():
#     with sync_playwright() as p:
#         browser = p.chromium.launch_persistent_context(
#             user_data_dir="./user_data", headless=True)
#
#         cleanup(browser)
#         page = browser.new_page()
#
#         ensure_logged_in(page)
#
#         with open("names.txt", "r") as names_file:
#             for line in names_file:
#                 # for line in islice(names_file, 204, None):
#                 page.goto(line.strip()) # not safe goto
#                 time.sleep(random.randint(1, 5))
#
#                 if page.is_disabled("button[data-page='chapters']"):
#                     print_cyan("=" * 100)
#                     print_cyan(line)
#                     print_cyan("=" * 100)
#                     continue
#                 page.click("button[data-page='chapters']") # not safe click
#
#                 chapters_links = page.eval_on_selector_all(
#                     ".chapters__list a.chapters__item",
#                     "els => els.map(el => el.href)"
#                 )
#
#                 with open("chapters.txt", 'a') as file:
#                     for link in chapters_links:
#                         file.write(link + "\n")
#                 time.sleep(random.randint(1, 5))
#
#         browser.close()
