from typing import Any, cast
import click
import pyperclip
from result import Result
from ipelago import stmt
from ipelago import db
from ipelago.gui import tk_my_feed_info, tk_post_msg
from ipelago.model import AppConfig, Bucket, my_bucket
from ipelago.publish import check_before_publish, publish_html, publish_show_info
from ipelago import util
from . import (
    __version__,
    __package_name__,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def check(ctx: click.Context, r: Result[Any, str], force_exit: bool) -> None:
    """检查 r, 有错误则打印并终止程序，无错误则什么都不用做。
    如果 force_exit is True, 则即使没有错误也终止程序。
    """
    errMsg = r.err()
    if errMsg:
        click.echo(f"Error: {errMsg}", err=True)
        ctx.exit()
    if force_exit:
        ctx.exit()


def check_init(ctx: click.Context) -> None:
    if not db.db_path.exists():
        click.echo("请先使用 'ago init' 命令进行初始化")
        ctx.exit()


def check_id(ctx: click.Context, item_id: str | None) -> None:
    if not item_id:
        click.echo("Error: require to specify an id.")
        ctx.exit()


def check_tk(tk_gui_func):
    try:
        tk_gui_func()
    except Exception:
        pass


def zen_mode(cfg: AppConfig, zen: bool) -> None:
    if cfg["zen_mode"] or zen:
        print()
        click.clear()


def show_info(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    click.echo(f"[ago] {__file__}")
    click.echo(f"[version] {__version__}")
    click.echo(f"[database] {db.db_path}")

    with db.connect_db() as conn:
        cfg = db.get_cfg(conn).unwrap()
        click.echo(f"[Zen Mode Always ON] {cfg['zen_mode']}")
        click.echo(f"[http_proxy] {cfg['http_proxy']}")
        click.echo(f"[use_proxy] {cfg['use_proxy']}")

    click.echo("[repo] https://github.com/ahui2016/pypelago")
    ctx.exit()


def set_proxy(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    with db.connect_db() as conn:
        cfg = db.get_cfg(conn).unwrap()
        value = cast(str, value).lower()
        if value == "true":
            cfg["use_proxy"] = True
        elif value == "false":
            cfg["use_proxy"] = False
        else:
            cfg["http_proxy"] = value
        db.update_cfg(cfg, conn)

        click.echo("OK.")
        click.echo(f"[http_proxy] {cfg['http_proxy']}")
        click.echo(f'[use_proxy] {cfg["use_proxy"]}')
    ctx.exit()


def toggle_zen(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    with db.connect_db() as conn:
        cfg = db.get_cfg(conn).unwrap()
        cfg["zen_mode"] = not cfg["zen_mode"]
        click.echo(f"[Zen Mode Always ON] {cfg['zen_mode']}")
        db.update_cfg(cfg, conn)
    ctx.exit()


@click.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.version_option(
    __version__,
    "-v",
    "-V",
    "--version",
    package_name=__package_name__,
    message="%(prog)s version: %(version)s",
)
@click.option(
    "-i",
    "--info",
    is_flag=True,
    help="Show informations about config and more.",
    expose_value=False,
    callback=show_info,
)
@click.option(
    "--set-proxy",
    help="Set the http proxy for requests.",
    expose_value=False,
    callback=set_proxy,
)
@click.option(
    "-zen",
    "--toggle-zen",
    is_flag=True,
    help="Toggle zen mode.",
    expose_value=False,
    callback=toggle_zen,
)
@click.option("name", "-init", "--init", help="Same as 'ago init'")
@click.pass_context
def cli(ctx: click.Context, name: str):
    """ipelago: CLI personal microblog (命令行个人微博客)

    https://pypi.org/project/pypelago/
    """
    if ctx.invoked_subcommand is None:
        if name:
            click.echo(db.init_app(name))
            ctx.exit()

        click.echo(ctx.get_help())
        ctx.exit()


# 以上是主命令
############
# 以下是子命令


@cli.command(context_settings=CONTEXT_SETTINGS, name="init")
@click.argument("name", nargs=1, required=True)
@click.pass_context
def init_command(ctx: click.Context, name: str):
    """Set the name of your microblog and initialize it.

    设置你的微博客名称并初始化数据库。

    Example: ago init "Emily's Microblog"
    """
    click.echo(db.init_app(name))
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "filename",
    "-f",
    "--file",
    type=click.Path(exists=True),
    help="Send the content of the file.",
)
@click.option(
    "gui", "-g", "--gui", is_flag=True, help="Open a GUI window for text input."
)
@click.argument("msg", nargs=-1)
@click.option(
    "pri", "-pri", "--private", is_flag=True, help="Specify the private island"
)
@click.pass_context
def post(ctx: click.Context, msg: Any, filename: str, gui: bool, pri: bool):
    """Post a message. (发送消息)

    Examples:

    ago post Hello world! (写一条微博客，内容为 'Hello world!')

    ago post              (默认发送系统剪贴板的内容)

    ago post -g           (打开 GUI 窗口写微博客)
    """
    check_init(ctx)

    if gui:
        check_tk(tk_post_msg(pri))
        ctx.exit()

    if filename:
        with open(filename, "r", encoding="utf-8") as f:
            msg = f.read()
        util.post_msg(msg, my_bucket(pri))
        ctx.exit()

    if msg:
        msg = " ".join(msg).strip()
    else:
        try:
            msg = pyperclip.paste()
        except Exception:
            pass

    util.post_msg(msg, my_bucket(pri))
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("entry_id", nargs=1)
@click.pass_context
def toggle(ctx: click.Context, entry_id: str):
    """Toggle Public/Private of an entry.

    切换一条消息的公开/隐私状态。
    """
    check_init(ctx)
    util.toggle_entry_bucket(entry_id)
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "first", "-first", "--first", is_flag=True, help="Read my latest message."
)
@click.option("next", "-next", "--next", is_flag=True, help="Read my next message.")
@click.option(
    "goto_date", "-go", "--goto", help="Move the cursor to a date(YYYY-MM-DD)"
)
@click.option("today", "-today", "--today", is_flag=True, help="Read today's messages.")
@click.option(
    "yesterday",
    "-yday",
    "--yesterday",
    is_flag=True,
    help="Read yesterday's messages.",
)
@click.option("date_prefix", "-date", "--date", help="Read messages of a date.")
@click.option("count", "-count", "--count", help="Count messages of a date.")
@click.option(
    "pub", "-pub", "--public", is_flag=True, help="Read my public messages only."
)
@click.option(
    "pri", "-pri", "--private", is_flag=True, help="Read my private messages only."
)
@click.option(
    "limit", "-limit", "--limit", type=int, help="Limit the number of messages."
)
@click.option("zen", "-zen", "--zen-mode", is_flag=True, help="Zen mode. (专注模式)")
@click.pass_context
def tl(
    ctx: click.Context,
    next: bool,
    first: bool,
    goto_date: str,
    today: bool,
    yesterday: bool,
    date_prefix: str,
    count: str,
    pub: bool,
    pri: bool,
    limit: int,
    zen: bool,
):
    """Timeline: Read my messages. (阅读自己发布的消息)

    Examples:

    ago tl        (阅读下一条消息)

    ago tl -first (阅读最新一条消息)

    ago tl -today (阅读今天的消息，默认上限 9 条)

    ago tl -today -limit 30 (设定上限为 30 条消息)
    """
    check_init(ctx)

    with db.connect_db() as conn:
        cfg = db.get_cfg(conn).unwrap()

        if not limit:
            limit = cfg["cli_page_n"]

        buckets = []
        if pub:
            buckets = [Bucket.Public.name]
        if pri:
            buckets = [Bucket.Private.name]

        if today:
            util.print_my_today(limit, buckets, conn)
        elif yesterday:
            util.print_my_yesterday(limit, buckets, conn)
        elif date_prefix:
            util.print_my_entries(date_prefix, limit, buckets, conn)
        elif count:
            util.count_my_entries(count, buckets, conn)
        elif goto_date:
            util.my_cursor_goto(goto_date, conn)
        elif first:
            zen_mode(cfg, zen)
            cfg["tl_cursor"] = ""
            db.update_cfg(cfg, conn)
            util.print_my_next_msg(conn)
        else:
            zen_mode(cfg, zen)
            util.print_my_next_msg(conn)

    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "gui", "-g", "--gui-info", is_flag=True, help="Open a GUI window to view/edit info."
)
@click.option(
    "info", "-info", "--info", is_flag=True, help="Show informations about my feed."
)
@click.option("link", "--set-link", help="Set the RSS link of my feed.")
@click.option("title", "--set-title", help="Set the title of my feed.")
@click.option("author", "--set-author", help="Set the author of my feed.")
@click.option("force", "-force", "--force", is_flag=True, help="Confirm overwrite.")
@click.pass_context
def publish(
    ctx: click.Context,
    gui: bool,
    link: str,
    title: str,
    author: str,
    info: bool,
    force: bool,
):
    check_init(ctx)

    with db.connect_db() as conn:
        if gui:
            check_tk(tk_my_feed_info(conn))
        elif info:
            publish_show_info(conn)
        elif title:
            db.connExec(conn, stmt.Update_my_feed_title, {"title": title}).unwrap()
            publish_show_info(conn)
        elif link:
            db.connExec(conn, stmt.Update_my_feed_link, {"link": link}).unwrap()
            publish_show_info(conn)
        elif author:
            db.connExec(conn, stmt.Update_my_feed_author, {"author": author}).unwrap()
            publish_show_info(conn)
        else:
            check(ctx, check_before_publish(conn), False)
            publish_html(conn, force)

    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option("show_list", "-l", "--list", is_flag=True, help="List all feeds.")
@click.option("follow", "-follow", "--follow", help="Subscribe a feed.")
@click.option(
    "parser",
    "-p",
    "--parser",
    type=click.Choice(["Base", "HasTitle", "HasSummary"]),
    help="Select a parser.",
)
@click.option(
    "first", "-first", "--first", is_flag=True, help="Read the latest message."
)
@click.option("next", "-next", "--next", is_flag=True, help="Read the next message.")
@click.option(
    "goto_date", "-go", "--goto", help="Move the cursor to a date(YYYY-MM-DD)"
)
@click.option(
    "limit", "-limit", "--limit", type=int, help="Limit the number of messages."
)
@click.option("update", "-u", "--update", help="Update a feed.")
@click.option("feed_id", "-feed", "--feed", help="Show messages of a feed.")
@click.option("new_id", "--set-id", help="Change the id of a feed.")
@click.option("new_name", "--set-name", help="Change the name of a feed.")
@click.option("delete", "-delete", "--delete", help="Delete a feed (specify by id).")
@click.option(
    "force", "-force", "--force", is_flag=True, help="Force to update or delete."
)
@click.option("zen", "-zen", "--zen-mode", is_flag=True, help="Zen mode. (专注模式)")
@click.pass_context
def news(
    ctx: click.Context,
    follow: str,
    parser: str,
    show_list: bool,
    first: bool,
    next: bool,
    goto_date:str,
    limit: int,
    force: bool,
    update: str,
    feed_id: str,
    new_id: str,
    new_name: str,
    delete: str,
    zen: bool,
):
    """Subscribe and read feeds. (订阅别人的消息)

    Exmaples:

    ago news -u all     (批量更新全部源)

    ago news -u r92p72  (更新 id 为 R92P72 的源)
    """
    check_init(ctx)

    with db.connect_db() as conn:
        cfg = db.get_cfg(conn).unwrap()

        if not limit:
            limit = cfg["cli_page_n"]

        if show_list:
            util.print_subs_list(conn)
        elif follow:
            if not parser:
                parser = "Base"
            util.subscribe(follow, parser, conn)
        elif update and update.upper() == "ALL":
            util.update_all_feeds(conn)
        elif update:
            util.update_one_feed(update, parser, force, conn)
        elif new_id:
            check_id(ctx, feed_id)
            """这是既有 new_id 也有 feed_id 的情形"""
            check(ctx, db.update_feed_id(new_id, feed_id, conn), False)
            util.print_subs_list(conn, new_id)
        elif new_name:
            check_id(ctx, feed_id)
            """这是既有 new_name 也有 feed_id 的情形"""
            check(ctx, db.update_feed_title(new_name, feed_id, conn), False)
            util.print_subs_list(conn, feed_id)
        elif feed_id:
            """这是只有 feed_id, 没有 new_id 的情形"""
            entries = db.get_news_by_feed(feed_id, limit, conn)
            util.print_entries(entries, cfg["news_show_link"], util.print_news_short_id)
        elif delete:
            if not force:
                click.echo("Error: require '-force' to delete a feed.")
                ctx.exit()
            click.echo(db.delete_feed(delete, conn))
        elif goto_date:
            util.news_cursor_goto(goto_date, conn)
        elif first:
            zen_mode(cfg, zen)
            cfg["news_cursor"] = ""
            db.update_cfg(cfg, conn)
            util.print_news_next_msg(conn)
        else:
            zen_mode(cfg, zen)
            util.print_news_next_msg(conn)

    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "entry_id", "-like", "--like", help="Move an entry to the Favorite bucket."
)
@click.pass_context
def fav(ctx: click.Context, entry_id: str):
    check_init(ctx)

    with db.connect_db() as conn:
        if entry_id:
            util.move_to_fav(entry_id, conn)
        else:
            util.print_recent_fav(conn)


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("entry_id", nargs=1)
@click.pass_context
def like(ctx: click.Context, entry_id: str):
    """Same as 'ago fav -like'"""
    check_init(ctx)

    with db.connect_db() as conn:
        util.move_to_fav(entry_id, conn)


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.argument("entry_id", nargs=1)
@click.option(
    "link", "-link", "--link", is_flag=True, help="Copy the link of an entry."
)
@click.pass_context
def copy(ctx: click.Context, entry_id: str, link: bool):
    """Copy the content/link of an entry. (复制消息内容或消息链接)

    Examples:

    ago copy 97ur       (复制 id 为 97ur 的消息的内容)

    ago copy 97ur -link (复制 id 为 97ur 的消息的链接，是指消息本身的链接)
    """
    with db.connect_db() as conn:
        util.copy_msg_link(entry_id, link, conn)
    ctx.exit()


if __name__ == "__main__":
    cli(obj={})
