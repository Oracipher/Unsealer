import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from .decrypter import decrypt_google_auth_uri

console = Console(stderr=True)

def main():
    parser = argparse.ArgumentParser(description="Google Authenticator 解封模块")
    parser.add_argument("uri", nargs="?", help="otpauth-migration:// 链接", default=None)
    args = parser.parse_args(sys.argv[2:])

    uri = args.uri
    if not uri:
        console.print(Panel("请粘贴从 Google Authenticator 导出的 URI 文本", title="[bold cyan]Google 模块", border_style="cyan"))
        uri = Prompt.ask("[bold yellow]> [/] 请输入 URI")

    if not uri.strip():
        console.print("[bold red]错误: [/] 未提供 URI。")
        return

    try:
        with console.status("[bold green]正在解析数据流..."):
            accounts = decrypt_google_auth_uri(uri.strip())

        table = Table(title="提取到的 2FA 账户", show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("服务商", style="cyan")
        table.add_column("账号名称", style="green")
        table.add_column("TOTP 密钥 (Base32)", style="bold yellow")
        table.add_column("算法", justify="center")
        table.add_column("位数", justify="center")

        for acc in accounts:
            table.add_row(
                acc['issuer'],
                acc['name'],
                acc['totp_secret'],
                acc['algorithm'],
                acc['digits']
            )

        console.print("\n", table)
        console.print(Panel(
            f"成功解封 [bold green]{len(accounts)}[/] 个账户。\n[red][!] 安全警告：请在完成备份后立即清理剪贴板和终端历史记录。",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]解析失败: [/] {e}")

if __name__ == "__main__":
    main()