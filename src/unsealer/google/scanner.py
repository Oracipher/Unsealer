import os
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode
from typing import Set

def extract_uris_from_path(path_str: str) -> Set[str]:
    """
    扫描路径下的所有二维码图片，提取迁移 URI
    """
    found_uris = set()
    path = Path(path_str)
    
    if not path.exists():
        return found_uris

    # 扫描支持的格式
    exts = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    files = [path] if path.is_file() else list(path.iterdir())
    
    for f in files:
        if f.suffix.lower() not in exts:
            continue
        try:
            with Image.open(f) as img:
                # 预处理：提高黑白对比度有助于扫码
                decoded = decode(img.convert('L'))
                for obj in decoded:
                    content = obj.data.decode('utf-8')
                    if content.startswith("otpauth-migration://"):
                        found_uris.add(content)
        except Exception:
            continue
            
    return found_uris