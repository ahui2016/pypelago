from typing import Any, cast
import click
import pyperclip
from result import Result
from ipelago.db import (
    connect_db,
    get_cfg,
    db_path,
    init_app,
    post_msg,
    update_cfg,
)
from ipelago.model import Bucket, my_bucket
from ipelago.publish import publish_html
from ipelago.util import (
    print_my_next_msg,
    print_my_today,
    print_my_yesterday,
    print_news_next_msg,
    subscribe,
)
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
    if not db_path.exists():
        click.echo("请先使用 'ago init' 命令进行初始化")
        ctx.exit()


def show_info(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    click.echo(f"[ago] {__file__}")
    click.echo(f"[version] {__version__}")
    click.echo(f"[database] {db_path}")

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()
        click.echo(f"[Zen Mode Always ON] {cfg['zen_mode']}")
        click.echo(f"[http_proxy] {cfg['http_proxy']}")
        click.echo(f"[use_proxy] {cfg['use_proxy']}")

    click.echo("[repo] https://github.com/ahui2016/pypelago")
    ctx.exit()


def set_proxy(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()
        value = cast(str, value).lower()
        if value == "true":
            cfg["use_proxy"] = True
        elif value == "false":
            cfg["use_proxy"] = False
        else:
            cfg["http_proxy"] = value
        update_cfg(cfg, conn)

        click.echo("OK.")
        click.echo(f"[http_proxy] {cfg['http_proxy']}")
        click.echo(f'[use_proxy] {cfg["use_proxy"]}')
    ctx.exit()


def toggle_zen(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    check_init(ctx)

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()
        cfg["zen_mode"] = not cfg["zen_mode"]
        click.echo(f"[Zen Mode Always ON] {cfg['zen_mode']}")
        update_cfg(cfg, conn)
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
            check(ctx, init_app(name), True)

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
    check(ctx, init_app(name), True)


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "filename",
    "-f",
    "--file",
    type=click.Path(exists=True),
    help="Send the content of the file.",
)
@click.argument("msg", nargs=-1)
@click.option(
    "pri", "-pri", "--private", is_flag=True, help="Specify the private island"
)
@click.pass_context
def post(ctx: click.Context, msg: Any, filename: str, pri: bool):
    """Post a message. (发送消息)

    Example 1: ago post (默认发送系统剪贴板的内容)

    Example 2: ago post Hello world! (发送 'Hello world!')

    Example 3: ago post -f ./file.txt (发送文件内容)
    """
    check_init(ctx)
    if msg:
        msg = " ".join(msg).strip()
    else:
        try:
            msg = pyperclip.paste()
        except Exception:
            pass

    click.echo(post_msg(msg, my_bucket(pri)))
    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "first", "-first", "--first", is_flag=True, help="Read my latest message."
)
@click.option("next", "-next", "--next", is_flag=True, help="Read my next message.")
@click.option("today", "-today", "--today", is_flag=True, help="Read today's messages.")
@click.option(
    "yesterday",
    "-yday",
    "--yesterday",
    is_flag=True,
    help="Read yesterday's messages.",
)
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
    today: bool,
    yesterday: bool,
    pub: bool,
    pri: bool,
    limit: int,
    zen: bool,
):
    """Timeline: Read my messages. (阅读自己发布的消息)

    Example 1: ago tl        (阅读下一条消息)

    Example 2: ago tl -first (阅读最新一条消息)

    Example 3: ago tl -today (阅读今天的消息，默认上限 9 条)

    Example 3: ago tl -today -limit 30 (设定上限为 30 条消息)
    """
    check_init(ctx)

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()

        if not limit:
            limit = cfg["cli_page_n"]

        buckets = [Bucket.Public.name, Bucket.Private.name]
        if pub:
            buckets = [Bucket.Public.name]
        if pri:
            buckets = [Bucket.Private.name]

        # 专注模式
        if cfg["zen_mode"] or zen:
            print()
            click.clear()

        if today:
            print_my_today(limit, buckets, conn)
        elif yesterday:
            print_my_yesterday(limit, buckets, conn)
        elif first:
            cfg["tl_cursor"] = ""
            update_cfg(cfg, conn)
            print_my_next_msg(conn)
        else:
            print_my_next_msg(conn)

    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def publish(ctx: click.Context):
    check_init(ctx)

    with connect_db() as conn:
        publish_html(conn)

    ctx.exit()


@cli.command(context_settings=CONTEXT_SETTINGS)
@click.option("feed_list", "-l", "--list", is_flag=True, help="List all feeds.")
@click.option("follow", "-follow", "--follow", help="Subscribe a feed.")
@click.option(
    "first", "-first", "--first", is_flag=True, help="Read the latest message."
)
@click.option("next", "-next", "--next", is_flag=True, help="Read the next message.")
@click.option(
    "limit", "-limit", "--limit", type=int, help="Limit the number of messages."
)
@click.option("update", "-u", "--update", is_flag=True, help="Update a feed.")
@click.option("name", "-name", "--name", help="Set the name of a feed.")
@click.option("delete", "-d", "--delete", help="Delete a feed (specify by url).")
@click.option(
    "force", "-force", "--force", is_flag=True, help="Force to update or delete."
)
@click.option("zen", "-zen", "--zen-mode", is_flag=True, help="Zen mode. (专注模式)")
@click.pass_context
def news(
    ctx: click.Context,
    follow: str,
    feed_list: bool,
    first: bool,
    next: bool,
    limit: int,
    force: bool,
    update: bool,
    name: str,
    delete: str,
    zen: bool,
):
    """Subscribe and read feeds. (订阅别人的消息)"""
    check_init(ctx)

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()

        if not limit:
            limit = cfg["cli_page_n"]

        if follow:
            subscribe(follow, conn)
        elif first:
            cfg["news_cursor"] = ""
            update_cfg(cfg, conn)
            print_news_next_msg(conn)
        else:
            print_news_next_msg(conn)

    ctx.exit()


if __name__ == "__main__":
    cli(obj={})
