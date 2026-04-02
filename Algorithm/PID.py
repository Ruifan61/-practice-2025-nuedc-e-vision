class PID:
    def __init__(self, Kp, Ki, Kd, setpoint, max_integral=100, min_integral=-100):
        """
        初始化PID控制器

        :param Kp: 比例增益
        :param Ki: 积分增益
        :param Kd: 微分增益
        :param setpoint: 目标值（期望值），默认为0
        :param max_integral: 积分项的最大值，防止积分饱和，默认为100
        :param min_integral: 积分项的最小值，防止积分饱和，默认为-100
        """
        self.Kp = Kp  # 比例增益
        self.Ki = Ki  # 积分增益
        self.Kd = Kd  # 微分增益
        self.setpoint = setpoint  # 目标值

        # PID控制器的状态变量
        self.prev_error = 0  # 上一个误差
        self.integral = 0  # 积分部分
        self.output = 0  # 控制器输出

        # 积分限幅
        self.max_integral = max_integral
        self.min_integral = min_integral

        # print(f"PID initialized with Kp={Kp}, Ki={Ki}, Kd={Kd}, setpoint={setpoint}, max_integral={max_integral}, min_integral={min_integral}")

    def update(self, current_value):
        """
        更新PID控制器，并计算控制输出

        :param current_value: 当前值
        :return: 控制输出
        """
        # 计算误差
        error = self.setpoint - current_value

        # 积分项：累加误差
        self.integral += error

        # 如果积分项超出最大值或最小值，限制积分项
        if self.integral > self.max_integral:
            self.integral = self.max_integral
        elif self.integral < self.min_integral:
            self.integral = self.min_integral

        # 微分项：误差变化率
        derivative = error - self.prev_error

        # PID控制器输出
        self.output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative

        # 更新上一误差
        self.prev_error = error

        return self.output

    def set_setpoint(self, setpoint):
        """
        更新目标值（setpoint）

        :param setpoint: 新的目标值
        """
        self.setpoint = setpoint
        self.integral = 0  # 每次目标值改变时，重置积分部分
        self.prev_error = 0  # 重置上一误差
        self.output = 0  # 重置控制输出

    def get_output(self):
        """
        获取当前的PID控制器输出

        :return: 当前的控制输出
        """
        return self.output
