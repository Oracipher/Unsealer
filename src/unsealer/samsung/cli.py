# src/unsealer/samsung/cli.py

import argparse
import sys
import csv
import os
import re
import traceback
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
import pyfiglet
from .decrypter import decrypt_and_parse
from typing import Dict, List, Any

# --- Initialize the rich console --- # 
console = Console(stderr=True)

def _format_logins_txt(data: List[Dict]) -> str:
    content = [
        f"====================\n [登录凭证] Logins ({len(data)} 条)\n===================="
    ]
    for i, entry in enumerate(data, 1):
        content.append(f"\n--- [ {i}. {entry.get('title', '未知条目')} ] ---")
        content.append(f"{'用户名:':<10} {entry.get('username_value', 'N/A')}")
        content.append(f"{'密码:':<10} {entry.get('password_value', 'N/A')}")
        if url := entry.get("origin_url"):
            content.append(f"{'网址/应用:':<10} {url}")
        if memo := entry.get("credential_memo"):
            content.append(f"{'备注:':<10} {memo}")
        if isinstance(otp := entry.get("otp"), dict) and otp.get("secret"):
            content.append(f"\n  [!!] 两步验证 (2FA) 密钥:")
            content.append(f"    {'密钥:':<8} {otp.get('secret')}")
            content.append(f"    {'账户:':<8} {otp.get('name', 'N/A')}")
    return "\n".join(content)


def _format_identities_txt(data: List[Dict]) -> str:
    content = [
        f"\n\n=======================\n [身份信息] Identities ({len(data)} 条)\n======================="
    ]
    for i, entry in enumerate(data, 1):
        content.append(f"\n--- [ {i}. {entry.get('name', '未知身份')} ] ---")
        if isinstance(id_card := entry.get("id_card_detail"), dict):
            content.append(f"{'身份证号:':<10} {id_card.get('mIDCardNumber', 'N/A')}")
            content.append(f"{'姓名:':<10} {id_card.get('mUsername', 'N/A')}")
            content.append(f"{'出生日期:':<10} {id_card.get('mBirthDay', 'N/A')}")
        if phones := entry.get("telephone_number_list"):
            content.append(f"{'电话:':<10} {', '.join(phones)}")
        if emails := entry.get("email_address_list"):
            content.append(f"{'邮箱:':<10} {', '.join(emails)}")
    return "\n".join(content)


def _format_addresses_txt(data: List[Dict]) -> str:
    content = [
        f"\n\n=====================\n [地址信息] Addresses ({len(data)} 条)\n====================="
    ]
    for i, entry in enumerate(data, 1):
        name = entry.get("full_name", f"地址 {i}")
        if name == "添加地址/名称":
            name = f"地址 {i} (模板)"
        content.append(f"\n--- [ {i}. {name} ] ---")
        addr_parts = [
            entry.get(k)
            for k in ["street_address", "city", "state", "zipcode", "country_code"]
        ]
        full_address = ", ".join(filter(None, addr_parts))
        if full_address:
            content.append(f"{'地址:':<10} {full_address}")
        if phone := entry.get("phone_number"):
            content.append(f"{'电话:':<10} {phone}")
        if email := entry.get("email"):
            content.append(f"{'邮箱:':<10} {email}")
    return "\n".join(content)


def _format_notes_txt(data: List[Dict]) -> str:
    content = [
        f"\n\n======================\n [安全备忘录] Notes ({len(data)} 条)\n======================"
    ]
    for i, entry in enumerate(data, 1):
        content.append(
            f"\n--- [ {i}. {entry.get('note_title', '无标题备忘录')} ] ---\n"
        )
        content.append(f"{entry.get('note_detail', '')}")
    return "\n".join(content)


# --- Markdown Custom Formatter --- # 
def _format_logins_md(data: List[Dict]) -> str:
    content = [f"## [登录凭证] Logins - 共 {len(data)} 条\n"]
    for i, entry in enumerate(data, 1):
        content.append(f"### {i}. {entry.get('title', '未知条目')}")
        content.append(f"- **用户名**: `{entry.get('username_value', 'N/A')}`")
        content.append(f"- **密码**: `{entry.get('password_value', 'N/A')}`")
        if url := entry.get("origin_url"):
            content.append(f"- **网址/应用**: `{url}`")
        if memo := entry.get("credential_memo"):
            content.append(f"- **备注**: {memo}")
        if isinstance(otp := entry.get("otp"), dict) and otp.get("secret"):
            content.append("- **[!] 两步验证 (2FA) 密钥**: ")
            content.append(f"  - **密钥 (Secret)**: `{otp.get('secret')}`")
            content.append(f"  - **账户**: `{otp.get('name', 'N/A')}`")
        content.append("\n---\n")
    return "\n".join(content)


def _format_identities_md(data: List[Dict]) -> str:
    content = [f"## [身份信息] Identities - 共 {len(data)} 条\n"]
    for i, entry in enumerate(data, 1):
        content.append(f"### {i}. {entry.get('name', '未知身份')}")
        if isinstance(id_card := entry.get("id_card_detail"), dict):
            content.append(f"- **身份证号**: `{id_card.get('mIDCardNumber', 'N/A')}`")
            content.append(f"- **姓名**: `{id_card.get('mUsername', 'N/A')}`")
            content.append(f"- **出生日期**: `{id_card.get('mBirthDay', 'N/A')}`")
        if phones := entry.get("telephone_number_list"):
            content.append(f"- **电话**: {', '.join([f'`{p}`' for p in phones])}")
        if emails := entry.get("email_address_list"):
            content.append(f"- **邮箱**: {', '.join([f'`{e}`' for e in emails])}")
        content.append("\n---\n")
    return "\n".join(content)


def _format_addresses_md(data: List[Dict]) -> str:
    content = [f"## [地址信息] Addresses - 共 {len(data)} 条\n"]
    for i, entry in enumerate(data, 1):
        name = entry.get("full_name", f"地址 {i}")
        if name == "添加地址/名称":
            name = f"地址 {i} (模板)"
        content.append(f"### {i}. {name}")
        addr_parts = [
            entry.get(k)
            for k in ["street_address", "city", "state", "zipcode", "country_code"]
        ]
        full_address = ", ".join(filter(None, addr_parts))
        if full_address:
            content.append(f"- **地址**: {full_address}")
        if phone := entry.get("phone_number"):
            content.append(f"- **电话**: `{phone}`")
        if email := entry.get("email"):
            content.append(f"- **邮箱**: `{email}`")
        content.append("\n---\n")
    return "\n".join(content)


def _format_notes_md(data: List[Dict]) -> str:
    content = [f"## [安全备忘录] Notes - 共 {len(data)} 条\n"]
    for i, entry in enumerate(data, 1):
        content.append(f"### {i}. {entry.get('note_title', '无标题备忘录')}")
        content.append(f"```\n{entry.get('note_detail', '')}\n```")
        content.append("\n---\n")
    return "\n".join(content)


def save_as_md(data: Dict[str, List[Any]], output_file: Path, banner: str):
    MD_FORMATTERS = {
        "logins": _format_logins_md,
        "identities": _format_identities_md,
        "addresses": _format_addresses_md,
        "notes": _format_notes_md,
    }
    ORDER = ["logins", "identities", "addresses", "notes"]
    sorted_tables = sorted(
        data.keys(), key=lambda x: ORDER.index(x) if x in ORDER else len(ORDER)
    )
    with open(output_file, "w", encoding="utf-8") as f:
        if banner:
            clean_banner = banner.strip()
            lines = clean_banner.split('\n')
            if lines:
                lines[0] = "   " + lines[0]
            modified_banner = "\n".join(lines)
            f.write(f"```\n{modified_banner}\n```\n\n")
            
        f.write("# Unsealer 综合解密报告\n\n")
        f.write(f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **数据摘要**: 共找到 **{len(data)}** 个数据类别。\n\n")
        f.write(
            "**[!] 安全警告：此文件包含您的密码、两步验证密钥、身份证号等极度敏感信息，请务必在安全的环境下查看，并妥善保管！**\n\n"
        )
        for table_name in sorted_tables:
            formatter = MD_FORMATTERS.get(table_name)
            if formatter:
                f.write(formatter(data[table_name]))
        f.write(f"\n*报告由 Unsealer (最终设计版) 生成*")


def save_as_txt(data: Dict[str, List[Any]], output_file: Path, banner: str):
    TXT_FORMATTERS = {
        "logins": _format_logins_txt,
        "identities": _format_identities_txt,
        "addresses": _format_addresses_txt,
        "notes": _format_notes_txt,
    }
    ORDER = ["logins", "identities", "addresses", "notes"]
    sorted_tables = sorted(
        data.keys(), key=lambda x: ORDER.index(x) if x in ORDER else len(ORDER)
    )
    with open(output_file, "w", encoding="utf-8") as f:
        if banner:
            f.write(f"{banner}\n")
        f.write("Unsealer 综合解密报告\n")
        f.write("------------------------\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"数据摘要: 共找到 {len(data)} 个数据类别。\n\n")
        f.write("!!!!!!!! 安全警告 !!!!!!!!\n此文件包含极度敏感信息，请妥善保管！\n\n")
        for table_name in sorted_tables:
            formatter = TXT_FORMATTERS.get(table_name)
            if formatter:
                f.write(formatter(data[table_name]))
        f.write(f"\n\n--- 报告结束 ---\n*由 Unsealer (最终设计版) 生成*")


def save_as_csv(data: dict, output_path: Path):
    """
    将每个数据类别保存为独立的CSV文件，并对嵌套数据进行展平处理
    """
    output_path.mkdir(exist_ok=True)

    for table_name, entries in data.items():
        if not entries:
            continue

        all_headers = set()
        flat_data = []
        for entry in entries:
            flat_entry = {}
            for key, value in entry.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_entry[f"{key}_{sub_key}"] = sub_value
                elif isinstance(value, list):
                    flat_entry[key] = "|".join(map(str, value))
                else:
                    flat_entry[key] = value
            all_headers.update(flat_entry.keys())
            flat_data.append(flat_entry)

        file_path = output_path / f"{table_name}.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sorted(list(all_headers)))
            writer.writeheader()
            writer.writerows(flat_data)

def _sanitize_filename(name: str) -> str:
    """
    移除或替换在文件名/目录名中非法的字符
    """
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def _display_banner() -> str:
    plain_banner = pyfiglet.figlet_format("Unsealer", font="slant")
    console.print(
        Panel(
            plain_banner,
            title="[bold white]Unsealer[/bold white]",
            subtitle="[cyan]v3.3 Final Edition[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    return plain_banner


def _setup_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="一个用于解密三星密码本 (.spass) 文件的优雅工具。"
    )
    parser.add_argument("input_file", type=Path, help="输入的 .spass 文件路径。")
    parser.add_argument(
        "-f",
        "--format",
        choices=["md", "txt", "csv"],
        default="md",
        help="输出文件格式 (默认为: md)。",
    )
    parser.add_argument("-o", "--output", type=Path, help="输出文件的路径或目录。")
    parser.add_argument("--preview", action="store_true", help="在终端中预览摘要信息。")
    parser.add_argument(
        "-y", "--force", action="store_true", help="强制覆盖已存在的输出文件或目录。"
    )
    return parser


def _process_decryption(
    args: argparse.Namespace, password: str, plain_banner: str
):
    try:
        file_content = args.input_file.read_bytes()
        with console.status(
            "[bold green]正在解密与深度提炼数据...[/bold green]", spinner="dots"
        ):
            all_tables = decrypt_and_parse(file_content, password)

        TABLE_NAMES = {
            "logins": "登录凭证",
            "identities": "身份信息",
            "addresses": "地址信息",
            "notes": "安全备忘录",
        }
        summary = Text()
        for name, data in all_tables.items():
            display_name = TABLE_NAMES.get(name, "其他数据")
            summary.append(f"✓ [cyan]{display_name}[/cyan]: 找到 {len(data)} 条目\n")

        console.print(
            Panel(
                summary,
                title="[bold green]✓ 解密成功[/bold green]",
                border_style="green",
            )
        )

        if args.preview:
            console.print("[dim]> 预览模式不会保存文件。使用 -f 和 -o 参数导出。[/dim]")
            return

        console.print(
            f"[cyan]> [/cyan]正在保存到 [bold magenta]{args.output}[/bold magenta] (格式: [yellow]{args.format.upper()}[/yellow])..."
        )

        save_dispatch = {
            "md": lambda data, path, banner: save_as_md(data, path, banner),
            "txt": lambda data, path, banner: save_as_txt(data, path, banner),
            "csv": lambda data, path, banner: save_as_csv(
                data, path
            ),
        }
        save_dispatch[args.format](all_tables, args.output, plain_banner)

        console.print(
            f"\n[bold green]✓ 操作成功！[/bold green] 数据已保存至 [bold magenta]{args.output}[/bold magenta]"
        )

    except (FileNotFoundError, ValueError) as e:
        console.print(f"[bold red]✗ 错误:[/bold red] {e}")
        sys.exit(1)
    except Exception:
        console.print(
            f"[bold red]✗ 发生未知内部错误。[/bold red] 详情已记录到 `unsealer_error.log` 文件中。"
        )
        with open("unsealer_error.log", "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            traceback.print_exc(file=f)
            f.write("\n")
        sys.exit(1)


def main():
    plain_banner = _display_banner()
    parser = _setup_arg_parser()
    
    args = parser.parse_args(sys.argv[2:])

    password = Prompt.ask(
        "[bold yellow]> [/bold yellow]请输入您的三星账户主密码", password=True
    )

    if not args.output and not args.preview:
        if args.format == "csv":
            sanitized_stem = _sanitize_filename(args.input_file.stem)
            args.output = Path(f"{sanitized_stem}_csv_export")
        else:
            args.output = args.input_file.with_suffix(f".{args.format}")

    if args.output and not args.preview and not args.force:
        if args.output.exists():
            if args.format == "csv" and args.output.is_dir():
                if any(args.output.iterdir()):
                    console.print(
                        f"[bold red]✗ 错误:[/bold red] 输出目录 '{args.output}' 已存在且非空。"
                    )
                    console.print(f"请使用 '-y' 或 '--force' 标志进行覆盖。")
                    sys.exit(1)
            elif args.output.is_file():
                console.print(
                    f"[bold red]✗ 错误:[/bold red] 输出文件 '{args.output}' 已存在。"
                )
                console.print(f"请使用 '-y' 或 '--force' 标志进行覆盖。")
                sys.exit(1)

    _process_decryption(args, password, plain_banner)


if __name__ == "__main__":
    main()