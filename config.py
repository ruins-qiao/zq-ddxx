import os

# 从环境变量中读取配置，如果环境变量不存在，则使用默认值 None
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
user_session = os.getenv('USER_SESSION', 'user_session') # 为session提供一个默认名

# 监控的群组ID，以逗号分隔，例如 "12345,67890"
group_str = os.getenv('GROUP_IDS', '')
group = [int(g) for g in group_str.split(',') if g] # 转换为整数列表

# 监控的朱雀群组ID
zq_group_str = os.getenv('ZQ_GROUP_IDS', '')
zq_group = [int(g) for g in zq_group_str.split(',') if g] # 转换为整数列表

# 类型转换和默认值
zq_bot = int(os.getenv('ZQ_BOT', ''))
user = int(os.getenv('USER_ID', ''))
name = os.getenv('NAME', '')
top = int(os.getenv('TOP', ''))

# 账户余额API配置
ZHUQUE_COOKIE = os.getenv('ZHUQUE_COOKIE')
ZHUQUE_X_CSRF = os.getenv('ZHUQUE_X_CSRF')
ZHUQUE_API_URL = os.getenv('ZHUQUE_API_URL')

# 检查必要的环境变量是否已设置
if not all([api_id, api_hash, ZHUQUE_COOKIE, ZHUQUE_X_CSRF, ZHUQUE_API_URL]):
    raise ValueError("请设置所有必要的环境变量: API_ID, API_HASH, ZHUQUE_COOKIE, ZHUQUE_X_CSRF, ZHUQUE_API_URL")