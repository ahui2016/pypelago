import sqlite3
import tkinter as tk
from ipelago.model import PublicBucketID, my_bucket
from ipelago.publish import publish_show_info
import ipelago.util as util
import ipelago.db as db

import pyperclip


def create_window_center(title: str) -> tk.Tk:
    window = tk.Tk()
    window.title(title)
    window.rowconfigure(0, minsize=500, weight=1)
    window.columnconfigure(1, minsize=500, weight=1)

    window_width = 500
    window_height = 250
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x_cordinate = int((screen_width / 2) - (window_width / 2))
    y_cordinate = int((screen_height / 2) - (window_height / 2))
    window.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

    return window


def create_input(master: tk.Misc, label: str, text: str, row: int) -> tk.Entry:
    form_label = tk.Label(master=master, text=label)
    form_input = tk.Entry(master=master, width=50)
    tk.Label(master=master, text=" ").grid(row=row, column=0, pady=5)
    form_label.grid(row=row, column=1, pady=5)
    form_input.grid(row=row, column=2, pady=5)
    tk.Label(master=master, text=" ").grid(row=row, column=3, pady=5)
    form_input.insert(tk.END, text)
    return form_input


def get_text(form_input: tk.Entry | tk.Text) -> str:
    if type(form_input) is tk.Entry:
        return form_input.get().strip()
    elif type(form_input) is tk.Text:
        return form_input.get("1.0", tk.END).strip()
    else:
        return ""


def tk_my_feed_info(conn: sqlite3.Connection) -> None:
    feed = db.get_feed_by_id(PublicBucketID, conn).unwrap()
    window = create_window_center("info - ipelago")

    label = tk.Label(text="Informations of my feed", pady=5)
    label.pack(pady=5)

    form = tk.Frame(relief=tk.SUNKEN, borderwidth=3)
    form.pack()

    tk.Label(master=form, text=" ").grid(row=0, column=0)
    title_input = create_input(form, "Title", feed.title, 1)
    link_input = create_input(form, "Link", feed.link, 2)
    author_input = create_input(form, "Author", feed.author_name, 3)
    tk.Label(master=form, text=" ").grid(row=4, column=0)

    buttons = tk.Frame()
    buttons.pack(pady=5)

    def btn_click():
        title = get_text(title_input)
        link = get_text(link_input)
        author = get_text(author_input)
        db.update_my_feed_info(link, title, author, conn).unwrap()
        window.quit()
        publish_show_info(conn)

    update_btn = tk.Button(master=buttons, text="Update", command=btn_click)
    update_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    cancel_btn = tk.Button(master=buttons, text="Cancel", command=window.quit)
    cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    title_input.focus()
    window.mainloop()


def tk_post_msg(pri: bool) -> None:
    window = create_window_center("Post - ipelago")

    label = tk.Label(text="ipelago", pady=5)
    label.pack()

    frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1, padx=5, pady=5)
    frame.pack()

    form_input = tk.Text(master=frame, width=60, height=10, pady=5)
    form_input.pack()

    def btn_click():
        msg = get_text(form_input)
        util.post_msg(msg, my_bucket(pri))
        window.quit()

    post_btn = tk.Button(master=frame, text="Post", command=btn_click)
    post_btn.pack(side=tk.RIGHT, padx=5, pady=5, ipadx=5)

    cancel_btn = tk.Button(master=frame, text="Cancel", command=window.quit)
    cancel_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    form_input.focus()
    try:
        msg = pyperclip.paste()
        form_input.insert(tk.END, msg)
    except Exception:
        pass

    window.mainloop()
