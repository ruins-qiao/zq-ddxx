
consequence = "大"
# 总开关
switch = True

# 自动切换押注策略 根据总余额来切换占比切换 总余额*0.33 > 炸一轮的总金额 就切换到此策略
auto = False
# 自动切换押注策略 根据总余额占比
proportion = 1

temporary = 450000

win = 0

# 开盘 开关
open_ydx = False

# 历史记录
history = []

# 押注模式  0 = 反投 1 = 预测 2 = 追投
mode= 0

# 输赢变量
status = 0

# 是否押注
bet = False

# 是否开始押注
bet_on = False

# 几连开始押注
continuous = 30

# 炸几次停止
explode = 1
# 炸停止多久 单位为局
stop = 10
# 盈利停止多久 单位为局
profit_stop = 50
# 记录炸几次
explode_count = 0
# 记录停止次数
stop_count = 0
# 连续标记
mark = True
# 连续标记
flag = True
# 暂停开关
mode_stop = True
# 预测短期暂停开关
forecast_stop = True
# 预测短期暂停次数
forecast_count = 0
# 序列
current_pattern = []

i = 1

# 存放历史消息
message = None
message1 = None
message2 = None
message3 = None

# 记录押注大小
bet_type = 0

# 记录押注局数
total = 0

# 记录m1胜利局数
win_total = 0

# 记录最近100局胜负情况
win_rate = []

# 初始金额
initial_amount = 1000

# 余额
balance = 300000

# 余额
temporary_balance = 450000

# 记录押注金额
bet_amount = 0

# 收益
earnings = 0

# 周期盈利
period_profit = 0

# 盈利限额
profit = 5000000

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


# 内置预设信息
ys = {"5":["2","3","3","3","1","1","50000"],"10":["2","3","3","3","1","1","100000"],"25":["2","3","3","3","1","1","250000"],"50":["2","3","3","3","1","1","500000"],"100":["2","3","3","3","1","1","1000000"],"tz":["30","1","1","1","1","1","1000"],"yc5":["30","3","3","3","1","1","50000"],"zt":["30","5","3","2","2","2","10000"],"cs":["30","1","3","3","2","2","500"]}

small_button = {500: 14, 2000: 12, 20000: 10, 50000: 8, 250000: 6, 1000000: 4, 5000000: 2, 50000000: 0}

big_button = {500: 15, 2000: 13, 20000: 11, 50000: 9, 250000: 7, 1000000: 5, 5000000: 3, 50000000: 1}



# ----- 6 新增配置变量 -----
predictions = []  # 预测历史，修复错误的关键字段
last_predict_info = "未知 (初始状态)"  # 用于存储最近一次算法预测的模式信息