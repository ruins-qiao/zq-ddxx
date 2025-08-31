from telethon import TelegramClient, events, functions
import config
import zq

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
# 获取对话列表并运行监听器
with client:
    client.run_until_disconnected()
