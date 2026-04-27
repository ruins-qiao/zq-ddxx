consequence = "大"

win = 0

# 历史记录
history = []

# 输赢历史记录
lose_history = []

# 输赢历史记录
a_history = []

# 输赢变量
status = 0

# 是否押注
bet = False

# 是否开始押注
bet_on = False

# 占比追投 几连追临时变量
chase = 3
# 占比追投 数据量
proportion = 1000

# 存放历史消息
message = None
message1 = None
message2 = None
message3 = None
message4 = None

# 记录押注大小
bet_type = 0

# 记录押注局数
total = 0

# 记录胜利局数
win_total = 0

# 初始金额
initial_amount = 500

# 余额
balance = 1000000


# 记录押注金额
bet_amount = 0

# 收益
earnings = 0

# 记录连赢次数
win_count = 0

# 记录连输次数
lose_count = 0

# 记录连大次数
win_times = 0

# 记录连小次数
lose_times = 0

# 连输限制
lose_stop = 2

# 输一次倍率
lose_once = 1.0

# 输二次倍率
lose_twice = 1.0

# 输三次倍率
lose_three = 1.0

# 输四次倍率
lose_four = 1.0

small_button = {500: 14, 2000: 12, 20000: 10, 50000: 8, 250000: 6, 1000000: 4, 5000000: 2, 50000000: 0}

big_button = {500: 15, 2000: 13, 20000: 11, 50000: 9, 250000: 7, 1000000: 5, 5000000: 3, 50000000: 1}

# --- 自动反向押注专属变量 ---
auto_reverse_switch = False       # 自动反向总开关
auto_reverse_amount = 500         # 反向押注固定金额
auto_reverse_start_rate = 51.0    # 触发自动反向的胜率下限（大于等于）
auto_reverse_stop_rate = 49.0     # 停止自动反向的胜率上限（小于）
auto_reverse_min_rounds = 50      # 触发所需的最小总局数

is_currently_reversing = False    # 当前是否处于自动反向激活状态
reverse_bet = False               # 本局是否下了反向单
reverse_bet_type = 0              # 反向单押了什么
reverse_bet_status = False        # 反向单输赢
reverse_total = 0                 # 反向总次数
reverse_win_total = 0             # 反向总赢次数
reverse_earnings = 0              # 反向总收益