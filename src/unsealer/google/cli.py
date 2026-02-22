# src/unsealer/google/cli.py

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from .decrypter import decrypt_google_auth_uri

# --- 初始化 rich 控制台 ---
console = Console(stderr=True)


def main():
    """
    模块的主执行函数
    """
    parser = argparse.ArgumentParser(
        description="解密 Google Authenticator 导出的 'otpauth-migration://' URI。"
    )
    parser.add_argument(
        "uri",
        nargs="?",  # '?' 表示0个或1个参数，使其成为可选的位置参数
        help="要解密的完整 'otpauth-migration://' URI。如果省略，将进入交互模式。",
        default=None
    )

    args = parser.parse_args(sys.argv[2:])

    auth_uri = args.uri

    # 如果没有通过命令行参数提供URI，则提示用户输入
    if not auth_uri:
        console.print(
            Panel(
                "请粘贴从 Google Authenticator 导出的二维码中获取的完整 URI。",
                title="[bold cyan]交互模式[/bold cyan]",
                border_style="cyan"
            )
        )
        auth_uri = Prompt.ask("[bold yellow]> [/]请输入URI")

    if not auth_uri or not auth_uri.strip():
        console.print(
            Panel("[bold red]错误:[/bold red] 未提供任何 URI。程序退出。", border_style="red")
        )
        sys.exit(1)

    try:
        with console.status("[bold green]正在解码URI并提取账户...[/bold green]", spinner="dots"):
            accounts = decrypt_google_auth_uri(auth_uri.strip())

        console.print(
            Panel(
                f"成功提取 [bold green]{len(accounts)}[/bold green] 个2FA账户。",
                title="[bold green]✓ 解密成功[/bold green]",
                border_style="green"
            )
        )

        # 创建一个表格来展示数据
        table = Table(title="Google Authenticator 账户信息", show_header=True, header_style="bold magenta")
        table.add_column("服务商 (Issuer)", style="dim", width=25)
        table.add_column("账户名 (Name)", style="cyan")
        table.add_column("TOTP 密钥 (Secret)", style="bold yellow", no_wrap=True)

        for account in accounts:
            table.add_row(
                account.get("issuer", "N/A"),
                account.get("name", "N/A"),
                account.get("totp_secret", "ERROR")
            )
        
        console.print(table)

        # 显示最终的安全警告
        console.print(
            Panel(
                "请立即将以上 [bold yellow]TOTP密钥[/bold yellow] 安全地导入到您的新密码管理器或认证应用中。\n处理完毕后，请务必[bold red]安全地删除[/bold red]所有包含这些密钥的临时文件或截图。",
                title="[bold red][!] 安全警告[/bold red]",
                border_style="red"
            )
        )

    except ValueError as e:
        console.print(
            Panel(
                f"[bold red]错误:[/bold red] {e}",
                title="[bold red]✗ 解密失败[/bold red]",
                border_style="red"
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()