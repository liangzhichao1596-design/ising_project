import numpy as np
import scipy.stats as st
import matplotlib.pyplot as plt
from amplify import IsingPoly, SymbolGenerator, IsingQuadraticModel
from amplify.client import FixstarsClient
from amplify import Solver
import re


# ==========================================
# 1. ADMM 求解器类 (加入 execution_time 提取)
# ==========================================
class ADMMSolver:
    def __init__(self, client, base_poly, cubic_terms, q_array, rho=2.0, fixed_vars=None, target_min_energy=0):
        self.client = client
        self.solver = Solver(client)
        self.base_poly = base_poly
        self.q = q_array
        self.num_qubits = len(q_array)
        self.rho = rho
        self.target_min_energy = target_min_energy
        self.fixed_vars = fixed_vars if fixed_vars is not None else {}
        self.triplets = self._parse_cubic_terms(cubic_terms)
        self.n_aux = len(self.triplets)

        self.y = np.zeros(self.n_aux)
        self.u = np.zeros(self.n_aux)

    def _parse_cubic_terms(self, cubic_list):##解析三次项
        parsed = []
        for term in cubic_list:
            indices = [int(x) for x in re.findall(r"q\[(\d+)\]", term)]
            coeff = 1.0
            clean_term = term.replace(" ", "")
            if clean_term.startswith("-"): coeff = -1.0

            if "3*" in term:
                coeff *= 3
            elif "2*" in term:
                coeff *= 2
            elif "4*" in term:
                coeff *= 4

            if len(indices) == 3:
                parsed.append((indices[0], indices[1], indices[2], coeff))
        return parsed

    def solve(self, max_iter=20, verbose=False):
        q = self.q
        best_valid_energy = float('inf')
        best_solution = None

        # 【修改点 1】：用于累加整个 ADMM 过程在底层硬件的实际执行时间
        total_execution_time = 0.0

        M = 20.0
        fixed_bias_poly = 0
        for idx, val in self.fixed_vars.items():
            target_sign = 1 if val == 1 else -1
            fixed_bias_poly -= M * target_sign * q[idx]

        energy_offset = -1.0 * self.target_min_energy

        for k in range(max_iter):
            admm_bias_poly = 0
            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                y_sign = 1.0 if self.y[idx] > 0 else -1.0
                admm_bias_poly += coeff * y_sign * q[k_idx]
                penalty = -1.0 * self.rho * (self.y[idx] + self.u[idx])
                admm_bias_poly += penalty * q[i] * q[j]

            total_poly = (self.base_poly + energy_offset) + admm_bias_poly + fixed_bias_poly
            total_model = IsingQuadraticModel(total_poly)

            # 关闭 Fixstars 的大量内部打印，保持控制台整洁
            self.client.parameters.timeout = 1000

            result = self.solver.solve(total_model)

            # 【修复点】：execution_time 是 self.solver 的属性
            # 官方文档中它返回的是一个数值（单位为毫秒 ms），所以我们除以 1000 转换为秒 (s)
            if hasattr(self.solver, 'execution_time') and self.solver.execution_time is not None:
                total_execution_time += self.solver.execution_time.total_seconds()

            if len(result) == 0:
                if verbose: print(f"Iter {k}: 无解")
                continue

            for solution in result:
                solution_energy = solution.energy
                q_val_list = self.q.decode(solution.values)
            q_val = np.array(q_val_list)

            try:
                 # 打印所有 q_val 内容
                print("=== 当前 q_val 全部内容 ===")
                for i, val in enumerate(q_val):
                       print(f"q_val[{i}] = {val}")
                print("=========================\n")
                total_real_energy = 7 + 2*q_val[4] - q_val[0]*q_val[1] - q_val[1]*q_val[4] - q_val[2]*q_val[3] - q_val[3]*q_val[4] - q_val[4]*q_val[5] - q_val[4]*q_val[6] - q_val[6]*q_val[7] - q_val[1]*q_val[3]*q_val[4] + q_val[1]*q_val[3]*q_val[6] - q_val[1]*q_val[4]*q_val[6] - q_val[3]*q_val[4]*q_val[6]

                normalized_base_energy = total_real_energy - self.target_min_energy
            except Exception as e:
                normalized_base_energy = 999.0

            if verbose: print(f"Iter {k + 1}: 能量={normalized_base_energy:.1f}")

            if abs(normalized_base_energy) < abs(best_valid_energy):
                best_valid_energy = normalized_base_energy
                best_solution = q_val

            # ====================== 【核心修改】 ======================
            # 只要能量等于0，立即终止迭代，不再继续循环
            if normalized_base_energy == 0:
                if verbose:
                    print(f"✅ 已找到最优解 normalized_base_energy = 0，提前终止迭代！")
                break  # 跳出for迭代循环
            # =========================================================

            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                prod = q_val[i] * q_val[j]
                self.y[idx] = 0.8 * prod + 0.2 * self.y[idx]
                self.u[idx] += (self.y[idx] - prod)

        # 【修改点 3】：将底层真实的求解耗时一同返回
        return best_solution, best_valid_energy, total_execution_time


# ==========================================
# 2. 封装求解与测时功能
# ==========================================
def measure_admm_time():
    """执行一次完整的 ADMM 求解，并返回耗时"""

    # 初始化客户端
    client = FixstarsClient()
    client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
    client.parameters.timeout = 1000

    gen = SymbolGenerator(IsingPoly)
    q = gen.array(8)

    # 模型数据
    cubic_terms_list = [
    '-q[1]*q[3]*q[4]',
    'q[1]*q[3]*q[6]',
    '-q[1]*q[4]*q[6]',
    '-q[3]*q[4]*q[6]',
    ]

    f_base = 7 + 2*q[4] - q[0]*q[1] - q[1]*q[4] - q[2]*q[3] - q[3]*q[4] - q[4]*q[5] - q[4]*q[6] - q[6]*q[7]

    THEORETICAL_MIN_ENERGY = 0
    manual_fixed_vars = {}
    # 123: -1

    admm = ADMMSolver(
        client,
        f_base,
        cubic_terms_list,
        q_array=q,
        rho=2.0,
        fixed_vars=manual_fixed_vars,
        target_min_energy=THEORETICAL_MIN_ENERGY
    )

    # 【修改点 4】：使用我们改写的 solve，解包接收三个返回值 (剔除了 time 模块)
    final_q_values, final_energy, hardware_execution_time = admm.solve(max_iter=15, verbose=True)

    return hardware_execution_time


# ==========================================
# 3. 统计计算与绘图模块
# ==========================================
def calculate_95_ci(data):
    """计算 95% 置信区间"""
    n = len(data)
    mean = np.mean(data)
    se = st.sem(data)
    ci = se * st.t.ppf((1 + 0.95) / 2., n - 1)
    return mean, ci


def run_performance_test():
    trials = 20 # 重复测试 30 次以满足统计学要求
    times = []

    print(f"=== 开始性能评估 (总测试次数: {trials}) ===")
    print("由于提取的是底层的真实执行时间，请耐心等待测试跑完...\n")

    for i in range(trials):
        print(f"执行测试第 {i + 1}/{trials} 次...", end="\r")
        t = measure_admm_time()
        times.append(t)

    print("\n\n测试完成！正在分析数据...")

    mean_time, ci_val = calculate_95_ci(times)

    # --- 打印结果给老师看 ---
    print("\n" + "=" * 50)
    print("性能测试评估报告 (ADMM 求解底层硬件执行时间 - 4-bit 加法器)")
    print("=" * 50)
    print(f"独立实验次数 (Trials) : {trials}")
    print(f"平均硬件耗时 (Mean)   : {mean_time:.6f} 秒")
    print(f"95% 置信区间边界 (+/-) : {ci_val:.6f} 秒")
    print(f"置信区间范围 (95% CI) : [{mean_time - ci_val:.6f} 秒, {mean_time + ci_val:.6f} 秒]")
    print("=" * 50)

    # --- 生成散点箱线图可视化 ---
    plt.figure(figsize=(8, 6))

    box = plt.boxplot(times, patch_artist=True, labels=['Hardware Execution Time (ADMM)'])

    colors = ['lightgreen']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    x = np.random.normal(1, 0.04, size=len(times))
    plt.scatter(x, times, alpha=0.5, color='darkgreen', label='Individual Test Runs')

    plt.title('ADMM Pure Hardware Execution Time (30 Trials)', fontsize=14)
    plt.ylabel('Hardware Execution Time (Seconds)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()

    save_path = "Hardware_Execution_Time_CI_Plot.png"
    plt.savefig(save_path, dpi=300)
    print(f"\n[图表生成] 执行时间的箱线图与散点图已保存至: {save_path}")


if __name__ == "__main__":
    run_performance_test()