import base64
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any

from google.protobuf import descriptor_pb2
from google.protobuf import message_factory
from google.protobuf import descriptor_pool

def _get_dynamic_payload_class():
    """
    基于最新的 google_auth.proto 规范动态构建消息类。
    不再依赖外部生成的 _pb2.py 文件，确保跨环境兼容性。
    """
    pool = descriptor_pool.Default()
    try:
        return message_factory.GetMessageClass(pool.FindMessageTypeByName('googleauth.MigrationPayload'))
    except KeyError:
        pass

    # 手动定义描述符，匹配 proto3 规范
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "google_auth.proto"
    file_descriptor_proto = file_proto
    file_descriptor_proto.package = "googleauth"
    file_descriptor_proto.syntax = "proto3"

    # 定义 MigrationPayload 消息
    msg = file_descriptor_proto.message_type.add()
    msg.name = "MigrationPayload"

    # 定义内部 OtpParameters 消息
    inner_msg = msg.nested_type.add()
    inner_msg.name = "OtpParameters"
    
    # 字段定义 (名称, 编号, 类型) - 类型参考: 12=Bytes, 9=String, 14=Enum, 3=Int64
    fields = [
        ("secret", 1, 12), ("name", 2, 9), ("issuer", 3, 9),
        ("algorithm", 4, 14), ("digits", 5, 14), ("type", 6, 14),
        ("counter", 7, 3), ("unique_id", 8, 9)
    ]
    for f_name, f_num, f_type in fields:
        f = inner_msg.field.add()
        f.name, f.number, f.type = f_name, f_num, f_type

    # MigrationPayload 主字段
    f = msg.field.add()
    f.name, f.number, f.label, f.type, f.type_name = "otp_parameters", 1, 3, 11, ".googleauth.MigrationPayload.OtpParameters"
    
    for i, (f_name, f_type) in enumerate([("version", 5), ("batch_size", 5), ("batch_index", 5), ("batch_id", 5)], 2):
        f = msg.field.add()
        f.name, f.number, f.label, f.type = f_name, i, 1, f_type

    pool.Add(file_descriptor_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName('googleauth.MigrationPayload'))

def decrypt_google_auth_uri(uri: str) -> List[Dict[str, Any]]:
    """
    解析 otpauth-migration URI 并提取 2FA 账户
    """
    parsed_uri = urlparse(uri)
    if parsed_uri.scheme != 'otpauth-migration':
        raise ValueError("无效的 URI 协议，请提供以 'otpauth-migration://' 开头的链接。")

    query_params = parse_qs(parsed_uri.query)
    data_list = query_params.get('data')
    if not data_list:
        raise ValueError("URI 中缺失关键的 'data' 参数。")

    # 处理 Base64
    encoded_data = data_list[0]
    padding_needed = len(encoded_data) % 4
    if padding_needed:
        encoded_data += '=' * (4 - padding_needed)
    
    binary_data = base64.b64decode(encoded_data)

    # 动态解析
    PayloadClass = _get_dynamic_payload_class()
    payload = PayloadClass()
    payload.ParseFromString(binary_data)

    # 映射表 (基于 google_auth.proto)
    ALGO_MAP = {0: "UNSPECIFIED", 1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}
    DIGIT_MAP = {0: "UNSPECIFIED", 1: "6", 2: "8", 3: "7"}
    TYPE_MAP = {0: "UNSPECIFIED", 1: "HOTP", 2: "TOTP"}

    accounts = []
    for otp in payload.otp_parameters:
        # 将原始二进制密钥转换为通用的 Base32 编码
        b32_secret = base64.b32encode(otp.secret).decode('utf-8').rstrip('=')
        
        accounts.append({
            "issuer": otp.issuer or "Unknown Issuer",
            "name": otp.name or "Unknown Account",
            "totp_secret": b32_secret,
            "algorithm": ALGO_MAP.get(otp.algorithm, "SHA1"),
            "digits": DIGIT_MAP.get(otp.digits, "6"),
            "type": TYPE_MAP.get(otp.type, "TOTP")
        })

    return accounts