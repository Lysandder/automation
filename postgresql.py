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


# def get_chapter_links(index: int) -> list:
#     with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
#         cur.execute(
#             "SELECT link FROM chapters WHERE id >= %s ORDER BY id ASC LIMIT %s;", 
#             (index, total_chapters_to_read)
#         )
#         return [row[0] for row in cur.fetchall()]


def get_chapter_link(index: int) -> str:
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT link FROM chapters WHERE id = %s;", (index,))
        return cur.fetchone()[0]


def add_card(card_name, rank, copy_number, manga_name, card_id, card_image, wishlist_page_count, action_id):
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO cards_queue (name, rank, copy_number, manga_name, card_id, image, wishlist_page_count, action_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (card_name, rank, copy_number, manga_name, card_id, card_image, wishlist_page_count, action_id))

        return cur.rowcount == 1


def is_active_card() -> bool:
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT EXISTS(SELECT 1 FROM cards_queue WHERE bot_state = %s)", ("active",))
        result = cur.fetchone()
        if result:
            return result[0]
        return False


def get_pending_card_info():
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM cards_queue
            WHERE bot_state = %s
            ORDER BY id
            LIMIT 1
        """, ("pending",))
        result = cur.fetchone() # tuple
        if result is None: # means no pending cards
            return None
        # cur.description is tuple of Column's, Column[0] is "name" of the column
        column_names = [column[0] for column in cur.description]
        card_dict = dict(zip(column_names, result))
        return card_dict


def set_card_state(state, id):
    with psycopg2.connect(info.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE cards_queue
            SET bot_state = %s
            WHERE id = %s
        """, (state, id))
        return cur.rowcount > 0


# testing
if __name__ == "__main__":
    index = get_index()
    print(index)
    print(get_chapter_links(index=index))

