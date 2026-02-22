# src\unsealer\samsung\decrypter.py

import base64
import hashlib
import csv
import io
import re
import json
import sys
import binascii
from typing import List, Dict, Any, Union
from pathlib import Path

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    print("错误：核心加密库 'pycryptodome' 未安装。请运行 'pip install pycryptodome'。")
    raise

# --- 从外部文件加载解析规则 ---
try:
    SCHEMA_PATH = Path(__file__).parent / "schema.json"
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        TABLE_SCHEMA = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"致命错误：无法加载或解析 schema.json 文件。程序无法继续。错误：{e}", file=sys.stderr)
    sys.exit(1)


# --- 加密参数常量 ---
# 将“魔法数字”定义为常量，增强代码的可读性和可维护性
SALT_SIZE = 20
IV_SIZE = 16  # AES-128/256 CBC IV 长度为 16 字节
KEY_SIZE = 32  # AES-256 密钥长度为 32 字节

# PBKDF2的迭代次数 (70000) 由三星的加密标准决定，必须使用此数值才能成功解密
PBKDF2_ITERATIONS = 70000


# --- 辅助解析函数 ---


def _safe_b64_decode(b64_string: str) -> str:
    if not b64_string or b64_string.strip() in ["", "JiYmTlVMTCYmJg=="]:
        return ""
    try:
        return base64.b64decode(b64_string).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return b64_string


def _parse_json_field(field_value: str) -> Union[Dict, str]:
    try:
        cleaned_value = field_value.replace('\\"', '"').strip()
        if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
            cleaned_value = cleaned_value[1:-1]
        return json.loads(cleaned_value)
    except (json.JSONDecodeError, TypeError):
        return field_value


def _parse_multi_b64_field(field_value: str) -> List[str]:
    if not field_value:
        return []
    decoded_parts = []
    parts = field_value.split("&&&")
    for part in parts:
        if not part:
            continue
        b64_part = part.split("#")[0]
        decoded = _safe_b64_decode(b64_part)
        if decoded:
            decoded_parts.append(decoded)
    return decoded_parts


def clean_android_url(url: str) -> str:
    if not url or re.search(r"\.[a-zA-Z]{2,}", url) or url.startswith("http"):
        return url
    if url.startswith("android://"):
        try:
            return url.split("@")[-1]
        except Exception:
            return url
    return url


# --- 核心解析逻辑 ---


def parse_decrypted_content(decrypted_content: str) -> Dict[str, List[Dict[str, Any]]]:
    all_tables: Dict[str, List[Dict[str, Any]]] = {}
    blocks = decrypted_content.split("next_table")
    unknown_table_count = 0

    for block_index, block in enumerate(blocks):
        clean_block = block.strip()
        if not clean_block or clean_block.count(";") < 2:
            continue

        try:
            reader = csv.DictReader(io.StringIO(clean_block), delimiter=";")
            headers = reader.fieldnames
            if not headers:
                continue

            table_name = None
            schema = {}
            for name, sch in TABLE_SCHEMA.items():
                if all(fp in headers for fp in sch.get("fingerprint", [])):
                    table_name = name
                    schema = sch
                    break

            if not table_name:
                if "24" in headers and len(headers) == 1:
                    continue
                unknown_table_count += 1
                table_name = f"unknown_data_{unknown_table_count}"
                schema = {"useful_fields": headers}

            table_entries: List[Dict[str, Any]] = []
            for row in reader:
                entry = {}
                for field in schema.get("useful_fields", []):
                    raw_value_pre = row.get(field)
                    if raw_value_pre is None:
                        continue

                    raw_value = _safe_b64_decode(raw_value_pre)
                    if not raw_value:
                        continue

                    if field in schema.get("json_fields", []):
                        entry[field] = _parse_json_field(raw_value)
                    elif field in schema.get("multi_b64_fields", []):
                        entry[field] = _parse_multi_b64_field(raw_value)
                    elif field == "origin_url":
                        entry[field] = clean_android_url(raw_value)
                    else:
                        entry[field] = raw_value

                if entry:
                    table_entries.append(entry)

            if table_entries:
                all_tables[table_name] = table_entries
        except Exception as e:
            print(
                f"警告: 解析数据块 #{block_index} 时出现问题并已跳过。错误: {e}",
                file=sys.stderr,
            )
            continue

    if not all_tables:
        raise ValueError("解密成功，但在文件中未找到任何有价值的数据。")

    return all_tables


def decrypt_and_parse(
    file_content_bytes: bytes, password: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    主解密函数
    """
    try:
        binary_data = base64.b64decode(file_content_bytes.decode("utf-8").strip())

        salt_end = SALT_SIZE
        iv_end = salt_end + IV_SIZE

        salt, iv, encrypted_data = (
            binary_data[:salt_end],
            binary_data[salt_end:iv_end],
            binary_data[iv_end:],
        )

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
            dklen=KEY_SIZE,
        )

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = unpad(
            cipher.decrypt(encrypted_data), AES.block_size, style="pkcs7"
        )

        return parse_decrypted_content(decrypted_data.decode("utf-8"))

    except (ValueError, binascii.Error):
        raise ValueError(
            "解密失败。请仔细检查您的密码是否正确，并确认文件是有效的三星密码本备份。"
        )
    except Exception as e:
        raise ValueError("解密或解析过程中发生未知内部错误。文件可能已损坏。") 