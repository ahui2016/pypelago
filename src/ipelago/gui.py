import tkinter as tk
from ipelago.model import my_bucket
import ipelago.util as util

import pyperclip


def tk_post_msg(pri: bool) -> None:
    window = tk.Tk()
    window.title("Post - ipelago")
    window.rowconfigure(0, minsize=500, weight=1)
    window.columnconfigure(1, minsize=500, weight=1)

    window_width = 500
    window_height = 250
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x_cordinate = int((screen_width / 2) - (window_width / 2))
    y_cordinate = int((screen_height / 2) - (window_height / 2))
    window.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

    label = tk.Label(text="ipelago", pady=5)
    label.pack()

    frame = tk.Frame(master=window, relief=tk.RAISED, borderwidth=1, padx=5, pady=5)
    frame.pack()

    form_input = tk.Text(master=frame, width=60, height=10, pady=5)
    form_input.pack()

    def tk_click():
        msg = form_input.get("1.0", tk.END)
        util.post_msg(msg, my_bucket(pri))
        window.quit()

    post_btn = tk.Button(master=frame, text="Post", command=tk_click)
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
