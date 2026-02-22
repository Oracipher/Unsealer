# src/unsealer/google/cli.py

import sys
import argparse
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# 内部模块导入
from .decrypter import decrypt_google_auth_uri
from .scanner import extract_uris_from_path

# 初始化控制台（错误流输出，不干扰管道）
console = Console(stderr=True)

def _save_report(accounts, output_path: Path):
    """将结果保存为 Markdown 格式"""
    content = [
        "# Google Authenticator 导出报告",
        f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n| 序号 | 发行者 (Issuer) | 账号名称 (Name) | 密钥 (Base32 Secret) | 算法 | 位数 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for i, acc in enumerate(accounts, 1):
        content.append(
            f"| {i} | {acc['issuer']} | {acc['name']} | `{acc['totp_secret']}` | "
            f"{acc['algorithm']} | {acc['digits']} |"
        )
    
    try:
        output_path.write_text("\n".join(content), encoding="utf-8")
        console.print(f"\n[bold green]✓[/] 报告已成功保存至: [bold magenta]{output_path}[/]")
    except Exception as e:
        console.print(f"[bold red]✗ 无法保存文件:[/bold red] {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Google Authenticator 迁移数据提取工具 (免 Protobuf 编译版)"
    )
    # 接受多个输入：URI 字符串、图片文件或包含二维码的文件夹
    parser.add_argument("inputs", nargs="*", help="URI 字符串、二维码图片路径或目录")
    parser.add_argument("-o", "--output", type=Path, help="导出 Markdown 报告的文件路径")
    
    # 接收来自 __main__.py 的参数分发 (sys.argv[2:])
    args = parser.parse_args(sys.argv[2:])

    final_uris = set()

    # 1. 第一步：处理命令行直接提供的输入
    if args.inputs:
        with console.status("[bold green]正在扫描输入源..."):
            for item in args.inputs:
                if item.startswith("otpauth-migration://"):
                    final_uris.add(item)
                else:
                    # 尝试作为文件路径扫描二维码
                    uris_found = extract_uris_from_path(item)
                    final_uris.update(uris_found)
    
    # 2. 第二步：交互模式（如果没有任何输入）
    if not final_uris:
        console.print(Panel(
            "未检测到输入数据。您可以：\n"
            "1. 直接粘贴 [bold cyan]otpauth-migration://[/] 开头的 URI\n"
            "2. 拖入包含二维码的 [bold cyan]图片文件[/] 或 [bold cyan]目录[/]\n"
            "\n直接按下 [bold yellow]回车[/] 开始解析已输入的数据。", 
            title="[bold cyan]Google Authenticator 提取器", 
            border_style="cyan"
        ))
        
        while True:
            val = Prompt.ask("[bold yellow]输入 URI/路径 (留空结束)[/]").strip()
            if not val:
                break
            if val.startswith("otpauth-migration://"):
                final_uris.add(val)
            else:
                uris_found = extract_uris_from_path(val)
                if uris_found:
                    final_uris.update(uris_found)
                    console.print(f"[dim]已从路径中提取 {len(uris_found)} 个 URI[/dim]")
                else:
                    console.print("[red]未在指定路径发现有效的二维码或 URI。[/red]")

    if not final_uris:
        console.print("[bold red]错误: 没有找到任何可处理的 Google 迁移数据。[/]")
        return

    # 3. 第三步：解密与去重
    all_accounts_map = {}
    try:
        with console.status("[bold green]正在解密多批次数据..."):
            for uri in final_uris:
                accounts = decrypt_google_auth_uri(uri)
                for acc in accounts:
                    # 使用 secret 作为 key 进行去重，防止多次扫描同一二维码
                    all_accounts_map[acc['totp_secret']] = acc

        # 按服务商名称排序
        final_accounts = sorted(all_accounts_map.values(), key=lambda x: x['issuer'].lower())

        # 4. 第四步：展示结果表格
        if not final_accounts:
            console.print("[yellow]解析完成，但未发现有效的账户数据。[/yellow]")
            return

        table = Table(
            title=f"\n成功提取 {len(final_accounts)} 个 2FA 账户", 
            header_style="bold magenta",
            border_style="dim"
        )
        table.add_column("服务商 (Issuer)", style="cyan", no_wrap=True)
        table.add_column("账户名称 (Name)", style="green")
        table.add_column("密钥 (Base32 Secret)", style="bold yellow")
        table.add_column("算法", justify="center")
        
        for acc in final_accounts:
            table.add_row(
                acc['issuer'], 
                acc['name'], 
                acc['totp_secret'], 
                acc['algorithm']
            )
        
        console.print("\n", table)

        # 5. 第五步：执行导出逻辑
        if args.output:
            _save_report(final_accounts, args.output)
        else:
            console.print("\n[dim]提示: 使用 -o 参数可将结果导出为 Markdown 文件。[/dim]")

    except Exception as e:
        console.print(f"[bold red]致命解析错误: [/] {e}")
        console.print("[dim]这可能是由于 URI 格式损坏或协议版本不兼容导致的。[/dim]")

if __name__ == "__main__":
    main()