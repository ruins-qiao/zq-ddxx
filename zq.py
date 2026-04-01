import sqlite3
import aiohttp
import variable
import config
from collections import defaultdict
import re
import os
import time
from typing import Any
import asyncio
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# 假设 delete_later, config, variable, query_records 等已经在外部定义
# 如果没有定义，请确保引入它们

async def reply_temp(client, event, text, delay=10, parse_mode="markdown", delete_trigger=True):
    """统一发送回执并添加定时删除任务"""
    try:
        # logger.info(f"正在回复: {text.replace(os.linesep, ' ')[:50]}...")
        msg = await client.send_message(config.group, text, parse_mode=parse_mode)
        # 创建删除任务 (用户消息 + 机器人回复)
        if delete_trigger and event:
            asyncio.create_task(delete_later(client, event.chat_id, event.id, delay))
        asyncio.create_task(delete_later(client, msg.chat_id, msg.id, delay))
    except Exception as e:
        logger.error(f"❌ 发送消息失败: {e}")


async def zq_user(client, event):
    # 1. 使用 split() 不带参数，可以自动处理多个连续空格
    args = event.raw_text.strip().split()
    if not args:
        return

    cmd = args[0].lower()  # 统一转小写，防止大小写敏感问题

    # --- 具体的命令处理逻辑 ---

    async def cmd_help():
        help_message = """```使用方法：
- start - 启动押注
- stop - 停止押注
- st - 设置策略 (st ys_name )
- res - 重置统计数据 (res)
- ms - 占比追投参数 (ms 3 1000)
- cl - 删除群组消息 (cl)
- top - 显示捐赠排行榜 (top)
- ys - 保存预设策略 (ys yc 3 3.0 3.0 3.0 3.0 10000)
- yss - 查看或删除预设 (yss 或 yss dl yc)
- js - 计算预设所需资金 (js ys1)
- h - 查看帮助```"""
        await reply_temp(client, event, help_message, delay=60)

    async def cmd_cl():
        yss = query_records(args[1])
        if not yss:
            await reply_temp(client, event, "❌ 策略不存在")
            return

        variable.lose_stop = yss["field2"]
        variable.lose_once = yss["field3"]
        variable.lose_twice = yss["field4"]
        variable.lose_three = yss["field5"]
        variable.lose_four = yss["field6"]
        variable.initial_amount = yss["amount"]
        await reply_temp(client, event, f"""设置策略 {yss["type"]}""")

    async def cmd_reset():
        variable.win_total = 0
        variable.total = 0
        variable.earnings = 0
        await reply_temp(client, event, "重置成功")

    async def cmd_mode():
        variable.chase = int(args[1])
        variable.proportion = int(args[2])
        await reply_temp(client, event, "设置成功")

    async def cmd_clean():
        target_groups = config.zq_group
        for g in target_groups:
            # 使用列表推导式优化，或直接传递迭代器(视Telethon版本而定)
            # 注意：iter_messages 是异步生成器
            messages = [msg.id async for msg in client.iter_messages(g, from_user='me')]
            if messages:
                await client.delete_messages(g, messages)
        # 这里只删除触发命令的那条消息，时间短一点
        asyncio.create_task(delete_later(client, event.chat_id, event.id, 3))

    async def cmd_top():
        users = count_users()
        if users <= 0:
            await reply_temp(client, event, "**暂无记录**")
            return

        all_users = query_users(config.zq_bot, order="DESC")
        donation_list = [f"```当前{config.name}个人总榜Top: {len(all_users)} 为"]

        # 优化字符串拼接
        for i, item in enumerate(all_users[:20], start=1):
            donation_list.append(
                f"     总榜Top {i}: {item['name']} 大佬共赏赐小弟: {item['count']} 次,共计: {format_number(int(item['amount']))} 爱心\n"
                f"{config.name} 共赏赐 {item['name']} 小弟： {item['neg_count']} 次,共计： {format_number(int(item['neg_amount']))} 爱心"
            )
        donation_list.append("```")
        await reply_temp(client, event, "\n".join(donation_list), delay=60)

    async def cmd_ys():
        # 参数转换比较多，直接传参
        name = args[1]
        params = [int(args[2]), float(args[3]), float(args[4]), float(args[5]), float(args[6]),
                  int(args[7])]

        ys = query_records(name)
        if ys is not None:
            mes = update_record(name, *params)  # 使用解包传递参数
        else:
            mes = add_record(name, *params)
        await reply_temp(client, event, mes)

    async def cmd_yss():
        if len(args) > 2 and args[1] == "dl":
            mes = delete_record(args[2])
            await reply_temp(client, event, mes)
            return

        if count_records() > 0:
            yss_data = query_records()
            mes = "```\n" + "\n\n".join(
                f"{ys['type']}: 押注{ys['field2']}次 金额 {ys['amount']}\n"
                f"倍率 {ys['field3']} / {ys['field4']} / {ys['field5']} / {ys['field6']}"
                for ys in yss_data
            ) + "\n```"
            await reply_temp(client, event, mes, delay=60)
        else:
            await reply_temp(client, event, "**暂无预设记录**")

    async def cmd_js():
        ys = query_records(args[1])
        if ys is not None:
            js_val = calculate_losses(ys["field2"], ys["amount"], ys["field3"], ys["field4"], ys["field5"],
                                      ys["field6"])
            mes = f"累计需要资金：{int(js_val)}"
        else:
            mes = "策略不存在"
        await reply_temp(client, event, mes)

    async def cmd_start():
        variable.bet_on = True
        await reply_temp(client, event, "启动押注")

    async def cmd_stop():
        variable.bet_on = False
        await reply_temp(client, event, "停止押注")

    # --- 命令路由表 ---
    handlers = {
        "h": cmd_help,
        "help": cmd_help,
        "st": cmd_cl,
        "res": cmd_reset,
        "ms": cmd_mode,
        "cl": cmd_clean,
        "top": cmd_top,
        "ys": cmd_ys,
        "yss": cmd_yss,
        "js": cmd_js,
        "start": cmd_start,
        "stop": cmd_stop
    }

    # --- 执行逻辑 ---
    if cmd in handlers:
        # --- 日志：记录接收到的命令 ---
        try:
            sender = await event.get_sender()
            user_name = sender.first_name if sender else "Unknown"
            logger.info(f"收到命令: {cmd} | 来自: {user_name} ({event.sender_id}) | 参数: {event.raw_text}")
        except Exception as e:
            logger.error(f"日志记录出错: {e}")
        try:
            await handlers[cmd]()
            logger.info(f"✅ 命令 {cmd} 执行成功")
        except (IndexError, ValueError) as e:
            # 捕获参数缺失(IndexError)或类型错误(ValueError)
            logger.warning(f"⚠️ 命令 {cmd} 参数错误: {e}")
            await reply_temp(client, event, f"❌ 命令执行错误: 参数缺失或格式不对。\nError: {str(e)}")
        except Exception as e:
            # 捕获其他未知错误
            logger.error(f"❌ 命令 {cmd} 发生异常: {e}", exc_info=True)
            await reply_temp(client, event, f"❌ 系统错误: {str(e)}")


class MessageDeduplicator:
    def __init__(self, time_window: float = 5.0):
        """
        初始化消息去重器
        :param time_window: 时间窗口（秒），默认为5秒
        """
        self.last_message = None
        self.last_timestamp = 0.0
        self.time_window = time_window

    def should_process(self, message: Any) -> bool:
        """
        判断是否应该处理该消息
        :param message: 接收到的消息
        :return: True 表示需要处理，False 表示重复消息
        """
        current_time = time.time()

        # 如果是第一条消息，直接处理
        if self.last_message is None:
            self.last_message = message
            self.last_timestamp = current_time
            return True

        # 检查是否在时间窗口内
        is_duplicate = (current_time - self.last_timestamp) < self.time_window

        # 更新最后的消息信息
        self.last_message = message
        self.last_timestamp = current_time

        # 如果在时间窗口内，认为是重复消息，不处理
        return not is_duplicate

    def reset(self):
        """重置去重器状态"""
        self.last_message = None
        self.last_timestamp = 0.0


async def zq_bet_on(client, event, deduplicator, functions):
    if deduplicator.should_process(event):
        if variable.bet_on:
            # 判断是否是开盘信息
            if event.reply_markup:
                # logger.info(f"开始押注！")
                # 获取压大还是小
                check = next_trend(variable.history)
                logger.info(f"本次押注：{"大" if check == 1 else "小"}")
                # 获取押注金额 根据连胜局数和底价进行计算
                variable.bet_amount = calculate_bet_amount(variable.win_count, variable.lose_count,
                                                           variable.initial_amount,
                                                           variable.lose_stop, variable.lose_once,
                                                           variable.lose_twice,
                                                           variable.lose_three, variable.lose_four)
                logger.info(f"本次押注金额：{variable.bet_amount}")
                variable.total += 1
                if check == 0:
                    variable.bet_type = 0
                else:
                    variable.bet_type = 1
                # 获取要点击的按钮集合
                com = find_combination(variable.bet_amount)
                # 押注
                variable.bet = True
                await bet(check, com, event)
                mes = f"""
                            **⚡ 押注： {"押大" if check else "押小"}
        💵 金额： {variable.bet_amount}**
                            """
                await reply_temp(client, event, mes, 60, delete_trigger=False)
        else:
            variable.bet = False

    else:
        logger.info(f"忽略重复消息（时间窗口内）: {event.id}")


def calculate_losses(cycles, initial, rate1, rate2, rate3, rate4):
    total = 0
    current_bet = initial
    for i in range(cycles):
        # 累加当前押注金额
        total += current_bet

        # 确定当前阶段倍数
        if i < 3:
            rate = [rate1, rate2, rate3][i]
        else:
            rate = rate4

        # 计算基础押注金额
        base_bet = current_bet * rate

        # 计算并处理额外金额（下次金额的1%取500整倍数）
        additional = closest_multiple_of_500((base_bet * 0.01))

        # 更新押注金额（基础金额 + 处理后的额外金额）
        current_bet = base_bet + additional

    return total


def next_trend(history):
    """
    占比追投
    """
    # 获取列表的最后 n 个元素
    last_n_elements = history[-variable.chase:]
    # 判断这些元素是否都相同
    # 将切片转换为集合，如果所有元素相同，集合的长度就是1
    if len(set(last_n_elements)) == 1:
        # 如果相同，返回列表的最后一个元素
        return history[-1]
    # 不相同按照占比押注
    # 获取列表总长度
    history = [1]
    total_count = len(history[-variable.proportion:])
    # 统计 1 的数量

    ones_count = history[-variable.proportion:].count(1)
    # 计算 1 的占比
    ratio_of_ones = ones_count / total_count
    # 判断占比并返回结果
    if ratio_of_ones > 0.5:
        return 0
    else:
        return 1


def calculate_bet_amount(win_count, lose_count, initial_amount, lose_stop, lose_once, lose_twice, lose_three,
                         lose_four):
    if win_count >= 0 and lose_count == 0:
        return closest_multiple_of_500(initial_amount)
    else:
        if (lose_count + 1) > lose_stop:
            variable.win_count = 0
            variable.lose_count = 0
            return closest_multiple_of_500(initial_amount)
        if lose_count == 1:
            return closest_multiple_of_500(initial_amount * lose_once)
        if lose_count == 2:
            return closest_multiple_of_500(variable.bet_amount * lose_twice)
        if lose_count == 3:
            return closest_multiple_of_500(variable.bet_amount * lose_three)
        return closest_multiple_of_500(variable.bet_amount * lose_four)


def find_combination(target):
    """
    处理押注金额  生成要点击按钮集合
    """
    # 数字集合
    numbers = [500, 2000, 20000, 50000, 250000, 1000000, 5000000, 50000000]
    # 将数字从大到小排序
    numbers.sort(reverse=True)
    combination = []

    for num in numbers:
        while target >= num:
            combination.append(num)
            target -= num

    if target == 0:
        return combination
    else:
        return None  # 如果无法拼凑，返回 None


def closest_multiple_of_500(n):
    """
    返回最接近给定数值的500的倍数。

    :param n: 输入的数值
    :return: 最接近的500的倍数
    """
    # 四舍五入到最近的500倍数
    return round(n / 500) * 500


async def bet(check, com, event):
    # 根据 check 决定使用哪组按钮映射 (True=大, False=小)
    button_map = variable.big_button if check else variable.small_button
    direction = "大" if check else "小"

    for c in com:
        # 每个金额最大重试次数
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # event.click 返回 BotCallbackAnswer 对象
                # 使用 wait_for 增加超时控制，防止请求一直卡住
                res = await asyncio.wait_for(event.click(button_map[c]), timeout=10.0)

                # 提取返回信息并记录日志
                msg_text = res.message.replace('\n', ' ') if (
                            res and hasattr(res, 'message') and res.message) else "无返回文本"
                # logger.info(f"押注[{direction}] 金额:{c} -> 返回: {msg_text}")

                # 1. 押注成功：跳出重试循环，继续下一个金额
                if "押注成功" in msg_text:
                    break

                # 2. 操作过快/繁忙：等待后重试
                if "操作过快" in msg_text or "系统繁忙" in msg_text:
                    logger.warning(f"检测到繁忙/过快，1秒后重试...")
                    await asyncio.sleep(1)
                    continue

                # 3. 其他明确的错误（如余额不足、封盘）：不重试，跳出当前金额
                break

            except asyncio.TimeoutError:
                logger.warning(f"押注[{direction}] 金额:{c} 第{attempt + 1}次请求超时，正在重试...")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"押注[{direction}] 金额:{c} 第{attempt + 1}次失败: {e}，正在重试...")
                await asyncio.sleep(1)

        # 按钮点击间隔
        await asyncio.sleep(1.0)


def count_sequences(records):
    # 初始化统计字典
    loss_counts = {}
    win_counts = {}

    # 边界处理：空记录
    if not records:
        logger.info("**🔴 连“输”结果：\n🟢 连“赢”结果：**")
        return

    # 初始化计数变量
    current = records[0]
    count = 1

    # 遍历记录序列
    for i in range(1, len(records)):
        if records[i] == current:
            count += 1
        else:
            # 根据当前状态更新对应字典
            if current == 0:
                loss_counts[count] = loss_counts.get(count, 0) + 1
            elif current == 1:
                win_counts[count] = win_counts.get(count, 0) + 1
            current = records[i]
            count = 1

    # 处理最后一组连续记录
    if current == 0:
        loss_counts[count] = loss_counts.get(count, 0) + 1
    elif current == 1:
        win_counts[count] = win_counts.get(count, 0) + 1

    # 按连续次数降序排序
    sorted_loss = sorted(loss_counts.items(), key=lambda x: x[0], reverse=True)
    sorted_win = sorted(win_counts.items(), key=lambda x: x[0], reverse=True)

    # 格式化输出结果
    output = "🔴 **连“输”结果：**\n"
    for length, times in sorted_loss:
        output += f"{length} 连“输” : {times} 次\n"

    output += "🟢 **连“赢”结果：**\n"
    for length, times in sorted_win:
        output += f"{length} 连“赢” : {times} 次\n"

    return output.rstrip()


def count_consecutive(data):
    """统计连续出现的次数"""
    counts = {"大": defaultdict(int), "小": defaultdict(int)}
    current_value = data[0]  # 记录当前数字（1 或 0）
    current_count = 1  # 当前连胜的次数

    for i in range(1, len(data)):
        if data[i] == current_value:
            current_count += 1
        else:
            # 记录当前连胜的次数
            label = "大" if current_value == 1 else "小"
            counts[label][current_count] += 1
            # 更新计数
            current_value = data[i]
            current_count = 1

    # 处理最后一组连续数字
    label = "大" if current_value == 1 else "小"
    counts[label][current_count] += 1

    return counts


# 格式化输出
def format_counts(counts, label):
    return os.linesep.join([f"{key} 连“{label}” : {counts[key]} 次" for key in sorted(counts.keys(), reverse=True)])


async def zq_settle(client, event):
    if not event.pattern_match:
        return

    # --- 0. 快照当前押注状态 ---
    # 关键修复：在进入任何 await 之前，将全局变量保存为局部变量
    # 防止在结算过程中，新的一局开始导致 variable.bet_amount 等参数被修改
    current_bet = variable.bet
    current_bet_amount = variable.bet_amount
    current_bet_type = variable.bet_type

    # --- 1. 解析开奖结果 ---
    # 获取开奖结果字符串 (假设 group(2) 是 "大" 或 "小")
    result_str = event.pattern_match.group(2)
    # 判断是否为 "大" (1), 否则为 "小" (0)
    is_big = (result_str == variable.consequence)
    result_int = 1 if is_big else 0

    # --- 2. 结算押注逻辑 (优先级最高) ---
    if current_bet:
        # 判断输赢: 开奖结果(1/0) 是否等于 押注类型(1/0)
        # 使用快照的 current_bet_type
        is_win = (result_int == current_bet_type)

        if is_win:
            variable.win_total += 1
            # 计算利润 (扣除 1% 手续费)
            # 使用快照的 current_bet_amount
            profit = int(current_bet_amount * 0.99)
            variable.earnings += profit
            variable.balance += profit

            variable.win_count += 1
            variable.lose_count = 0

            variable.status = 1  # 1 表示赢
            variable.lose_history.append(1)
        else:
            # 输
            variable.earnings -= current_bet_amount
            variable.balance -= current_bet_amount

            variable.win_count = 0
            variable.lose_count += 1

            variable.status = 0  # 0 表示输
            variable.lose_history.append(0)
    else:
        # 未押注，记录状态为 3
        variable.lose_history.append(3)

    # 维护 lose_history 长度
    if len(variable.lose_history) > 1000:
        variable.lose_history.pop(0)

    # --- 3. 更新基础统计 (连大/连小) ---
    if is_big:
        variable.win_times += 1
        variable.lose_times = 0
    else:
        variable.win_times = 0
        variable.lose_times += 1

    # --- 4. 更新历史记录列表 ---
    variable.history.append(result_int)
    variable.a_history.append(result_int)

    # 维护 history 长度 (保持约 1000 条)
    if len(variable.history) > 1000:
        variable.history.pop(0)

    # 处理 a_history (每 1000 局发送一次完整走势)
    if len(variable.a_history) >= 1000:
        try:
            history_str = os.linesep.join(
                " ".join(map(str, variable.a_history[i:i + 20]))
                for i in range(0, len(variable.a_history), 20)
            )
            mes = f"📊 **近期 1000 次走势记录**\n{history_str}"
            await client.send_message(config.group, mes, parse_mode="markdown")
        except Exception as e:
            logger.error(f"发送历史走势失败: {e}")
        finally:
            variable.a_history.clear()

    # --- 5. 定时发送统计面板 (每 10 局) ---
    if len(variable.history) > 3 and len(variable.history) % 10 == 0:
        # 同步余额
        variable.balance = await fetch_account_balance()

        # 批量删除旧消息
        messages_to_delete = []
        if variable.message1: messages_to_delete.append(variable.message1)
        if variable.message3: messages_to_delete.append(variable.message3)
        if variable.message4: messages_to_delete.append(variable.message4)

        if messages_to_delete:
            try:
                await client.delete_messages(config.group, messages_to_delete)
            except Exception as e:
                logger.error(f"删除旧统计消息失败: {e}")
            variable.message1 = None
            variable.message3 = None
            variable.message4 = None

        # 发送新统计
        try:
            # 1000局统计
            result_counts_1000 = count_consecutive(variable.history)
            mes1 = f"""
📊 **最近 1000 局：**
🔴 **连“小”结果：**
{format_counts(result_counts_1000["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts_1000["大"], "大")}
"""
            variable.message1 = await client.send_message(config.group, mes1, parse_mode="markdown")

            # 200局统计
            result_counts_200 = count_consecutive(variable.history[-200:])
            mes3 = f"""
📊 **最近 200 局：**
🔴 **连“小”结果：**
{format_counts(result_counts_200["小"], "小")}
🟢 **连“大”结果：**
{format_counts(result_counts_200["大"], "大")}
"""
            variable.message3 = await client.send_message(config.group, mes3, parse_mode="markdown")

            # 输赢走势
            result_mes = count_sequences(variable.lose_history)
            variable.message4 = await client.send_message(config.group, result_mes, parse_mode="markdown")
        except Exception as e:
            logger.error(f"发送统计面板失败: {e}")

    # --- 6. 发送本局输赢通知 (仅在押注时) ---
    if current_bet:
        win_str = "赢" if variable.status else "输"
        # 使用快照的 current_bet_amount
        amount_str = str(int(current_bet_amount * 0.99)) if variable.status else str(current_bet_amount)

        mess = f"""**📉 输赢统计： {win_str} {amount_str}
    🎲 结果： {result_str}**"""

        await reply_temp(client, event, mess, delay=60, delete_trigger=False)

    # --- 7. 发送每局结算信息 ---
    # 删除上一局的结算消息
    if variable.message:
        try:
            await variable.message.delete()
        except Exception:
            pass

    # 构建结算面板内容
    reversed_data = ["✅" if x == 1 else "❌" for x in variable.history[-40:][::-1]]

    mes = f"""
📊 **近期 40 次结果**（由近及远）
✅：大（1）  ❌：小（0）
{os.linesep.join(" ".join(reversed_data[i:i + 10]) for i in range(0, len(reversed_data), 10))}

———————————————
"""
    mes += f"""🎯 **策略设定**
💰 **初始金额：{variable.initial_amount}**
⏹ **押注 {variable.lose_stop} 次停止**
📉 ** 押注倍率 {variable.lose_once} / {variable.lose_twice} / {variable.lose_three} / {variable.lose_four} **
🎯 ** {variable.chase}连追投 / 数据量：{variable.proportion} **\n
"""

    if variable.win_total > 0:
        win_rate = (variable.win_total / variable.total * 100) if variable.total > 0 else 0
        mes += f"""🎯 **押注次数：{variable.total}**
🏆 **胜率：{win_rate:.2f}%**\n"""

    mes += f"""💰 **收益：{variable.earnings/10000}万**
💰 **总余额：{variable.balance/10000}万**"""

    # 发送结算面板
    try:
        variable.message = await client.send_message(config.group, mes, parse_mode="markdown")
    except Exception as e:
        logger.error(f"发送结算面板失败: {e}")



# 3.3 异步获取账户余额
async def fetch_account_balance():
    """异步获取账户余额，失败时返回旧值"""
    headers = {
        "Cookie": config.ZHUQUE_COOKIE,
        "X-Csrf-Token": config.ZHUQUE_X_CSRF
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(config.ZHUQUE_API_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=5)) as response:
                data = await response.json()
                return int(data.get("data", {}).get("bonus", variable.balance))
    except Exception:
        return variable.balance


async def qz_red_packet(client, event, functions):
    if event.reply_markup:
        logger.info("消息包含按钮！")

        # 遍历按钮
        for row in event.reply_markup.rows:
            for button in row.buttons:
                if hasattr(button, 'data'):  # 内联按钮
                    logger.info(f"发现内联按钮：{button.text}, 数据：{button.data}")
                else:  # 普通按钮
                    logger.info(f"发现普通按钮：{button.text}")
                    # 点击第一个按钮（假设是内联按钮）
                i = 0
                while i < 30:
                    if event.reply_markup.rows[0].buttons[0].data:
                        await event.click(0)  # 点击第一个按钮
                        response = await client(functions.messages.GetBotCallbackAnswerRequest(
                            peer=event.chat_id,  # 目标聊天
                            msg_id=event.id,  # 消息 ID
                            data=button.data  # 按钮的 callback_data
                        ))
                        if response.message:
                            if re.search(r"已获得 (\d+) 灵石", response.message):
                                # 匹配 "已获得 xxx 灵石"
                                bonus = re.search(r"已获得 (\d+) 灵石", response.message).group(1)
                                await client.send_message(config.group, f"🎉 抢到红包{bonus}灵石！")
                                logger.info("你成功领取了灵石！")
                                return
                            elif re.search("不能重复领取", response.message):
                                # 匹配 "不能重复领取"
                                await client.send_message(config.group, f"⚠️ 抢到红包，但是没有获取到灵石数量！")
                                logger.info("不能重复领取的提示")
                                return
                        await asyncio.sleep(1)
                        i += 1


async def zq_shoot(client, event):
    # 获取当前消息的回复消息
    current_message_id = event.reply_to_msg_id
    if current_message_id:
        # 获取上一条消息（即当前消息的回复消息）
        message1 = await client.get_messages(event.chat_id, ids=current_message_id)
        # 是自己转账给别人
        if message1.sender_id == config.user:
            if message1.reply_to_msg_id:
                # 获取被转帐人信息
                message2 = await client.get_messages(event.chat_id, ids=message1.reply_to_msg_id)
                user_id = message2.sender.id
                user_name = message2.sender.first_name
                match = re.search(r"\+(\d+)", message1.raw_text)
                amount = 0
                if match:
                    amount = match.group(1)
                # 查询用户数据
                user = query_users(event.sender_id, user_id)
                if user is not None:
                    update_user(event.sender_id, user_id, name=user_name, neg_amount=user["neg_amount"] + int(amount),
                                neg_count=user["neg_count"] + 1)
                else:
                    add_user(event.sender_id, user_id, name=user_name, amount=0, count=0, neg_amount=int(amount),
                             neg_count=1)

                user = query_users(event.sender_id, user_id)
                donation_list = f"大哥赏了你 {user["neg_count"]} 次 一共 {format_number(user["neg_amount"])} 爱心！\n 这可是我的血汗钱，别乱花哦"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message2.id)
                await asyncio.sleep(30)
                await ms.delete()
        # 获取上一条消息的回复（即上一条消息的上一条）
        if message1.reply_to_msg_id:
            message2 = await client.get_messages(event.chat_id, ids=message1.reply_to_msg_id)
            if message2.from_id.user_id == config.user:
                # 获取大佬的id
                user_id = message1.sender.id
                user_name = message1.sender.first_name
                match = re.search(r"\+(\d+)", message1.raw_text)
                amount = 0
                if match:
                    amount = match.group(1)
                logger.info(f"收到来自他人的转账人id:{user_id}  名称：{user_name}   金额：{amount}")
                # 查询用户数据
                user = query_users(event.sender_id, user_id)
                if user is not None:
                    update_user(event.sender_id, user_id, name=user_name, amount=user["amount"] + int(amount),
                                count=user["count"] + 1)
                    await client.send_message(config.group, f"{user_name} 向您转账 {amount} 爱心",
                                              parse_mode="markdown")
                else:
                    add_user(event.sender_id, user_id, name=user_name, amount=int(amount), count=1, neg_amount=0,
                             neg_count=0)
                    await client.send_message(config.group, f"{user_name} 向您转账 {amount} 爱心",
                                              parse_mode="markdown")

                all_users = query_users(event.sender_id, order="DESC")
                # 找到当前用户在排序中的位置
                user = query_users(event.sender_id, user_id)
                index = next((i for i, item in enumerate(all_users) if item["user_id"] == user["user_id"]), -1)
                # 生成捐赠榜文本
                donation_list = f"```感谢 {user_name} 大佬赏赐的: {format_number(int(amount))} 爱心\n"
                donation_list += f"大佬您共赏赐了小弟: {user["count"]} 次,共计: {format_number(user["amount"])} 爱心\n"
                # donation_list += f"您是{config.name}个人打赏总榜的Top: {index + 1}\n\n"
                # donation_list += f"当前{config.name}个人总榜Top: 5 为\n"
                # # 添加总榜 Top 5
                # for i, item in enumerate(all_users[:5], start=1):
                #     name = item['name']
                #     count = item['count']
                #     am = item['amount']
                #     donation_list += f"     总榜Top {i}: {mask_if_less(int(amount), config.top, name)} 大佬共赏赐小弟: {mask_if_less(int(amount), config.top, count)} 次,共计: {mask_if_less(int(amount), config.top, format_number(int(am)))} 爱心\n"
                # donation_list += f"\n单次打赏>={format_number(config.top)}魔力查看打赏榜，感谢大佬，并期待您的下次打赏\n"
                # donation_list += f"小弟给大佬您共孝敬了: {user["neg_count"]} 次,共计: {format_number(user["neg_amount"])} 爱心"
                # donation_list += f"\n二狗哥出品，必属精品```"
                donation_list += f"```"
                ms = await client.send_message(event.chat_id, donation_list, reply_to=message1.id)
                await asyncio.sleep(30)
                await ms.delete()


def format_number(number: int) -> str:
    return f"{number:,}"


def mask_if_less(num1: int, num2: int, s) -> str:
    """
    如果 num1 小于 num2，则将 s 替换为等长的 '*'，否则返回 s 原值
    :param num1: 第一个整数，必须小于 num2
    :param num2: 第二个整数，必须大于 num1
    :param s: 需要处理的任意类型数据
    :return: 处理后的字符串
    """
    # 将第三个参数转换为字符串，支持多种数据类型
    s = str(s)

    # 判断条件，如果 num1 小于 num2，返回等长的 '*'
    return '*' * len(s) if num1 < num2 else s


async def delete_later(client, chat_id, msg_id, delay):
    """在后台等待 `delay` 秒后删除消息"""
    await asyncio.sleep(delay)
    await client.delete_messages(chat_id, msg_id)


# 数据库文件名
USERS_FILE = 'users.db'
YS_DATA_FILE = 'ys_data.db'


# 检查表是否存在并创建表
def create_table_if_not_exists():
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone() is None:
            # 表不存在，创建表
            cursor.execute('''
                CREATE TABLE users (
                    bot_id INTEGER,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    amount REAL DEFAULT 0.0,
                    count INTEGER DEFAULT 0,
                    neg_amount REAL DEFAULT 0.0,
                    neg_count INTEGER DEFAULT 0,
                    PRIMARY KEY (bot_id, user_id)
                )
            ''')
            logger.info("表 'users' 已创建")
        else:
            logger.info("表 'users' 已存在，无需创建")
        # 检查表是否存在，不存在则创建
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ys_data'")
        if cursor.fetchone() is None:
            cursor.execute('''
                CREATE TABLE ys_data (
                    type TEXT PRIMARY KEY,
                    field2 INTEGER,
                    field3 REAL,
                    field4 REAL,
                    field5 REAL,
                    field6 REAL,
                    amount INTEGER
                )
            ''')
            logger.info("表 'ys_data' 已创建")
        else:
            logger.info("表 'ys_data' 已存在，无需创建")


data = {
    "5697370563": [
        {"id": 9999, "name": "川普", "amount": 100, "count": 1, "-amount": 200, "-count": 1},
    ]
}


# 初始化数据   如需要写入历史数据使用此方法
def init_database():
    create_table_if_not_exists()  # 先检查并创建表
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        # 插入所有数据
        users_data = [(int(bot_id), item['id'], item['name'], float(item['amount']), item['count'],
                       float(item['-amount']), item['-count'])
                      for bot_id, items in data.items() for item in items]
        cursor.executemany('''
            INSERT OR REPLACE INTO users (bot_id, user_id, name, amount, count, neg_amount, neg_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', users_data)
        conn.commit()
    logger.info(f"数据初始化完成，数据条数: {len(users_data)}")


# 添加新记录
def add_user(bot_id, user_id, name, amount=0.0, count=0, neg_amount=0.0, neg_count=0):
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (bot_id, user_id, name, amount, count, neg_amount, neg_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bot_id, user_id, name, float(amount), count, float(neg_amount), neg_count))
        conn.commit()
    logger.info(f"已添加用户: {name} (Bot ID: {bot_id}, User ID: {user_id})")


# 更新用户数据
def update_user(bot_id, user_id, name=None, amount=None, count=None, neg_amount=None, neg_count=None):
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if amount is not None:
            updates.append("amount = ?")
            params.append(float(amount))
        if count is not None:
            updates.append("count = ?")
            params.append(count)
        if neg_amount is not None:
            updates.append("neg_amount = ?")
            params.append(float(neg_amount))
        if neg_count is not None:
            updates.append("neg_count = ?")
            params.append(neg_count)

        if updates:
            params.extend([bot_id, user_id])
            query = f"UPDATE users SET {', '.join(updates)} WHERE bot_id = ? AND user_id = ?"
            cursor.execute(query, params)
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"已更新用户 (Bot ID: {bot_id}, User ID: {user_id})")
            else:
                logger.info(f"未找到用户 (Bot ID: {bot_id}, User ID: {user_id})")
        else:
            logger.info("没有提供更新数据")


# 查询所有用户或根据 bot_id 和 user_id 查询
def query_users(bot_id=None, user_id=None, order=None):
    with sqlite3.connect(USERS_FILE) as conn:
        conn.row_factory = sqlite3.Row  # 返回字典格式
        cursor = conn.cursor()
        base_query = "SELECT bot_id, user_id, name, amount, count, neg_amount, neg_count FROM users"
        order_clause = ""

        # 处理排序
        if order == "ASC":
            order_clause = " ORDER BY amount ASC"
        elif order == "DESC":
            order_clause = " ORDER BY amount DESC"

        if bot_id is None and user_id is None:
            cursor.execute(base_query + order_clause)
            return [dict(row) for row in cursor.fetchall()]
        elif bot_id is not None and user_id is not None:
            cursor.execute(base_query + " WHERE bot_id = ? AND user_id = ?", (bot_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        elif bot_id is not None:
            cursor.execute(base_query + " WHERE bot_id = ?" + order_clause, (bot_id,))
            return [dict(row) for row in cursor.fetchall()]
        else:
            cursor.execute(base_query + " WHERE user_id = ?" + order_clause, (user_id,))
            return [dict(row) for row in cursor.fetchall()]


# 查询记录条数
def count_users():
    with sqlite3.connect(USERS_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count


# 添加新记录
def add_record(type_id, field2, field3, field4, field5, field6, amount):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO ys_data (type, field2, field3, field4, field5, field6, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (type_id, field2, float(field3), float(field4), float(field5), float(field6), int(amount)))
        conn.commit()
    return f"已添加：{type_id} 预设"


# 根据 type 删除记录
def delete_record(type_id):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ys_data WHERE type = ?", (type_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return f"已删除：{type_id} 预设"
        else:
            return f"未找到：{type_id} 预设"


# 更新记录
def update_record(type_id, field2=None, field3=None, field4=None, field5=None, field6=None, amount=None):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []

        if field2 is not None:
            updates.append("field2 = ?")
            params.append(field2)
        if field3 is not None:
            updates.append("field3 = ?")
            params.append(float(field3))
        if field4 is not None:
            updates.append("field4 = ?")
            params.append(float(field4))
        if field5 is not None:
            updates.append("field5 = ?")
            params.append(float(field5))
        if field6 is not None:
            updates.append("field6 = ?")
            params.append(float(field6))
        if amount is not None:
            updates.append("amount = ?")
            params.append(int(amount))

        if updates:
            params.append(type_id)
            query = f"UPDATE ys_data SET {', '.join(updates)} WHERE type = ?"
            cursor.execute(query, params)
            conn.commit()
            if cursor.rowcount > 0:
                return f"已更新：{type_id} 预设"
            else:
                return f"未找到：{type_id} 预设"
        else:
            return "没有提供更新数据"


# 查询记录
def query_records(type_id=None):
    with sqlite3.connect(YS_DATA_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if type_id is None:
            cursor.execute("SELECT * FROM ys_data ORDER BY amount DESC")
            return [dict(row) for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT * FROM ys_data WHERE type = ?", (type_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


# 查询记录条数
def count_records():
    with sqlite3.connect(YS_DATA_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ys_data")
        count = cursor.fetchone()[0]
        return count
