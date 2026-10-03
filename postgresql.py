import psycopg2
import info

total_chapters_to_read = 3


def get_index():
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT value FROM state WHERE key = %s;", ("index",))
        response = cur.fetchone()
        if not response or response[0] == 0:
            raise ValueError(
                f"Invalid state index retrieved: {response[0] if response else 'None'}. "
                "Expected a non-zero index in database."
            )
        return response[0]


def set_index(chapters_read: int = total_chapters_to_read):
    current_index = get_index()
    new_index = current_index + chapters_read 
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("UPDATE state SET value = %s WHERE key = %s;", (new_index, "index"))


def get_chapter_links(index: int) -> list:
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT link FROM chapters WHERE id >= %s ORDER BY id ASC LIMIT %s;", 
            (index, total_chapters_to_read)
        )
        return [row[0] for row in cur.fetchall()]


def add_card(card_name, rank, copy_number, manga_name, card_id, card_image, wishlist_page_count):
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cards_queue (name, rank, copy_number, manga_name, card_id, image, wishlist_page_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (card_name, rank, copy_number, manga_name, card_id, card_image, wishlist_page_count))

        return cur.rowcount == 1

