from telethon import TelegramClient, events, functions
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import config
import zq
import logging

# 2. 创建 Telegram 客户端
client = TelegramClient(config.user_session, config.api_id, config.api_hash)
# 程序启动时 创建数据库
zq.create_table_if_not_exists()
# 创建去重器
deduplicator = zq.MessageDeduplicator(time_window=5.0)


@client.on(
    events.NewMessage(chats=config.zq_group, pattern=r"内容: (.*)\n灵石: .*\n剩余: .*\n大善人: (.*)",
                      from_users=config.zq_bot))
async def zq_red_packet_handler(event):
    await zq.qz_red_packet(client, event, functions)


@client.on(
    events.NewMessage(chats=config.zq_group, pattern=r"\[近 40 次结果\]\[由近及远\]\[0 小 1 大\].*",
                      from_users=config.zq_bot))
async def zq_bet_on_handler(event):
    await zq.zq_bet_on(client, event, deduplicator)


@client.on(
    events.NewMessage(chats=config.zq_group, pattern=r"已结算: 结果为 (\d+) ([大|小])", from_users=config.zq_bot))
async def zq_settle_handler(event):
    await zq.zq_settle(client, event)


@client.on(
    events.NewMessage(chats=config.group))
async def zq_user_handler(event):
    await zq.zq_user(client, event)


@client.on(
    events.NewMessage(chats=config.zq_group, pattern=r"转账成功.*", from_users=config.zq_bot))
async def zq_shoot_handler(event):
    await zq.zq_shoot(client, event)




# 启动客户端
print("正在连接到 Telegram...")
client.start()
print("客户端已启动，正在监听指定群组消息...")
# ================== 新增代码开始 ==================
# # --- 1. 配置日志 (新增) ---
# # 这会自动创建一个名为 bot_debug.log 的文件
# logging.basicConfig(
#     filename='bot_debug.log',
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# # --- 2. 配置区域 ---
# LATENCY_OFFSET = 0.4
# TARGET_GROUP = -1002346599496  # 替换你的群组ID
# MESSAGE_TEXT = "服务器日志测试 - 祝OurBits9周年快乐！"
#
#
# # --- 3. 测试版发送函数 (写入日志) ---
# async def sniper_send_msg():
#     try:
#         # 1. 获取时间
#         now = datetime.now(pytz.timezone('Asia/Shanghai'))
#         # 测试模式：目标是下一分钟的第0秒
#         target_time = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
#
#         # 2. 计算开火时间
#         fire_time = target_time - timedelta(seconds=LATENCY_OFFSET)
#
#         # 3. 计算等待
#         current_now = datetime.now(pytz.timezone('Asia/Shanghai'))
#         wait_seconds = (fire_time - current_now).total_seconds()
#
#         if wait_seconds > 0:
#             # 记录日志：准备等待
#             logging.info(f"[准备] 目标: {target_time.strftime('%H:%M:%S')} | 需等待: {wait_seconds:.3f}s")
#             await asyncio.sleep(wait_seconds)
#
#         # 4. 发送
#         await client.send_message(TARGET_GROUP, MESSAGE_TEXT)
#
#         # 记录日志：发送成功实际时间
#         real_time = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%H:%M:%S.%f')
#         logging.info(f"[成功] 消息已发出 | 实际上链时间: {real_time}")
#
#     except Exception as e:
#         # 记录日志：报错
#         logging.error(f"[错误] 发送失败: {str(e)}")
#
#
# # --- 4. 调度器服务 ---
# async def start_scheduler_service():
#     scheduler = AsyncIOScheduler()
#     tz_shanghai = pytz.timezone('Asia/Shanghai')
#
#     # 测试模式：每分钟的第55秒唤醒
#     scheduler.add_job(
#         sniper_send_msg,
#         trigger=CronTrigger(
#
#             second='55', timezone=tz_shanghai)
#     )
#
#     scheduler.start()
#     logging.info(">>> 测试调度器已启动 (每分钟运行) <<<")
#
# # 注入任务
# client.loop.create_task(start_scheduler_service())
# ================== 新增代码结束 ==================

# 获取对话列表并运行监听器
with client:
    client.run_until_disconnected()
