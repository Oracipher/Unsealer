# src\unsealer\google\decrypter.py



import base64
import binascii
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any

from . import google_auth_pb2


def decrypt_google_auth_uri(uri: str) -> List[Dict[str, Any]]:
    """
    解码Google Authenticator导出的URI，并提取所有2FA账户信息
    Args:
        uri: 从Google Authenticator二维码扫描得到的完整 'otpauth-migration://...' 字符串
    Returns:
        一个包含字典的列表，每个字典代表一个2FA账户，包含
        issuer, name, 和最重要的 totp_secret (Base32编码)
    Raises:
        ValueError: 如果URI无效、数据损坏或解析过程中出现任何错误
    """
    try:
        # 1. URI解析与验证
        parsed_uri = urlparse(uri)
        if parsed_uri.scheme != 'otpauth-migration' or parsed_uri.netloc != 'offline':
            raise ValueError("无效的URI格式，必须以 'otpauth-migration://offline' 开头。")

        query_params = parse_qs(parsed_uri.query)
        if 'data' not in query_params:
            raise ValueError("URI中未找到 'data' 参数。")
        
        encoded_data = query_params['data'][0]

        # 2. Base64解码 -> 获取二进制Protobuf数据
        padding_needed = len(encoded_data) % 4
        if padding_needed:
            encoded_data += '=' * (4 - padding_needed)
        
        binary_data = base64.b64decode(encoded_data)

        # 3. Protocol Buffers (Protobuf) 反序列化
        payload = google_auth_pb2.MigrationPayload()
        payload.ParseFromString(binary_data)

        # 4. 账户数据处理与转换
        accounts = []
        for otp_param in payload.otp_parameters:
            # 将Protobuf中的原始二进制密钥(secret)转换为标准的Base32字符串
            secret_bytes = otp_param.secret
            # 使用标准的b32encode，并移除末尾的填充'='，这是TOTP密钥的常见格式
            totp_secret = base64.b32encode(secret_bytes).decode('utf-8').rstrip('=')

            # 将Protobuf的枚举值转换为人类可读的字符串，便于后续使用
            algo_map = {0: "SHA1", 1: "SHA1", 2: "SHA256", 4: "MD5"}
            digit_map = {0: 6, 1: 6, 2: 8}
            type_map = {0: "TOTP", 2: "TOTP"}

            account = {
                "issuer": otp_param.issuer,
                "name": otp_param.name,
                "totp_secret": totp_secret,
                "algorithm": algo_map.get(otp_param.algorithm, "UNKNOWN"),
                "digits": digit_map.get(otp_param.digits, 6),
                "type": type_map.get(otp_param.type, "UNKNOWN"),
            }
            accounts.append(account)

        if not accounts:
            raise ValueError("解密成功，但未在数据中找到任何账户信息。")

        return accounts

    except (binascii.Error, ValueError) as e:
        # 捕获Base64解码错误或我们自己抛出的ValueError
        raise ValueError(f"解码失败: {e}")
    except Exception as e:
        # 捕获所有其他异常，如Protobuf解析错误
        raise ValueError(f"处理Google Authenticator数据时发生未知错误。数据可能已损坏或格式不兼容。错误: {e}")


# 如果直接运行此文件，可以进行快速测试
if __name__ == '__main__':
    # 提供一个示例URI
    TEST_URI = "otpauth-migration://offline?data=CjEKCkhlbGxvId6tvu8SGEV4YW1wbGU6YWxpY2VAZ21haWwuY29tGAEgASgLMgtFeGFtcGxlOkNvZGUaGEV4YW1wbGU6YWxpY2VAZ21haWwuY29tIAEoATACEAEYASAA"
    
    print("--- 正在测试 Google Authenticator 解密模块 ---")
    
    try:
        extracted_accounts = decrypt_google_auth_uri(TEST_URI)
        print(f"\n[✓] 解密成功！找到 {len(extracted_accounts)} 个账户:")
        
        for i, acc in enumerate(extracted_accounts, 1):
            print(f"\n--- 账户 #{i} ---")
            print(f"  服务商 (Issuer): {acc['issuer']}")
            print(f"  账户名 (Name):    {acc['name']}")
            print(f"  TOTP 密钥:       {acc['totp_secret']}  <-- 这是您需要备份的密钥!")
            print(f"  算法:            {acc['algorithm']}")
            print(f"  位数:            {acc['digits']}")

    except ValueError as e:
        print(f"\n[✗] 测试失败: {e}")