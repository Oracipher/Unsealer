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
    parser.add_argument("uris", nargs="*", help="一个或多个 otpauth-migration:// 链接")
    args = parser.parse_args(sys.argv[2:])

    input_uris = args.uris
    
    # 交互模式：如果命令行没给 URI，就循环询问，直到用户输入空行为止
    if not input_uris:
        console.print(Panel("请依次粘贴所有二维码的 URI 文本。\n全部粘贴完后，直接按 [回车] 开始解析。", 
                            title="[bold cyan]Google 多批次模式", border_style="cyan"))
        while True:
            uri = Prompt.ask("[bold yellow]输入 URI (留空结束)[/]")
            if not uri.strip():
                break
            input_uris.append(uri.strip())

    if not input_uris:
        console.print("[bold red]错误: [/] 未提供任何 URI。")
        return

    all_accounts = []
    try:
        with console.status("[bold green]正在处理所有批次..."):
            for uri in input_uris:
                accounts = decrypt_google_auth_uri(uri)
                all_accounts.extend(accounts)

        # 去重（根据密钥去重，防止用户重复扫描同一个二维码）
        unique_accounts = {acc['totp_secret']: acc for acc in all_accounts}.values()
        
        table = Table(title=f"成功提取: {len(unique_accounts)} 个账户", show_header=True, header_style="bold magenta")
        table.add_column("服务商", style="cyan")
        table.add_column("账号名称", style="green")
        table.add_column("TOTP 密钥 (Base32)", style="bold yellow")
        table.add_column("算法")

        for acc in sorted(unique_accounts, key=lambda x: x['issuer']):
            table.add_row(acc['issuer'], acc['name'], acc['totp_secret'], acc['algorithm'])

        console.print("\n", table)
        
    except Exception as e:
        console.print(f"[bold red]解析失败: [/] {e}")

if __name__ == "__main__":
    main()