import click
from result import Result
from ipelago.db import connect_db, get_cfg, db_path
from ipelago.model import Day
from . import (
    __version__,
    __package_name__,
)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

def check(ctx: click.Context, r: Result, force_exit:bool) -> None:
    """检查 r, 有错误则打印并终止程序，无错误则什么都不用做。
       如果 force_exit is True, 则即使没有错误也终止程序。
    """
    errMsg = r.err()
    if errMsg:
        click.echo(f"Error: {errMsg}", err=True)
        ctx.exit()
    if force_exit:
        ctx.exit()


def show_info(ctx: click.Context, _, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"[ago] {__file__}")
    click.echo(f"[version] {__version__}")
    click.echo(f"[database] {db_path}")

    with connect_db() as conn:
        cfg = get_cfg(conn).unwrap()
        click.echo(f"[Zen Mode Always ON] {cfg.zen_mode}")
        click.echo(f"[http_proxy] {cfg.http_proxy}")
        click.echo(f"[use_proxy] {cfg.use_proxy}")
        click.echo(f"[session-max-age] {cfg.session_max_age//Day} days")

    click.echo(f"[repo] https://github.com/ahui2016/pypelago")
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
    help="Show informations about ipelago-cli.",
    expose_value=False,
    callback=show_info,
)
@click.pass_context
def cli(ctx: click.Context):
    """ipelago: CLI personal microblog (命令行个人微博客)

    https://pypi.org/project/ipelago/
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()
