import sys
import os
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def scan_image(image_path):
    """
    在一张图片中寻找并解码所有二维码
    """
    uris = []
    try:
        # 使用 Pillow 打开图片
        with Image.open(image_path) as img:
            # pyzbar 的 decode 函数天然支持在一张图中识别多个二维码
            decoded_objects = decode(img)
            
            for obj in decoded_objects:
                content = obj.data.decode('utf-8')
                # 过滤出 Google Authenticator 的迁移协议
                if content.startswith("otpauth-migration://"):
                    uris.append(content)
        return uris
    except Exception as e:
        console.print(f"[red]![/] 读取 {image_path.name} 出错: {e}")
        return []

def main():
    if len(sys.argv) < 2:
        console.print("[yellow]用法:[/] python qr_reader.py <图片路径或目录>")
        return

    input_path = Path(sys.argv[1])
    all_found_uris = set() # 使用集合自动去重
    image_stats = {}

    # 确定要处理的文件列表
    if input_path.is_dir():
        files = []
        for ext in ('*.png', '*.jpg', '*.jpeg', '*.bmp'):
            files.extend(input_path.glob(ext))
    elif input_path.is_file():
        files = [input_path]
    else:
        console.print("[bold red]错误:[/] 路径不存在。")
        return

    if not files:
        console.print("[bold yellow]未找到任何图片文件。[/]")
        return

    with console.status("[bold green]正在深度扫描二维码...") as status:
        for f in files:
            found = scan_image(f)
            if found:
                image_stats[f.name] = len(found)
                all_found_uris.update(found)

    # 打印扫描报告
    if image_stats:
        table = Table(title="二维码扫描报告", header_style="bold magenta")
        table.add_column("文件名", style="cyan")
        table.add_column("发现有效二维码数量", justify="center", style="green")
        
        for name, count in image_stats.items():
            table.add_row(name, str(count))
        
        console.print(table)
    else:
        console.print(Panel("[bold red]未在图片中发现任何有效的 Google 迁移二维码。[/]", border_style="red"))
        return

    # 输出提取结果
    console.print(f"\n[bold green]成功提取到 {len(all_found_uris)} 条唯一 URI：[/]\n")
    
    # 打印出来方便复制，或者直接重定向到文件
    for uri in all_found_uris:
        console.print(Panel(uri, subtitle="复制此内容到 unsealer", border_style="blue"))

    console.print("\n[bold yellow]提示:[/] 你可以将这些 URI 逐个（或批量）输入到 [cyan]unsealer google[/] 命令中。")

if __name__ == "__main__":
    main()