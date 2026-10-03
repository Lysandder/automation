# import psycopg2
# from psycopg2.extras import execute_values
# import io
# import db
# import info
#
# conn = psycopg2.connect(info.DATABASE_URL)
# cur = conn.cursor()
# # cur.execute("DROP TABLE IF EXISTS chapters, names, state CASCADE;")
#
#
# # INDEX
# cur.execute("""
#     CREATE TABLE IF NOT EXISTS state (
#         key TEXT PRIMARY KEY,
#         value INT NOT NULL
#     )
# """)
#
# current_index = db.get_index()
#
# cur.execute("""
#     INSERT INTO state (key, value)
#     VALUES (%s, %s)
#     ON CONFLICT (key)
#     DO UPDATE SET value = EXCLUDED.value
# """, ("index", current_index))
#
#
# # CHAPTERS
# cur.execute("""
#     CREATE TABLE IF NOT EXISTS chapters (
#         id SERIAL PRIMARY KEY,
#         link TEXT NOT NULL UNIQUE
#     )
# """)
#
# with open("chapters.txt", 'r') as file:
#     # chapter_links = [line.strip() for line in file if line.strip()]
#     chapter_links = list(dict.fromkeys(line.strip() for line in file if line.strip())) # removes duplicates if they exist
# chapter_links_str = io.StringIO('\n'.join(chapter_links))
# chapter_links_str.seek(0)
# cur.copy_expert("COPY chapters (link) FROM STDIN WITH (FORMAT text)", chapter_links_str)
#
# # NAMES
# cur.execute("""
#     CREATE TABLE IF NOT EXISTS names (
#         id SERIAL PRIMARY KEY,
#         link TEXT NOT NULL UNIQUE
#     )
# """)
#
# with open("names.txt", 'r') as file:
#     # name_links = [line.strip() for line in file if line.strip()]
#     name_links = list(dict.fromkeys(line.strip() for line in file if line.strip())) # removes duplicates if they exist
# name_links_str = io.StringIO('\n'.join(name_links))
# cur.copy_expert("COPY names (link) FROM STDIN WITH (FORMAT text)", name_links_str)
#
#
# # CARDS QUEUE
# cur.execute("""
#     CREATE TABLE IF NOT EXISTS cards_queue (
#         id SERIAL PRIMARY KEY,
#         name TEXT NOT NULL,
#         rank TEXT NOT NULL,
#         copy_number INT NOT NULL,
#         manga_name TEXT NOT NULL,
#         card_id INT NOT NULL,
#         image TEXT NOT NULL,
#         wishlist_page_count INT NOT NULL
#     )
# """)
#
#
# conn.commit() # for committing inserting, updating requests
#
# cur.close()
# conn.close()

