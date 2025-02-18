from telethon import TelegramClient, events
import utils
import variable
import config

# 2. 创建 Telegram 客户端
client = TelegramClient(config.user_session, config.api_id, config.api_hash)


@client.on(events.NewMessage(
    chats=config.group))  # 替换为群组用户名或群组 ID
async def group_message_handler(event):
    """
    监听指定群组的消息。
    """
    # 获取消息信息
    sender = await event.get_sender()
    # sender_name = sender.first_name if sender else "未知用户"
    # 获取用户id
    sender_id = sender.id if sender else "未知 ID"
    # print(f"收到来自 {sender_name} (ID: {sender_id}) 的消息：{event.raw_text}")

    # 判断是不是秋人发送的消息  秋人id 5697370563
    if sender_id == config.zq_bot:
        message = event.raw_text[0:12]
        # 处理红包信息
        await utils.handle_red_packet_message(event, client)
        # 处理 结算信息
        await utils.handle_settlement_message(message, client)
        if variable.switch:
            # 处理押注
            await utils.bet_on(event, message, client)
    # 处理自己发送的 消息
    if sender_id == config.user:
        await utils.handle_user_message(event, client)


# 启动客户端
print("正在连接到 Telegram...")
client.start()
print("客户端已启动，正在监听指定群组消息...")
# 获取对话列表并运行监听器
with client:
    client.run_until_disconnected()


