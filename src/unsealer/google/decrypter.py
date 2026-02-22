import base64
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any

def _parse_varint(data, pos):
    """解析 Protobuf 的 Varint 编码"""
    res = 0
    shift = 0
    while True:
        b = data[pos]
        res |= (b & 0x7f) << shift
        pos += 1
        if not (b & 0x80):
            return res, pos
        shift += 7

def _parse_message(data):
    """简易 Protobuf 逻辑解析器：将二进制流解析为 Tag 字典"""
    pos = 0
    res = {}
    while pos < len(data):
        tag_and_type, pos = _parse_varint(data, pos)
        tag = tag_and_type >> 3
        wire_type = tag_and_type & 0x07
        
        if wire_type == 0:  # Varint
            val, pos = _parse_varint(data, pos)
        elif wire_type == 2:  # Length-delimited (String/Bytes/Nested)
            l, pos = _parse_varint(data, pos)
            val = data[pos:pos+l]
            pos += l
        else:
            raise ValueError(f"Unsupported wire type: {wire_type}")
        
        if tag not in res:
            res[tag] = []
        res[tag].append(val)
    return res

def decrypt_google_auth_uri(uri: str) -> List[Dict[str, Any]]:
    """
    不需要 pb2 文件的 Google 迁移 URI 解析器
    """
    try:
        parsed_uri = urlparse(uri)
        query_params = parse_qs(parsed_uri.query)
        encoded_data = query_params.get('data', [''])[0]
        
        # 1. Base64 解码
        missing_padding = len(encoded_data) % 4
        if missing_padding:
            encoded_data += '=' * (4 - missing_padding)
        binary_payload = base64.b64decode(encoded_data)

        # 2. 解析外层 MigrationPayload
        # Tag 1: repeated OtpParameters otp_parameters
        payload_dict = _parse_message(binary_payload)
        otp_params_list = payload_dict.get(1, [])

        # 3. 映射表
        ALGO_MAP = {0: "SHA1", 1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}
        
        accounts = []
        for raw_otp in otp_params_list:
            # 解析内层 OtpParameters 消息
            otp_dict = _parse_message(raw_otp)
            
            # 提取字段 (Tag 对应 .proto 文件中的序号)
            # 1: secret, 2: name, 3: issuer, 4: algorithm, 5: digits, 6: type
            secret = otp_dict.get(1, [b''])[0]
            name = otp_dict.get(2, [b'Unknown'])[0].decode('utf-8')
            issuer = otp_dict.get(3, [b''])[0].decode('utf-8')
            algo_idx = otp_dict.get(4, [1])[0]
            digit_idx = otp_dict.get(5, [1])[0]

            # 转换 Secret 为 Base32
            b32_secret = base64.b32encode(secret).decode('utf-8').rstrip('=')
            
            # 处理 Issuer 逻辑
            if not issuer and ":" in name:
                issuer = name.split(":", 1)[0].strip()
                name = name.split(":", 1)[1].strip()

            accounts.append({
                "issuer": issuer or "Unknown",
                "name": name,
                "totp_secret": b32_secret,
                "algorithm": ALGO_MAP.get(algo_idx, "SHA1"),
                "digits": "8" if digit_idx == 2 else "6"
            })

        return accounts
    except Exception as e:
        raise ValueError(f"Manual parsing failed: {str(e)}")