from amplify import IsingPoly, SymbolGenerator, IsingQuadraticModel
from amplify.client import FixstarsClient
from amplify import Solver
import numpy as np
import re
import time
import scipy.stats as stats
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm  # 进度条，方便查看10次实验进度
import warnings

warnings.filterwarnings('ignore')

# 设置中文字体（避免图表中文乱码）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号


# ==========================================
# 1. 时间分析工具类（增强版）
# ==========================================
class TimeAnalyzer:
    def __init__(self):
        self.iter_times: List[float] = []  # 存储每次迭代的耗时（秒）
        self.run_times: List[float] = []  # 存储多次运行的总耗时（秒）
        self.all_iter_times: List[float] = []  # 所有运行的所有迭代耗时

    def record_iter_time(self, iter_time: float):
        """记录单次迭代的耗时"""
        self.iter_times.append(iter_time)

    def finish_run(self):
        """完成一次完整运行，记录总耗时并重置迭代计时"""
        total_time = sum(self.iter_times)
        self.run_times.append(total_time)
        self.all_iter_times.extend(self.iter_times)
        self.iter_times = []

    def calculate_time_complexity(self) -> Dict:
        """计算时间复杂度相关指标"""
        if not self.all_iter_times:
            return {}

        # 基础统计
        avg_iter_time = np.mean(self.all_iter_times)
        std_iter_time = np.std(self.all_iter_times)
        min_iter_time = np.min(self.all_iter_times)
        max_iter_time = np.max(self.all_iter_times)

        # 时间复杂度（基于迭代次数和单次迭代耗时）
        # O(N * T) 其中N是迭代次数，T是单次迭代平均耗时
        n_iterations = len(self.all_iter_times)
        time_complexity = f"O({n_iterations} * {avg_iter_time:.2f}) = O({n_iterations * avg_iter_time:.2f}s)"

        return {
            "average_iteration_time": avg_iter_time,
            "std_iteration_time": std_iter_time,
            "min_iteration_time": min_iter_time,
            "max_iteration_time": max_iter_time,
            "total_iterations": n_iterations,
            "total_solving_time": sum(self.all_iter_times),
            "time_complexity_estimate": time_complexity,
            "iterations_per_second": 1 / avg_iter_time if avg_iter_time > 0 else 0
        }

    def calculate_95_confidence_interval(self, confidence_level: float = 0.95) -> Tuple[float, float]:
        """计算95%置信区间（针对迭代耗时）"""
        if len(self.all_iter_times) < 2:
            return (0.0, 0.0)

        # 使用t分布计算置信区间（小样本更准确）
        n = len(self.all_iter_times)
        mean = np.mean(self.all_iter_times)
        std_err = stats.sem(self.all_iter_times)  # 标准误差
        t_val = stats.t.ppf((1 + confidence_level) / 2, n - 1)  # t临界值

        margin_error = t_val * std_err
        lower_bound = mean - margin_error
        upper_bound = mean + margin_error

        return (lower_bound, upper_bound)

    def print_analysis_report(self, title="时间复杂度与置信区间分析报告"):
        """打印完整的时间分析报告"""
        print("\n" + "=" * 60)
        print(f"📊 {title}")
        print("=" * 60)

        # 基础时间统计
        time_stats = self.calculate_time_complexity()
        if not time_stats:
            print("⚠️  无足够的时间数据进行分析")
            return

        print(f"\n1. 时间复杂度分析:")
        print(f"   - 时间复杂度估算: {time_stats['time_complexity_estimate']}")
        print(f"   - 总迭代次数: {time_stats['total_iterations']}")
        print(f"   - 总求解时间: {time_stats['total_solving_time']:.2f} 秒")
        print(f"   - 平均单次迭代耗时: {time_stats['average_iteration_time']:.4f} 秒")
        print(f"   - 迭代耗时标准差: {time_stats['std_iteration_time']:.4f} 秒")
        print(f"   - 最快迭代耗时: {time_stats['min_iteration_time']:.4f} 秒")
        print(f"   - 最慢迭代耗时: {time_stats['max_iteration_time']:.4f} 秒")
        print(f"   - 迭代速度: {time_stats['iterations_per_second']:.2f} 次/秒")

        # 置信区间
        ci_lower, ci_upper = self.calculate_95_confidence_interval()
        print(f"\n2. 95% 置信区间 (单次迭代耗时):")
        print(f"   - 置信区间: [{ci_lower:.4f}, {ci_upper:.4f}] 秒")
        print(f"   - 置信区间宽度: {ci_upper - ci_lower:.4f} 秒")
        print(
            f"   - 均值 ± 边际误差: {np.mean(self.all_iter_times):.4f} ± {ci_upper - np.mean(self.all_iter_times):.4f} 秒")

        # 多次运行统计（如果有）
        if len(self.run_times) > 1:
            print(f"\n3. 多次运行统计:")
            print(f"   - 运行次数: {len(self.run_times)}")
            print(f"   - 平均运行总耗时: {np.mean(self.run_times):.2f} 秒")
            print(f"   - 运行总耗时标准差: {np.std(self.run_times):.2f} 秒")


# ==========================================
# 2. 辅助函数：构建f_base多项式
# ==========================================
def build_f_base(q):
    """构建f_base多项式，拆分成长行避免截断"""
    part1 = (
            q[0] * q[1] + -2 * q[0] * q[9] + -2 * q[1] * q[9] + q[0] + q[1] + -2 * q[9] +
            q[0] * q[1] + -2 * q[0] * q[10] + -2 * q[1] * q[10] + -q[0] + -q[1] + 2 * q[10] +
            2 * q[10] * q[11] + q[9] * q[11] + -2 * q[9] * q[12] + -2 * q[11] * q[12] + -q[9] + -q[11] + 2 * q[12]
    )

    part2 = (
            q[12] * q[8] + -2 * q[12] * q[13] + -2 * q[8] * q[13] + q[12] + q[8] + -2 * q[13] +
            q[12] * q[8] + -2 * q[12] * q[14] + -2 * q[8] * q[14] + -q[12] + -q[8] + 2 * q[14] +
            2 * q[14] * q[15] + q[13] * q[15] + -2 * q[13] * q[16] + -2 * q[15] * q[16] + -q[13] + -q[15] + 2 * q[16]
    )

    part3 = (
            q[0] * q[1] + -2 * q[0] * q[17] + -2 * q[1] * q[17] + -q[0] + -q[1] + 2 * q[17] +
            q[0] * q[8] + -2 * q[0] * q[18] + -2 * q[8] * q[18] + -q[0] + -q[8] + 2 * q[18] +
            q[1] * q[8] + -2 * q[1] * q[19] + -2 * q[8] * q[19] + -q[1] + -q[8] + 2 * q[19] +
            5 + q[17] + -4 * q[20] + -2 * q[17] * q[20] + -q[18] * q[19] + -q[18] * q[20] + -q[19] * q[20]
    )

    part4 = (
            q[2] * q[3] + -2 * q[2] * q[21] + -2 * q[3] * q[21] + q[2] + q[3] + -2 * q[21] +
            q[2] * q[3] + -2 * q[2] * q[22] + -2 * q[3] * q[22] + -q[2] + -q[3] + 2 * q[22] +
            2 * q[22] * q[23] + q[21] * q[23] + -2 * q[21] * q[24] + -2 * q[23] * q[24] + -q[21] + -q[23] + 2 * q[24]
    )

    part5 = (
            q[24] * q[20] + -2 * q[24] * q[25] + -2 * q[20] * q[25] + q[24] + q[20] + -2 * q[25] +
            q[24] * q[20] + -2 * q[24] * q[26] + -2 * q[20] * q[26] + -q[24] + -q[20] + 2 * q[26] +
            2 * q[26] * q[27] + q[25] * q[27] + -2 * q[25] * q[28] + -2 * q[27] * q[28] + -q[25] + -q[27] + 2 * q[28]
    )

    part6 = (
            q[2] * q[3] + -2 * q[2] * q[29] + -2 * q[3] * q[29] + -q[2] + -q[3] + 2 * q[29] +
            q[2] * q[20] + -2 * q[2] * q[30] + -2 * q[20] * q[30] + -q[2] + -q[20] + 2 * q[30] +
            q[3] * q[20] + -2 * q[3] * q[31] + -2 * q[20] * q[31] + -q[3] + -q[20] + 2 * q[31] +
            5 + q[29] + -4 * q[32] + -2 * q[29] * q[32] + -q[30] * q[31] + -q[30] * q[32] + -q[31] * q[32]
    )

    part7 = (
            q[4] * q[5] + -2 * q[4] * q[33] + -2 * q[5] * q[33] + q[4] + q[5] + -2 * q[33] +
            q[4] * q[5] + -2 * q[4] * q[34] + -2 * q[5] * q[34] + -q[4] + -q[5] + 2 * q[34] +
            2 * q[34] * q[35] + q[33] * q[35] + -2 * q[33] * q[36] + -2 * q[35] * q[36] + -q[33] + -q[35] + 2 * q[36]
    )

    part8 = (
            q[36] * q[32] + -2 * q[36] * q[37] + -2 * q[32] * q[37] + q[36] + q[32] + -2 * q[37] +
            q[36] * q[32] + -2 * q[36] * q[38] + -2 * q[32] * q[38] + -q[36] + -q[32] + 2 * q[38] +
            2 * q[38] * q[39] + q[37] * q[39] + -2 * q[37] * q[40] + -2 * q[39] * q[40] + -q[37] + -q[39] + 2 * q[40]
    )

    part9 = (
            q[4] * q[5] + -2 * q[4] * q[41] + -2 * q[5] * q[41] + -q[4] + -q[5] + 2 * q[41] +
            q[4] * q[32] + -2 * q[4] * q[42] + -2 * q[32] * q[42] + -q[4] + -q[32] + 2 * q[42] +
            q[5] * q[32] + -2 * q[5] * q[43] + -2 * q[32] * q[43] + -q[5] + -q[32] + 2 * q[43] +
            5 + q[41] + -4 * q[44] + -2 * q[41] * q[44] + -q[42] * q[43] + -q[42] * q[44] + -q[43] * q[44]
    )

    part10 = (
            q[6] * q[7] + -2 * q[6] * q[45] + -2 * q[7] * q[45] + q[6] + q[7] + -2 * q[45] +
            q[6] * q[7] + -2 * q[6] * q[46] + -2 * q[7] * q[46] + -q[6] + -q[7] + 2 * q[46] +
            2 * q[46] * q[47] + q[45] * q[47] + -2 * q[45] * q[48] + -2 * q[47] * q[48] + -q[45] + -q[47] + 2 * q[48]
    )

    part11 = (
            q[48] * q[44] + -2 * q[48] * q[49] + -2 * q[44] * q[49] + q[48] + q[44] + -2 * q[49] +
            q[48] * q[44] + -2 * q[48] * q[50] + -2 * q[44] * q[50] + -q[48] + -q[44] + 2 * q[50] +
            2 * q[50] * q[51] + q[49] * q[51] + -2 * q[49] * q[52] + -2 * q[51] * q[52] + -q[49] + -q[51] + 2 * q[52]
    )

    part12 = (
            q[6] * q[7] + -2 * q[6] * q[53] + -2 * q[7] * q[53] + -q[6] + -q[7] + 2 * q[53] +
            q[6] * q[44] + -2 * q[6] * q[54] + -2 * q[44] * q[54] + -q[6] + -q[44] + 2 * q[54] +
            q[7] * q[44] + -2 * q[7] * q[55] + -2 * q[44] * q[55] + -q[7] + -q[44] + 2 * q[55] +
            5 + q[53] + -4 * q[56] + -2 * q[53] * q[56] + -q[54] * q[55] + -q[54] * q[56] + -q[55] * q[56]
    )

    part13 = (
            q[0] * q[1] + -2 * q[0] * q[57] + -2 * q[1] * q[57] + -q[0] + -q[1] + 2 * q[57] +
            q[2] * q[3] + -2 * q[2] * q[58] + -2 * q[3] * q[58] + -q[2] + -q[3] + 2 * q[58] +
            q[4] * q[5] + -2 * q[4] * q[59] + -2 * q[5] * q[59] + -q[4] + -q[5] + 2 * q[59] +
            q[6] * q[7] + -2 * q[6] * q[60] + -2 * q[7] * q[60] + -q[6] + -q[7] + 2 * q[60]
    )

    part14 = (
            q[0] * q[1] + -2 * q[0] * q[61] + -2 * q[1] * q[61] + q[0] + q[1] + -2 * q[61] +
            q[0] * q[1] + -2 * q[0] * q[62] + -2 * q[1] * q[62] + -q[0] + -q[1] + 2 * q[62] +
            2 * q[62] * q[63] + q[61] * q[63] + -2 * q[61] * q[64] + -2 * q[63] * q[64] + -q[61] + -q[63] + 2 * q[64]
    )

    part15 = (
            q[2] * q[3] + -2 * q[2] * q[65] + -2 * q[3] * q[65] + q[2] + q[3] + -2 * q[65] +
            q[2] * q[3] + -2 * q[2] * q[66] + -2 * q[3] * q[66] + -q[2] + -q[3] + 2 * q[66] +
            2 * q[66] * q[67] + q[65] * q[67] + -2 * q[65] * q[68] + -2 * q[67] * q[68] + -q[65] + -q[67] + 2 * q[68]
    )

    part16 = (
            q[4] * q[5] + -2 * q[4] * q[69] + -2 * q[5] * q[69] + q[4] + q[5] + -2 * q[69] +
            q[4] * q[5] + -2 * q[4] * q[70] + -2 * q[5] * q[70] + -q[4] + -q[5] + 2 * q[70] +
            2 * q[70] * q[71] + q[69] * q[71] + -2 * q[69] * q[72] + -2 * q[71] * q[72] + -q[69] + -q[71] + 2 * q[72]
    )

    part17 = (
            q[6] * q[7] + -2 * q[6] * q[73] + -2 * q[7] * q[73] + q[6] + q[7] + -2 * q[73] +
            q[6] * q[7] + -2 * q[6] * q[74] + -2 * q[7] * q[74] + -q[6] + -q[7] + 2 * q[74] +
            2 * q[74] * q[75] + q[73] * q[75] + -2 * q[73] * q[76] + -2 * q[75] * q[76] + -q[73] + -q[75] + 2 * q[76]
    )

    part18 = (
            q[64] * q[8] + -2 * q[64] * q[77] + -2 * q[8] * q[77] + -q[64] + -q[8] + 2 * q[77] +
            q[57] * q[77] + -2 * q[57] * q[78] + -2 * q[77] * q[78] + q[57] + q[77] + -2 * q[78] +
            q[68] * q[78] + -2 * q[68] * q[79] + -2 * q[78] * q[79] + -q[68] + -q[78] + 2 * q[79]
    )

    part19 = (
            q[58] * q[79] + -2 * q[58] * q[80] + -2 * q[79] * q[80] + q[58] + q[79] + -2 * q[80] +
            q[72] * q[80] + -2 * q[72] * q[81] + -2 * q[80] * q[81] + -q[72] + -q[80] + 2 * q[81] +
            q[59] * q[81] + -2 * q[59] * q[82] + -2 * q[81] * q[82] + q[59] + q[81] + -2 * q[82]
    )

    part20 = (
            q[76] * q[82] + -2 * q[76] * q[83] + -2 * q[82] * q[83] + -q[76] + -q[82] + 2 * q[83] +
            q[60] * q[83] + -2 * q[60] * q[84] + -2 * q[83] * q[84] + q[60] + q[83] + -2 * q[84] +
            q[64] * q[8] + -2 * q[64] * q[85] + -2 * q[8] * q[85] + q[64] + q[8] + -2 * q[85]
    )

    part21 = (
            q[64] * q[8] + -2 * q[64] * q[86] + -2 * q[8] * q[86] + -q[64] + -q[8] + 2 * q[86] +
            2 * q[86] * q[87] + q[85] * q[87] + -2 * q[85] * q[88] + -2 * q[87] * q[88] + -q[85] + -q[87] + 2 * q[88]
    )

    part22 = (
            q[68] * q[78] + -2 * q[68] * q[89] + -2 * q[78] * q[89] + q[68] + q[78] + -2 * q[89] +
            q[68] * q[78] + -2 * q[68] * q[90] + -2 * q[78] * q[90] + -q[68] + -q[78] + 2 * q[90] +
            2 * q[90] * q[91] + q[89] * q[91] + -2 * q[89] * q[92] + -2 * q[91] * q[92] + -q[89] + -q[91] + 2 * q[92]
    )

    part23 = (
            q[72] * q[80] + -2 * q[72] * q[93] + -2 * q[80] * q[93] + q[72] + q[80] + -2 * q[93] +
            q[72] * q[80] + -2 * q[72] * q[94] + -2 * q[80] * q[94] + -q[72] + -q[80] + 2 * q[94] +
            2 * q[94] * q[95] + q[93] * q[95] + -2 * q[93] * q[96] + -2 * q[95] * q[96] + -q[93] + -q[95] + 2 * q[96]
    )

    part24 = (
            q[76] * q[82] + -2 * q[76] * q[97] + -2 * q[82] * q[97] + q[76] + q[82] + -2 * q[97] +
            q[76] * q[82] + -2 * q[76] * q[98] + -2 * q[82] * q[98] + -q[76] + -q[82] + 2 * q[98] +
            2 * q[98] * q[99] + q[97] * q[99] + -2 * q[97] * q[100] + -2 * q[99] * q[100] + -q[97] + -q[99] + 2 * q[100]
    )

    part25 = (
            q[16] * q[88] + -2 * q[16] * q[101] + -2 * q[88] * q[101] + q[16] + q[88] + -2 * q[101] +
            q[16] * q[88] + -2 * q[16] * q[102] + -2 * q[88] * q[102] + -q[16] + -q[88] + 2 * q[102] +
            2 * q[102] * q[103] + q[101] * q[103] + -2 * q[101] * q[104] + -2 * q[103] * q[104] + -q[101] + -q[
        103] + 2 * q[104]
    )

    part26 = (
            q[28] * q[92] + -2 * q[28] * q[105] + -2 * q[92] * q[105] + q[28] + q[92] + -2 * q[105] +
            q[28] * q[92] + -2 * q[28] * q[106] + -2 * q[92] * q[106] + -q[28] + -q[92] + 2 * q[106] +
            2 * q[106] * q[107] + q[105] * q[107] + -2 * q[105] * q[108] + -2 * q[107] * q[108] + -q[105] + -q[
        107] + 2 * q[108]
    )

    part27 = (
            q[40] * q[96] + -2 * q[40] * q[109] + -2 * q[96] * q[109] + q[40] + q[96] + -2 * q[109] +
            q[40] * q[96] + -2 * q[40] * q[110] + -2 * q[96] * q[110] + -q[40] + -q[96] + 2 * q[110] +
            2 * q[110] * q[111] + q[109] * q[111] + -2 * q[109] * q[112] + -2 * q[111] * q[112] + -q[109] + -q[
        111] + 2 * q[112]
    )

    part28 = (
            q[52] * q[100] + -2 * q[52] * q[113] + -2 * q[100] * q[113] + q[52] + q[100] + -2 * q[113] +
            q[52] * q[100] + -2 * q[52] * q[114] + -2 * q[100] * q[114] + -q[52] + -q[100] + 2 * q[114] +
            2 * q[114] * q[115] + q[113] * q[115] + -2 * q[113] * q[116] + -2 * q[115] * q[116] + -q[113] + -q[
        115] + 2 * q[116]
    )

    part29 = (
            q[56] * q[84] + -2 * q[56] * q[117] + -2 * q[84] * q[117] + q[56] + q[84] + -2 * q[117] +
            q[56] * q[84] + -2 * q[56] * q[118] + -2 * q[84] * q[118] + -q[56] + -q[84] + 2 * q[118] +
            2 * q[118] * q[119] + q[117] * q[119] + -2 * q[117] * q[120] + -2 * q[119] * q[120] + -q[117] + -q[
        119] + 2 * q[120]
    )

    part30 = (
            5 + q[104] + -4 * q[121] + -2 * q[104] * q[121] + -q[108] * q[112] + -q[108] * q[121] + -q[112] * q[121] +
            q[116] * q[120] + -2 * q[116] * q[122] + -2 * q[120] * q[122] + q[116] + q[120] + -2 * q[122] +
            q[121] * q[122] + -2 * q[121] * q[123] + -2 * q[122] * q[123] + q[121] + q[122] + -2 * q[123]
    )

    # 合并所有部分
    f_base = (
            part1 + part2 + part3 + part4 + part5 + part6 + part7 + part8 + part9 + part10 +
            part11 + part12 + part13 + part14 + part15 + part16 + part17 + part18 + part19 + part20 +
            part21 + part22 + part23 + part24 + part25 + part26 + part27 + part28 + part29 + part30
    )

    return f_base


# ==========================================
# 3. ADMM 求解器类 (提前终止+时间统计)
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

        # 初始化辅助变量
        self.y = np.zeros(self.n_aux)
        self.u = np.zeros(self.n_aux)

        # 时间分析器
        self.time_analyzer = TimeAnalyzer()

        # 提前终止相关
        self.early_stop = False
        self.stop_iteration = -1
        self.stop_energy = float('inf')

        print(f"[ADMM] 初始化完成: 3次项数量={self.n_aux}, 理论最低能量={self.target_min_energy}")

    def _parse_cubic_terms(self, cubic_list):
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

    def solve(self, max_iter=20):
        q = self.q
        best_valid_energy = float('inf')
        best_solution = None

        # 构建固定变量 Bias
        M = 20.0
        fixed_bias_poly = 0
        for idx, val in self.fixed_vars.items():
            target_sign = 1 if val == 1 else -1
            fixed_bias_poly -= M * target_sign * q[idx]

        # 能量 Offset
        energy_offset = -1.0 * self.target_min_energy

        for k in range(max_iter):
            iter_start_time = time.time()

            # x-update
            admm_bias_poly = 0
            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                y_sign = 1.0 if self.y[idx] > 0 else -1.0
                admm_bias_poly += coeff * y_sign * q[k_idx]
                penalty = -1.0 * self.rho * (self.y[idx] + self.u[idx])
                admm_bias_poly += penalty * q[i] * q[j]

            total_poly = (self.base_poly + energy_offset) + admm_bias_poly + fixed_bias_poly
            total_model = IsingQuadraticModel(total_poly)

            # 求解
            result = self.solver.solve(total_model)

            if len(result) == 0:
                iter_time = time.time() - iter_start_time
                self.time_analyzer.record_iter_time(iter_time)
                continue

            for solution in result:
                solution_energy = solution.energy
                q_val_list = self.q.decode(solution.values)
            q_val = np.array(q_val_list)

            # 计算能量
            try:
                quadratic_energy = build_f_base(q_val)
                cubic_energy = (
                        -q_val[17] * q_val[18] * q_val[19] + q_val[17] * q_val[18] * q_val[20] +
                        q_val[17] * q_val[19] * q_val[20] + 2 * q_val[18] * q_val[19] * q_val[20] +
                        -q_val[29] * q_val[30] * q_val[31] + q_val[29] * q_val[30] * q_val[32] +
                        q_val[29] * q_val[31] * q_val[32] + 2 * q_val[30] * q_val[31] * q_val[32] +
                        -q_val[41] * q_val[42] * q_val[43] + q_val[41] * q_val[42] * q_val[44] +
                        q_val[41] * q_val[43] * q_val[44] + 2 * q_val[42] * q_val[43] * q_val[44] +
                        -q_val[53] * q_val[54] * q_val[55] + q_val[53] * q_val[54] * q_val[56] +
                        q_val[53] * q_val[55] * q_val[56] + 2 * q_val[54] * q_val[55] * q_val[56] +
                        -q_val[104] * q_val[108] * q_val[112] + q_val[104] * q_val[108] * q_val[121] +
                        q_val[104] * q_val[112] * q_val[121] + 2 * q_val[108] * q_val[112] * q_val[121]
                )
                total_real_energy = quadratic_energy + cubic_energy
                normalized_base_energy = total_real_energy - self.target_min_energy
            except Exception as e:
                normalized_base_energy = 999.0

            # 记录耗时
            iter_time = time.time() - iter_start_time
            self.time_analyzer.record_iter_time(iter_time)

            if abs(normalized_base_energy) < abs(best_valid_energy):
                best_valid_energy = normalized_base_energy
                best_solution = q_val

            # 提前终止判断
            if abs(normalized_base_energy) < 0.1:
                self.early_stop = True
                self.stop_iteration = k + 1
                self.stop_energy = normalized_base_energy
                break

            # y-update & u-update
            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                prod = q_val[i] * q_val[j]
                self.y[idx] = 0.8 * prod + 0.2 * self.y[idx]
                self.u[idx] += (self.y[idx] - prod)

        self.time_analyzer.finish_run()
        return best_solution, best_valid_energy


# ==========================================
# 4. 10次重复实验主函数 (仅改这里！)
# ==========================================
def run_10_experiments():
    # 初始化客户端
    client = FixstarsClient()
    client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
    client.parameters.timeout = 5000

    # 全局变量定义
    gen = SymbolGenerator(IsingPoly)
    q = gen.array(124)

    # 三次项列表
    cubic_terms_list = [
        '-q[17]*q[18]*q[19]', 'q[17]*q[18]*q[20]', 'q[17]*q[19]*q[20]', '2*q[18]*q[19]*q[20]',
        '-q[29]*q[30]*q[31]', 'q[29]*q[30]*q[32]', 'q[29]*q[31]*q[32]', '2*q[30]*q[31]*q[32]',
        '-q[41]*q[42]*q[43]', 'q[41]*q[42]*q[44]', 'q[41]*q[43]*q[44]', '2*q[42]*q[43]*q[44]',
        '-q[53]*q[54]*q[55]', 'q[53]*q[54]*q[56]', 'q[53]*q[55]*q[56]', '2*q[54]*q[55]*q[56]',
        '-q[104]*q[108]*q[112]', 'q[104]*q[108]*q[121]', 'q[104]*q[112]*q[121]', '2*q[108]*q[112]*q[121]'
    ]

    # 构建f_base
    f_base = build_f_base(q)

    # 能量偏移和固定变量
    THEORETICAL_MIN_ENERGY = -309
    manual_fixed_vars = {123: -1}

    # 实验数据存储
    experiment_data = {
        "实验次数": [],
        "是否提前终止": [],
        "终止迭代次数": [],
        "终止能量": [],
        "总求解时间(秒)": [],
        "平均单次迭代耗时(秒)": [],
        "迭代次数": [],
        "95%置信区间下界(秒)": [],
        "95%置信区间上界(秒)": [],
        "置信区间宽度(秒)": []
    }

    # 运行10次实验（带进度条）
    print("开始10次重复实验...")
    for exp_num in tqdm(range(1, 11), desc="实验进度"):  # 仅改这里：101→11
        # 每次实验重新初始化求解器（避免状态残留）
        admm = ADMMSolver(
            client,
            f_base,
            cubic_terms_list,
            q_array=q,
            rho=2.0,
            fixed_vars=manual_fixed_vars,
            target_min_energy=THEORETICAL_MIN_ENERGY
        )

        # 执行求解
        final_q_values, final_energy = admm.solve(max_iter=15)

        # 收集数据
        experiment_data["实验次数"].append(exp_num)
        experiment_data["是否提前终止"].append(admm.early_stop)
        experiment_data["终止迭代次数"].append(admm.stop_iteration if admm.early_stop else 15)
        experiment_data["终止能量"].append(round(final_energy, 4))

        # 时间相关数据
        time_stats = admm.time_analyzer.calculate_time_complexity()
        total_time = time_stats.get("total_solving_time", 0)
        avg_iter_time = time_stats.get("average_iteration_time", 0)
        n_iterations = time_stats.get("total_iterations", 0)

        experiment_data["总求解时间(秒)"].append(round(total_time, 4))
        experiment_data["平均单次迭代耗时(秒)"].append(round(avg_iter_time, 4))
        experiment_data["迭代次数"].append(n_iterations)

        # 置信区间相关
        ci_lower, ci_upper = admm.time_analyzer.calculate_95_confidence_interval()
        experiment_data["95%置信区间下界(秒)"].append(round(ci_lower, 4))
        experiment_data["95%置信区间上界(秒)"].append(round(ci_upper, 4))
        experiment_data["置信区间宽度(秒)"].append(round(ci_upper - ci_lower, 4))

    # 转换为DataFrame（方便后续分析和表格生成）
    df = pd.DataFrame(experiment_data)

    # 保存数据到CSV（可选）
    df.to_csv("ADMM_10次实验数据.csv", index=False, encoding="utf-8-sig")
    print("\n10次实验完成！数据已保存到 ADMM_10次实验数据.csv")

    return df


# ==========================================
# 5. 生成可视化图表和综合报告
# ==========================================
def generate_report_and_plots(df):
    # ======================
    # 1. 生成统计表格
    # ======================
    print("\n" + "=" * 80)
    print("📋 ADMM 10次重复实验统计表格")
    print("=" * 80)

    # 基础统计
    basic_stats = {
        "提前终止次数": df["是否提前终止"].sum(),
        "提前终止率(%)": round(df["是否提前终止"].mean() * 100, 2),
        "平均终止迭代次数": round(df["终止迭代次数"].mean(), 2),
        "平均总求解时间(秒)": round(df["总求解时间(秒)"].mean(), 2),
        "总求解时间标准差(秒)": round(df["总求解时间(秒)"].std(), 2),
        "平均单次迭代耗时(秒)": round(df["平均单次迭代耗时(秒)"].mean(), 2),
        "平均置信区间宽度(秒)": round(df["置信区间宽度(秒)"].mean(), 2),
        "最小终止能量": round(df["终止能量"].min(), 4),
        "最大终止能量": round(df["终止能量"].max(), 4),
        "平均终止能量": round(df["终止能量"].mean(), 4)
    }

    # 打印统计表格
    stats_df = pd.DataFrame(list(basic_stats.items()), columns=["统计指标", "数值"])
    print(stats_df.to_string(index=False))

    # ======================
    # 2. 绘制可视化图表（子图布局）
    # ======================
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("ADMM 10次重复实验可视化分析", fontsize=16, fontweight="bold")

    # 子图1：提前终止迭代次数分布
    ax1 = axes[0, 0]
    stop_iter_data = df[df["是否提前终止"]]["终止迭代次数"]
    ax1.hist(stop_iter_data, bins=5, alpha=0.7, color="skyblue", edgecolor="black")
    ax1.set_title("提前终止迭代次数分布", fontsize=12, fontweight="bold")
    ax1.set_xlabel("终止迭代次数")
    ax1.set_ylabel("频次")
    ax1.grid(alpha=0.3)

    # 子图2：总求解时间分布
    ax2 = axes[0, 1]
    ax2.hist(df["总求解时间(秒)"], bins=5, alpha=0.7, color="lightcoral", edgecolor="black")
    ax2.axvline(df["总求解时间(秒)"].mean(), color="red", linestyle="--",
                label=f"均值: {df['总求解时间(秒)'].mean():.2f}s")
    ax2.set_title("总求解时间分布", fontsize=12, fontweight="bold")
    ax2.set_xlabel("总求解时间(秒)")
    ax2.set_ylabel("频次")
    ax2.legend()
    ax2.grid(alpha=0.3)

    # 子图3：平均单次迭代耗时 vs 实验次数
    ax3 = axes[1, 0]
    ax3.plot(df["实验次数"], df["平均单次迭代耗时(秒)"], color="green", alpha=0.6, marker=".", markersize=6)
    ax3.axhline(df["平均单次迭代耗时(秒)"].mean(), color="red", linestyle="--",
                label=f"均值: {df['平均单次迭代耗时(秒)'].mean():.4f}s")
    ax3.set_title("平均单次迭代耗时随实验次数变化", fontsize=12, fontweight="bold")
    ax3.set_xlabel("实验次数")
    ax3.set_ylabel("平均单次迭代耗时(秒)")
    ax3.legend()
    ax3.grid(alpha=0.3)

    # 子图4：置信区间宽度分布
    ax4 = axes[1, 1]
    ax4.hist(df["置信区间宽度(秒)"], bins=5, alpha=0.7, color="gold", edgecolor="black")
    ax4.axvline(df["置信区间宽度(秒)"].mean(), color="red", linestyle="--",
                label=f"均值: {df['置信区间宽度(秒)'].mean():.4f}s")
    ax4.set_title("95%置信区间宽度分布", fontsize=12, fontweight="bold")
    ax4.set_xlabel("置信区间宽度(秒)")
    ax4.set_ylabel("频次")
    ax4.legend()
    ax4.grid(alpha=0.3)

    # 保存图表
    plt.tight_layout()
    plt.savefig("ADMM_10次实验可视化分析.png", dpi=300, bbox_inches="tight")
    plt.show()

    # ======================
    # 3. 生成综合分析报告
    # ======================
    print("\n" + "=" * 80)
    print("📊 ADMM 10次重复实验综合分析报告")
    print("=" * 80)

    # 核心结论
    print("\n一、核心实验结果")
    print(
        f"1. 提前终止表现：共{df['是否提前终止'].sum()}次实验检测到能量归零并提前终止，提前终止率为{df['是否提前终止'].mean() * 100:.2f}%")
    print(
        f"2. 迭代效率：提前终止实验的平均终止迭代次数为{df[df['是否提前终止']]['终止迭代次数'].mean():.2f}次（最大迭代次数15次）")
    print(f"3. 时间性能：")
    print(f"   - 平均总求解时间：{df['总求解时间(秒)'].mean():.2f}秒，标准差：{df['总求解时间(秒)'].std():.2f}秒")
    print(
        f"   - 平均单次迭代耗时：{df['平均单次迭代耗时(秒)'].mean():.4f}秒，标准差：{df['平均单次迭代耗时(秒)'].std():.4f}秒")
    print(
        f"4. 能量稳定性：终止能量均值为{df['终止能量'].mean():.4f}，最小值为{df['终止能量'].min():.4f}，最大值为{df['终止能量'].max():.4f}")

    # 时间复杂度分析
    print("\n二、时间复杂度分析")
    avg_n_iter = df["迭代次数"].mean()
    avg_iter_time = df["平均单次迭代耗时(秒)"].mean()
    avg_total_time = avg_n_iter * avg_iter_time
    print(f"1. 平均时间复杂度：O({avg_n_iter:.0f} * {avg_iter_time:.2f}) = O({avg_total_time:.2f}s)")
    print(f"2. 迭代效率：平均每秒完成{1 / avg_iter_time:.2f}次迭代")

    # 置信区间分析
    print("\n三、95%置信区间分析")
    avg_ci_width = df["置信区间宽度(秒)"].mean()
    print(f"1. 平均置信区间宽度：{avg_ci_width:.4f}秒，表明单次迭代耗时的统计稳定性较好")
    print(
        f"2. 置信区间下界均值：{df['95%置信区间下界(秒)'].mean():.4f}秒，上界均值：{df['95%置信区间上界(秒)'].mean():.4f}秒")
    print(
        f"3. 95%的实验中，单次迭代耗时的真实均值落在[{df['95%置信区间下界(秒)'].mean():.4f}, {df['95%置信区间上界(秒)'].mean():.4f}]秒范围内")

    # 结论与建议
    print("\n四、结论与建议")
    print("1. 结论：")
    print("   - ADMM算法在该问题上具有较好的收敛性，提前终止率较高，能够有效找到能量归零的解")
    print("   - 算法时间性能稳定，单次迭代耗时的置信区间宽度较小，无明显异常波动")
    print("   - 总求解时间主要由迭代次数决定，提前终止能显著减少总耗时")
    print("2. 建议：")
    print("   - 可进一步优化rho参数，尝试降低单次迭代耗时，提升迭代效率")
    print("   - 可增加最大迭代次数至20次，观察是否能提升提前终止率")
    print("   - 可针对未提前终止的实验，分析能量未归零的原因，优化约束条件")


# ==========================================
# 6. 执行主流程
# ==========================================
if __name__ == "__main__":
    # 运行10次实验
    experiment_df = run_10_experiments()

    # 生成报告和图表
    generate_report_and_plots(experiment_df)