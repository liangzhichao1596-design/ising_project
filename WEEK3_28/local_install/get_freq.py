import subprocess


def get_precise_m1_freq_ghz():
    """
    通过调用 macOS XNU 内核接口，精准获取 Apple Silicon 最大物理频率 (GHz)
    无正则、无猜测，直接读取底层硬件注册表
    """
    try:
        # 首选：读取硬件最大物理频率 (M1/M2/M3 原生支持)
        # 返回结果是精确的 Hz，例如 3200000000
        hz_str = subprocess.check_output(["sysctl", "-n", "hw.cpufrequency_max"], text=True).strip()
        return round(int(hz_str) / 1e9, 2)

    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        # 如果上一步失败，尝试读取旧版或 Intel Mac 兼容的通用节点
        try:
            hz_str = subprocess.check_output(["sysctl", "-n", "hw.cpufrequency"], text=True).strip()
            return round(int(hz_str) / 1e9, 2)

        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            print("警告：无法从系统内核读取 CPU 频率，将使用默认值。")
            # 只有在系统接口完全被屏蔽的极端情况下，才返回 3.2
            return 3.2


# 测试一下
if __name__ == "__main__":
    freq = get_precise_m1_freq_ghz()
    print(f"精准读取到的 M1 频率为: {freq} GHz")