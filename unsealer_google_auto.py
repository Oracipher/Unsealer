import sys
import os
from pathlib import Path
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 确保可以导入 unsealer 模块
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from unsealer.google.decrypter import decrypt_google_auth_uri
except ImportError:
    print("错误：无法找到 unsealer 模块。请确保此脚本放在项目根目录下。")
    sys.exit(1)

console = Console()

def extract_uris_from_images(folder_path):
    """扫描文件夹中所有图片，提取并合并所有唯一 URI"""
    found_uris = set()
    extensions = ('*.png', '*.jpg', '*.jpeg', '*.bmp')
    path = Path(folder_path)
    
    image_files = []
    if path.is_file():
        image_files = [path]
    else:
        for ext in extensions:
            image_files.extend(path.glob(ext))

    if not image_files:
        return []

    with console.status("[bold green]正在从图片中提取二维码数据...") as status:
        for img_file in image_files:
            try:
                with Image.open(img_file) as img:
                    decoded = decode(img)
                    for obj in decoded:
                        content = obj.data.decode('utf-8')
                        if content.startswith("otpauth-migration://"):
                            found_uris.add(content)
            except Exception as e:
                console.print(f"[red]![/] 处理 {img_file.name} 失败: {e}")
    
    return list(found_uris)

def save_to_file(accounts):
    """将结果保存为 Markdown 格式的文本文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"google_auth_export_{timestamp}.md"
    
    content = [
        "# Google Authenticator 解密导出报告",
        f"- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **账号总数**: {len(accounts)}",
        "\n> [!] **安全警告**: 此文件包含极度敏感的 2FA 密钥。请务必妥善保管，并在完成迁移后彻底删除此文件。\n",
        "| 服务商 (Issuer) | 账号名称 (Name) | TOTP 密钥 (Secret) | 算法/位数 |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    for acc in accounts:
        config = f"{acc['algorithm']}/{acc['digits']}位"
        content.append(f"| {acc['issuer']} | {acc['name']} | `{acc['totp_secret']}` | {config} |")
    
    content.append("\n\n--- \n*由 Unsealer 全自动导出工具生成*")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    
    return filename

def main():
    if len(sys.argv) < 2:
        console.print("[yellow]用法:[/] python unsealer_google_auto.py <图片文件夹路径>")
        return

    folder_path = sys.argv[1]
    
    # 1. 提取所有 URI
    uris = extract_uris_from_images(folder_path)
    if not uris:
        console.print(Panel("[bold red]未发现有效的 Google 迁移二维码数据。[/]", border_style="red"))
        return

    # 2. 解密并整合
    all_accounts_map = {}
    try:
        with console.status("[bold green]正在解密所有批次并整合数据...") as status:
            for uri in uris:
                accounts = decrypt_google_auth_uri(uri)
                for acc in accounts:
                    all_accounts_map[acc['totp_secret']] = acc

        final_accounts = sorted(all_accounts_map.values(), key=lambda x: x['issuer'].lower())

        # 3. 终端展示
        table = Table(title=f"解密成功: 共 {len(final_accounts)} 个账户", header_style="bold magenta", border_style="green")
        table.add_column("服务商", style="cyan")
        table.add_column("账号名称", style="green")
        table.add_column("密钥", style="bold yellow")
        for acc in final_accounts:
            table.add_row(acc['issuer'], acc['name'], acc['totp_secret'])
        console.print("\n", table)

        # 4. 自动保存为文件 (核心改进点)
        output_file = save_to_file(final_accounts)
        
        console.print(Panel(
            f"数据整合完成！\n\n[bold green]✓[/] 终端已展示预览。\n[bold green]✓[/] 完整数据已自动保存至文件: [bold magenta]{output_file}[/]\n\n[red][!] 请注意：处理完此文件后请务必将其安全删除。",
            title="[bold green]操作成功",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]解析过程中出现错误: [/] {e}")

if __name__ == "__main__":
    main()