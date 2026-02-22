import base64
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any

from google.protobuf import descriptor_pb2
from google.protobuf import message_factory
from google.protobuf import descriptor_pool

def _get_dynamic_payload_class():
    """
    动态构建 MigrationPayload 类。
    将枚举字段声明为 Int32，以绕过 Python 3.12 对枚举定义的严格校验，
    同时保持二进制层面的完全兼容。
    """
    pool = descriptor_pool.Default()
    try:
        return message_factory.GetMessageClass(pool.FindMessageTypeByName('googleauth.MigrationPayload'))
    except KeyError:
        pass

    file_descriptor_proto = descriptor_pb2.FileDescriptorProto()
    file_descriptor_proto.name = "google_auth.proto"
    file_descriptor_proto.package = "googleauth"
    file_descriptor_proto.syntax = "proto3"

    # 1. 定义 MigrationPayload 消息
    msg = file_descriptor_proto.message_type.add()
    msg.name = "MigrationPayload"

    # 2. 定义内部 OtpParameters 消息
    inner_msg = msg.nested_type.add()
    inner_msg.name = "OtpParameters"
    
    # 字段定义：将 Enum (14) 全部改为 Int32 (5)，这是解决报错的关键
    # 编号参考: 12=Bytes, 9=String, 5=Int32, 3=Int64
    fields = [
        ("secret", 1, 12), 
        ("name", 2, 9), 
        ("issuer", 3, 9),
        ("algorithm", 4, 5), # 改为 Int32
        ("digits", 5, 5),    # 改为 Int32
        ("type", 6, 5),      # 改为 Int32
        ("counter", 7, 3), 
        ("unique_id", 8, 9)
    ]
    for f_name, f_num, f_type in fields:
        f = inner_msg.field.add()
        f.name, f.number, f.type = f_name, f_num, f_type

    # 3. 关联主消息字段
    f = msg.field.add()
    f.name, f.number, f.label, f.type, f.type_name = "otp_parameters", 1, 3, 11, ".googleauth.MigrationPayload.OtpParameters"
    
    # 其他元数据字段
    for i, f_name in enumerate(["version", "batch_size", "batch_index", "batch_id"], 2):
        f = msg.field.add()
        f.name, f.number, f.label, f.type = f_name, i, 1, 5

    # 4. 载入描述符池
    pool.Add(file_descriptor_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName('googleauth.MigrationPayload'))

def decrypt_google_auth_uri(uri: str) -> List[Dict[str, Any]]:
    """
    解析 otpauth-migration URI
    """
    try:
        parsed_uri = urlparse(uri)
        if parsed_uri.scheme != 'otpauth-migration':
            raise ValueError("无效的 URI 协议。")

        query_params = parse_qs(parsed_uri.query)
        data_list = query_params.get('data')
        if not data_list:
            raise ValueError("URI 中缺失 data 参数。")

        encoded_data = data_list[0]
        # 自动处理 Base64 填充
        padding_needed = len(encoded_data) % 4
        if padding_needed:
            encoded_data += '=' * (4 - padding_needed)
        
        binary_data = base64.b64decode(encoded_data)

        # 动态解析
        PayloadClass = _get_dynamic_payload_class()
        payload = PayloadClass()
        payload.ParseFromString(binary_data)

        # 映射逻辑（基于 proto3 规范）
        ALGO_MAP = {0: "UNSPECIFIED", 1: "SHA1", 2: "SHA256", 3: "SHA512", 4: "MD5"}
        DIGIT_MAP = {0: "UNSPECIFIED", 1: "6", 2: "8", 3: "7"}
        TYPE_MAP = {0: "UNSPECIFIED", 1: "HOTP", 2: "TOTP"}

        # accounts = []
        # for otp in payload.otp_parameters:
        #     # 转换密钥为 Base32
        #     b32_secret = base64.b32encode(otp.secret).decode('utf-8').rstrip('=')
            
        #     accounts.append({
        #         "issuer": otp.issuer or "Unknown",
        #         "name": otp.name or "Unknown",
        #         "totp_secret": b32_secret,
        #         "algorithm": ALGO_MAP.get(otp.algorithm, "SHA1"),
        #         "digits": DIGIT_MAP.get(otp.digits, "6"),
        #         "type": TYPE_MAP.get(otp.type, "TOTP")
        #     })
        accounts = []
        for otp in payload.otp_parameters:
            # --- 智能字段解析开始 ---
            raw_name = otp.name or ""
            raw_issuer = otp.issuer or ""
            
            # 逻辑 1：如果 issuer 为空，尝试从 name 中提取（处理 GitHub:user 这种格式）
            if not raw_issuer and ":" in raw_name:
                display_issuer = raw_name.split(":", 1)[0].strip()
                display_name = raw_name.split(":", 1)[1].strip()
            else:
                display_issuer = raw_issuer
                display_name = raw_name

            # 逻辑 2：双重回退机制
            # 如果解析后 issuer 还是空，用 name 补位
            final_issuer = display_issuer or display_name or "Unknown Issuer"
            # 如果 name 为空，用 issuer 补位
            final_name = display_name or display_issuer or "Unknown Account"
            
            # 如果两者完全一样（说明数据里只有一个字段），为了美观，我们可以微调
            if final_issuer == final_name:
                final_name = "-" # 或者保持原样
            # --- 智能字段解析结束 ---

            b32_secret = base64.b32encode(otp.secret).decode('utf-8').rstrip('=')
            
            accounts.append({
                "issuer": final_issuer,
                "name": final_name,
                "totp_secret": b32_secret,
                "algorithm": ALGO_MAP.get(otp.algorithm, "SHA1"),
                "digits": DIGIT_MAP.get(otp.digits, "6"),
                "type": TYPE_MAP.get(otp.type, "TOTP")
            })

        return accounts
    except Exception as e:
        # 向上传递更清晰的错误信息
        raise ValueError(str(e))