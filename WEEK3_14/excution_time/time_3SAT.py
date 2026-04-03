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
                total_real_energy = q_val[0] * q_val[1] + -2 * q_val[0] * q_val[9] + -2 * q_val[1] * \
                                    q_val[9] + q_val[0] + q_val[1] + -2 * q_val[9] + q_val[0] * q_val[1] + -2 * q_val[0] * q_val[10] + -2 * q_val[1] * \
                                    q_val[10] + -q_val[0] + -q_val[1] + 2 * q_val[10] + 2 * q_val[10] * q_val[11] + \
                                    q_val[9] * q_val[11] + -2 * q_val[9] * q_val[12] + -2 * q_val[11] * q_val[12] + - \
                                    q_val[9] + -q_val[11] + 2 * q_val[12] + q_val[12] * q_val[8] + -2 * q_val[12] * \
                                    q_val[13] + -2 * q_val[8] * q_val[13] + q_val[12] + q_val[8] + -2 * q_val[13] + \
                                    q_val[12] * q_val[8] + -2 * q_val[12] * q_val[14] + -2 * q_val[8] * q_val[14] + - \
                                    q_val[12] + -q_val[8] + 2 * q_val[14] + 2 * q_val[14] * q_val[15] + q_val[13] * \
                                    q_val[15] + -2 * q_val[13] * q_val[16] + -2 * q_val[15] * q_val[16] + -q_val[13] + - \
                                    q_val[15] + 2 * q_val[16] + q_val[0] * q_val[1] + -2 * q_val[0] * q_val[17] + -2 * \
                                    q_val[1] * q_val[17] + -q_val[0] + -q_val[1] + 2 * q_val[17] + q_val[0] * q_val[8] + -2 * q_val[0] * q_val[18] + -2 * q_val[8] * q_val[18] + -q_val[0] + -q_val[8] + 2 * q_val[18] + q_val[1] * q_val[8] + -2 * q_val[1] * q_val[19] + -2 * q_val[8] * q_val[19] + - \
                                    q_val[1] + -q_val[8] + 2 * q_val[19] + 5 + q_val[17] + -4 * q_val[20] + -2 * q_val[17] * q_val[20] + -q_val[18] * q_val[19] + -q_val[18] * q_val[20] + -q_val[19] * \
                                    q_val[20] + q_val[2] * q_val[3] + -2 * q_val[2] * q_val[21] + -2 * q_val[3] * q_val[21] + q_val[2] + q_val[3] + -2 * q_val[21] + q_val[2] * q_val[3] + -2 * q_val[2] * q_val[22] + -2 * q_val[3] * q_val[22] + -q_val[2] + -q_val[3] + 2 * q_val[22] + 2 * \
                                    q_val[22] * q_val[23] + q_val[21] * q_val[23] + -2 * q_val[21] * \
                                    q_val[24] + -2 * q_val[23] * q_val[24] + -q_val[21] + -q_val[23] + 2 * q_val[24] + \
                                    q_val[24] * q_val[20] + -2 * q_val[24] * q_val[25] + -2 * q_val[20] * q_val[25] + \
                                    q_val[24] + q_val[20] + -2 * q_val[25] + q_val[24] * q_val[20] + -2 * q_val[24] * \
                                    q_val[26] + -2 * q_val[20] * q_val[26] + -q_val[24] + -q_val[20] + 2 * q_val[26] + 2 * q_val[26] * q_val[27] + q_val[25] * q_val[27] + -2 * q_val[25] * \
                                    q_val[28] + -2 * q_val[27] * q_val[28] + -q_val[25] + -q_val[27] + 2 * q_val[28] + \
                                    q_val[2] * q_val[3] + -2 * q_val[2] * q_val[29] + -2 * q_val[3] * q_val[29] + - \
                                    q_val[2] + -q_val[3] + 2 * q_val[29] + q_val[2] * q_val[20] + -2 * q_val[2] * q_val[30] + -2 * q_val[20] * q_val[30] + -q_val[2] + -q_val[20] + 2 * q_val[30] + \
                                    q_val[3] * q_val[20] + -2 * q_val[3] * q_val[31] + -2 * q_val[20] * q_val[31] + - \
                                    q_val[3] + -q_val[20] + 2 * q_val[31] + 5 + q_val[29] + -4 * q_val[32] + -2 * q_val[29] * q_val[32] + -q_val[30] * q_val[31] + -q_val[30] * q_val[32] + -q_val[31] * \
                                    q_val[32] + q_val[4] * q_val[5] + -2 * q_val[4] * q_val[33] + -2 * q_val[5] * q_val[33] + q_val[4] + q_val[5] + -2 * q_val[33] + q_val[4] * q_val[5] + -2 * q_val[4] * q_val[34] + -2 * q_val[5] * q_val[34] + -q_val[4] + -q_val[5] + 2 * q_val[34] + 2 * q_val[34] * q_val[35] + q_val[33] * q_val[35] + -2 * q_val[33] * \
                                    q_val[36] + -2 * q_val[35] * q_val[36] + -q_val[33] + -q_val[35] + 2 * q_val[36] + \
                                    q_val[36] * q_val[32] + -2 * q_val[36] * q_val[37] + -2 * q_val[32] * q_val[37] + \
                                    q_val[36] + q_val[32] + -2 * q_val[37] + q_val[36] * q_val[32] + -2 * q_val[36] * \
                                    q_val[38] + -2 * q_val[32] * q_val[38] + -q_val[36] + -q_val[32] + 2 * q_val[38] + 2 * q_val[38] * q_val[39] + q_val[37] * q_val[39] + -2 * q_val[37] * \
                                    q_val[40] + -2 * q_val[39] * q_val[40] + -q_val[37] + -q_val[39] + 2 * q_val[40] + \
                                    q_val[4] * q_val[5] + -2 * q_val[4] * q_val[41] + -2 * q_val[5] * q_val[41] + - \
                                    q_val[4] + -q_val[5] + 2 * q_val[41] + q_val[4] * q_val[32] + -2 * q_val[4] * q_val[42] + -2 * q_val[32] * q_val[42] + -q_val[4] + -q_val[32] + 2 * q_val[42] + \
                                    q_val[5] * q_val[32] + -2 * q_val[5] * q_val[43] + -2 * q_val[32] * q_val[43] + - \
                                    q_val[5] + -q_val[32] + 2 * q_val[43] + 5 + q_val[41] + -4 * q_val[44] + -2 * q_val[41] * q_val[44] + -q_val[42] * q_val[43] + -q_val[42] * q_val[44] + -q_val[43] * \
                                    q_val[44] + q_val[6] * q_val[7] + -2 * q_val[6] * q_val[45] + -2 * q_val[7] * q_val[45] + q_val[6] + q_val[7] + -2 * q_val[45] + q_val[6] * q_val[7] + -2 * q_val[6] * q_val[46] + -2 * q_val[7] * q_val[46] + -q_val[6] + -q_val[7] + 2 * q_val[46] + 2 * q_val[46] * q_val[47] + q_val[45] * q_val[47] + -2 * q_val[45] * \
                                    q_val[48] + -2 * q_val[47] * q_val[48] + -q_val[45] + -q_val[47] + 2 * q_val[48] + \
                                    q_val[48] * q_val[44] + -2 * q_val[48] * q_val[49] + -2 * q_val[44] * q_val[49] + \
                                    q_val[48] + q_val[44] + -2 * q_val[49] + q_val[48] * q_val[44] + -2 * q_val[48] * \
                                    q_val[50] + -2 * q_val[44] * q_val[50] + -q_val[48] + -q_val[44] + 2 * q_val[50] + 2 * q_val[50] * q_val[51] + q_val[49] * q_val[51] + -2 * q_val[49] * \
                                    q_val[52] + -2 * q_val[51] * q_val[52] + -q_val[49] + -q_val[51] + 2 * q_val[52] + \
                                    q_val[6] * q_val[7] + -2 * q_val[6] * q_val[53] + -2 * q_val[7] * q_val[53] + - \
                                    q_val[6] + -q_val[7] + 2 * q_val[53] + q_val[6] * q_val[44] + -2 * q_val[6] * q_val[54] + -2 * q_val[44] * q_val[54] + -q_val[6] + -q_val[44] + 2 * q_val[54] + \
                                    q_val[7] * q_val[44] + -2 * q_val[7] * q_val[55] + -2 * q_val[44] * q_val[55] + - \
                                    q_val[7] + -q_val[44] + 2 * q_val[55] + 5 + q_val[53] + -4 * q_val[56] + -2 * q_val[53] * q_val[56] + -q_val[54] * q_val[55] + -q_val[54] * q_val[56] + -q_val[55] * \
                                    q_val[56] + q_val[0] * q_val[1] + -2 * q_val[0] * q_val[57] + -2 * q_val[1] * q_val[57] + -q_val[0] + -q_val[1] + 2 * q_val[57] + q_val[2] * q_val[3] + -2 * q_val[2] * \
                                    q_val[58] + -2 * q_val[3] * q_val[58] + -q_val[2] + -q_val[3] + 2 * q_val[58] + q_val[4] * q_val[5] + -2 * q_val[4] * q_val[59] + -2 * q_val[5] * q_val[59] + -q_val[4] + -q_val[5] + 2 * q_val[59] + q_val[6] * q_val[7] + -2 * q_val[6] * q_val[60] + -2 * q_val[7] * q_val[60] + -q_val[6] + -q_val[7] + 2 * q_val[60] + q_val[0] * q_val[1] + -2 * q_val[0] * q_val[61] + -2 * q_val[1] * q_val[61] + q_val[0] + q_val[1] + -2 * q_val[61] + q_val[0] * q_val[1] + -2 * q_val[0] * q_val[62] + -2 * q_val[1] * q_val[62] + -q_val[0] + -q_val[1] + 2 * q_val[62] + 2 * q_val[62] * q_val[63] + q_val[61] * q_val[63] + -2 * q_val[61] * \
                                    q_val[64] + -2 * q_val[63] * q_val[64] + -q_val[61] + -q_val[63] + 2 * q_val[64] + \
                                    q_val[2] * q_val[3] + -2 * q_val[2] * q_val[65] + -2 * q_val[3] * q_val[65] + q_val[2] + q_val[3] + -2 * q_val[65] + q_val[2] * q_val[3] + -2 * q_val[2] * q_val[66] + -2 * q_val[3] * q_val[66] + -q_val[2] + -q_val[3] + 2 * q_val[66] + 2 * \
                                    q_val[66] * q_val[67] + q_val[65] * q_val[67] + -2 * q_val[65] * q_val[68] + -2 * \
                                    q_val[67] * q_val[68] + -q_val[65] + -q_val[67] + 2 * q_val[68] + q_val[4] * q_val[5] + -2 * q_val[4] * q_val[69] + -2 * q_val[5] * q_val[69] + q_val[4] + q_val[5] + -2 * q_val[69] + q_val[4] * q_val[5] + -2 * q_val[4] * q_val[70] + -2 * \
                                    q_val[5] * q_val[70] + -q_val[4] + -q_val[5] + 2 * q_val[70] + 2 * q_val[70] * \
                                    q_val[71] + q_val[69] * q_val[71] + -2 * q_val[69] * q_val[72] + -2 * q_val[71] * \
                                    q_val[72] + -q_val[69] + -q_val[71] + 2 * q_val[72] + q_val[6] * q_val[7] + -2 * \
                                    q_val[6] * q_val[73] + -2 * q_val[7] * q_val[73] + q_val[6] + q_val[7] + -2 * q_val[73] + q_val[6] * q_val[7] + -2 * q_val[6] * q_val[74] + -2 * q_val[7] * q_val[74] + -q_val[6] + -q_val[7] + 2 * q_val[74] + 2 * q_val[74] * q_val[75] + q_val[73] * q_val[75] + -2 * \
                                    q_val[73] * q_val[76] + -2 * q_val[75] * q_val[76] + -q_val[73] + -q_val[75] + 2 * q_val[76] + q_val[64] * q_val[8] + -2 * q_val[64] * \
                                    q_val[77] + -2 * q_val[8] * q_val[77] + -q_val[64] + -q_val[8] + 2 * q_val[77] + \
                                    q_val[57] * q_val[77] + -2 * q_val[57] * q_val[78] + -2 * q_val[77] * q_val[78] + \
                                    q_val[57] + q_val[77] + -2 * q_val[78] + q_val[68] * q_val[78] + -2 * q_val[68] * \
                                    q_val[79] + -2 * q_val[78] * q_val[79] + -q_val[68] + -q_val[78] + 2 * q_val[79] + \
                                    q_val[58] * q_val[79] + -2 * q_val[58] * q_val[80] + -2 * q_val[79] * q_val[80] + \
                                    q_val[58] + q_val[79] + -2 * q_val[80] + q_val[72] * q_val[80] + -2 * q_val[72] * \
                                    q_val[81] + -2 * q_val[80] * q_val[81] + -q_val[72] + -q_val[80] + 2 * q_val[81] + \
                                    q_val[59] * q_val[81] + -2 * q_val[59] * q_val[82] + -2 * q_val[81] * q_val[82] + \
                                    q_val[59] + q_val[81] + -2 * q_val[82] + q_val[76] * q_val[82] + -2 * q_val[76] * \
                                    q_val[83] + -2 * q_val[82] * q_val[83] + -q_val[76] + -q_val[82] + 2 * q_val[83] + \
                                    q_val[60] * q_val[83] + -2 * q_val[60] * q_val[84] + -2 * q_val[83] * q_val[84] + \
                                    q_val[60] + q_val[83] + -2 * q_val[84] + q_val[64] * q_val[8] + -2 * q_val[64] * \
                                    q_val[85] + -2 * q_val[8] * q_val[85] + q_val[64] + q_val[8] + -2 * q_val[85] + \
                                    q_val[64] * q_val[8] + -2 * q_val[64] * q_val[86] + -2 * q_val[8] * q_val[86] + - \
                                    q_val[64] + -q_val[8] + 2 * q_val[86] + 2 * q_val[86] * q_val[87] + q_val[85] * \
                                    q_val[87] + -2 * q_val[85] * q_val[88] + -2 * q_val[87] * q_val[88] + -q_val[85] + - \
                                    q_val[87] + 2 * q_val[88] + q_val[68] * q_val[78] + -2 * q_val[68] * q_val[89] + -2 * q_val[78] * q_val[89] + q_val[68] + q_val[78] + -2 * q_val[89] + \
                                    q_val[68] * q_val[78] + -2 * q_val[68] * q_val[90] + -2 * q_val[78] * q_val[90] + - \
                                    q_val[68] + -q_val[78] + 2 * q_val[90] + 2 * q_val[90] * q_val[91] + q_val[89] * \
                                    q_val[91] + -2 * q_val[89] * q_val[92] + -2 * q_val[91] * q_val[92] + -q_val[89] + - \
                                    q_val[91] + 2 * q_val[92] + q_val[72] * q_val[80] + -2 * q_val[72] * q_val[93] + -2 * q_val[80] * q_val[93] + q_val[72] + q_val[80] + -2 * q_val[93] + \
                                    q_val[72] * q_val[80] + -2 * q_val[72] * q_val[94] + -2 * q_val[80] * q_val[94] + - \
                                    q_val[72] + -q_val[80] + 2 * q_val[94] + 2 * q_val[94] * q_val[95] + q_val[93] * \
                                    q_val[95] + -2 * q_val[93] * q_val[96] + -2 * q_val[95] * q_val[96] + -q_val[93] + - \
                                    q_val[95] + 2 * q_val[96] + q_val[76] * q_val[82] + -2 * q_val[76] * q_val[97] + -2 * q_val[82] * q_val[97] + q_val[76] + q_val[82] + -2 * q_val[97] + \
                                    q_val[76] * q_val[82] + -2 * q_val[76] * q_val[98] + -2 * q_val[82] * q_val[98] + - \
                                    q_val[76] + -q_val[82] + 2 * q_val[98] + 2 * q_val[98] * q_val[99] + q_val[97] * \
                                    q_val[99] + -2 * q_val[97] * q_val[100] + -2 * q_val[99] * q_val[100] + -q_val[97] + -q_val[99] + 2 * q_val[100] + q_val[16] * q_val[88] + -2 * q_val[16] * q_val[101] + -2 * \
                                    q_val[88] * q_val[101] + q_val[16] + q_val[88] + -2 * q_val[101] + q_val[16] * \
                                    q_val[88] + -2 * q_val[16] * q_val[102] + -2 * q_val[88] * q_val[102] + -q_val[16] + -q_val[88] + 2 * q_val[102] + 2 * q_val[102] * q_val[103] + q_val[101] * q_val[103] + -2 * \
                                    q_val[101] * q_val[104] + -2 * q_val[103] * q_val[104] + -q_val[101] + -q_val[103] + 2 * q_val[104] + q_val[28] * q_val[92] + -2 * q_val[28] * q_val[105] + -2 * q_val[92] * \
                                    q_val[105] + q_val[28] + q_val[92] + -2 * q_val[105] + q_val[28] * q_val[92] + -2 * \
                                    q_val[28] * q_val[106] + -2 * q_val[92] * q_val[106] + -q_val[28] + -q_val[92] + 2 * \
                                    q_val[106] + 2 * q_val[106] * q_val[107] + q_val[105] * q_val[107] + -2 * q_val[105] * q_val[108] + -2 * q_val[107] * q_val[108] + -q_val[105] + -q_val[107] + 2 * q_val[108] + q_val[40] * q_val[96] + -2 * q_val[40] * q_val[109] + -2 * q_val[96] * \
                                    q_val[109] + q_val[40] + q_val[96] + -2 * q_val[109] + q_val[40] * q_val[96] + -2 * \
                                    q_val[40] * q_val[110] + -2 * q_val[96] * q_val[110] + -q_val[40] + -q_val[96] + 2 * \
                                    q_val[110] + 2 * q_val[110] * q_val[111] + q_val[109] * q_val[111] + -2 * q_val[109] * q_val[112] + -2 * q_val[111] * q_val[112] + -q_val[109] + -q_val[111] + 2 * q_val[112] + q_val[52] * q_val[100] + -2 * q_val[52] * q_val[113] + -2 * q_val[100] * \
                                    q_val[113] + q_val[52] + q_val[100] + -2 * q_val[113] + q_val[52] * q_val[100] + -2 * q_val[52] * q_val[114] + -2 * q_val[100] * q_val[114] + -q_val[52] + -q_val[100] + 2 * q_val[114] + 2 * q_val[114] * q_val[115] + q_val[113] * q_val[115] + -2 * \
                                    q_val[113] * q_val[116] + -2 * q_val[115] * q_val[116] + -q_val[113] + -q_val[115] + 2 * q_val[116] + q_val[56] * q_val[84] + -2 * q_val[56] * q_val[117] + -2 * q_val[84] * \
                                    q_val[117] + q_val[56] + q_val[84] + -2 * q_val[117] + q_val[56] * q_val[84] + -2 * \
                                    q_val[56] * q_val[118] + -2 * q_val[84] * q_val[118] + -q_val[56] + -q_val[84] + 2 * \
                                    q_val[118] + 2 * q_val[118] * q_val[119] + q_val[117] * q_val[119] + -2 * q_val[117] * q_val[120] + -2 * q_val[119] * q_val[120] + -q_val[117] + -q_val[119] + 2 * q_val[120] + 5 + q_val[104] + -4 * q_val[121] + -2 * q_val[104] * q_val[121] + -q_val[108] * q_val[112] + -q_val[108] * q_val[121] + -q_val[112] * q_val[121] + q_val[116] * q_val[120] + -2 * q_val[116] * q_val[122] + -2 * q_val[120] * q_val[122] + q_val[116] + q_val[120] + -2 * q_val[122] + q_val[121] * q_val[122] + -2 * q_val[121] * q_val[123] + -2 * q_val[122] * q_val[123] + q_val[121] + q_val[122] + -2 * q_val[123] + -q_val[17] * q_val[18] * q_val[19] + q_val[17] * q_val[18] * q_val[20] + q_val[17] * q_val[19] * q_val[20] + 2 * q_val[18] * q_val[19] * q_val[20] + -q_val[29] * q_val[30] * q_val[31] + q_val[29] * q_val[30] * \
                                    q_val[32] + q_val[29] * q_val[31] * q_val[32] + 2 * q_val[30] * q_val[31] * q_val[32] + -q_val[41] * q_val[42] * q_val[43] + q_val[41] * q_val[42] * q_val[44] + \
                                    q_val[41] * q_val[43] * q_val[44] + 2 * q_val[42] * q_val[43] * q_val[44] + -q_val[53] * q_val[54] * q_val[55] + q_val[53] * q_val[54] * q_val[56] + q_val[53] * q_val[55] * q_val[56] + 2 * q_val[54] * q_val[55] * q_val[56] + -q_val[104] * q_val[108] * q_val[112] + q_val[104] * q_val[108] * q_val[121] + q_val[104] * q_val[112] * q_val[121] + 2 * q_val[108] * q_val[112] * q_val[121]

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
    q = gen.array(124)

    # 模型数据
    cubic_terms_list = [
        '-q[17]*q[18]*q[19]', 'q[17]*q[18]*q[20]', 'q[17]*q[19]*q[20]', '2*q[18]*q[19]*q[20]',
        '-q[29]*q[30]*q[31]', 'q[29]*q[30]*q[32]', 'q[29]*q[31]*q[32]', '2*q[30]*q[31]*q[32]',
        '-q[41]*q[42]*q[43]', 'q[41]*q[42]*q[44]', 'q[41]*q[43]*q[44]', '2*q[42]*q[43]*q[44]',
        '-q[53]*q[54]*q[55]', 'q[53]*q[54]*q[56]', 'q[53]*q[55]*q[56]', '2*q[54]*q[55]*q[56]',
        '-q[104]*q[108]*q[112]', 'q[104]*q[108]*q[121]', 'q[104]*q[112]*q[121]', '2*q[108]*q[112]*q[121]'
    ]

    f_base = q[0] * q[1] + -2 * q[0] * q[9] + -2 * q[1] * q[9] + q[0] + q[1] + -2 * q[9] + q[0] * q[1] + -2 * q[0] * q[10] + -2 * q[1] * q[10] + -q[0] + -q[1] + 2 * q[10] + 2 * q[10] * q[11] + q[9] * q[11] + -2 * q[9] * q[12] + -2 * q[11] * q[12] + -q[9] + -q[11] + 2 * q[12] + q[12] * q[8] + -2 * q[12] * q[13] + -2 * q[8] * q[13] + q[12] + q[8] + -2 * q[13] + q[12] * q[8] + -2 * q[12] * q[14] + -2 * q[8] * q[14] + -q[12] + -q[8] + 2 * q[14] + 2 * q[14] * q[15] + q[13] * q[15] + -2 * q[13] * q[16] + -2 * q[15] * q[16] + -q[13] + -q[15] + 2 * q[16] + q[0] * q[1] + -2 * q[0] * q[17] + -2 * q[1] * q[17] + -q[0] + -q[1] + 2 * q[17] + q[0] * q[8] + -2 * q[0] * q[18] + -2 * q[8] * q[18] + -q[0] + -q[8] + 2 * q[18] + q[1] * q[8] + -2 * q[1] * q[19] + -2 * q[8] * q[19] + -q[1] + -q[8] + 2 * q[19] + 5 + q[17] + -4 * q[20] + -2 * q[17] * q[20] + -q[18] * q[19] + -q[18] * q[20] + -q[19] * q[20] + q[2] * q[3] + -2 * q[2] * q[21] + -2 * q[3] * q[21] + q[2] + q[3] + -2 * q[21] + q[2] * q[3] + -2 * q[2] * q[22] + -2 * q[3] * q[22] + -q[2] + -q[3] + 2 * q[22] + 2 * q[22] * q[23] + q[21] * q[23] + -2 * q[21] * q[24] + -2 * q[23] * q[24] + -q[21] + -q[23] + 2 * q[24] + q[24] * q[20] + -2 * q[24] * q[25] + -2 * q[20] * q[25] + q[24] + q[20] + -2 * q[25] + q[24] * q[20] + -2 * q[24] * q[26] + -2 * q[20] * q[26] + -q[24] + -q[20] + 2 * q[26] + 2 * q[26] * q[27] + q[25] * q[27] + -2 * q[25] * q[28] + -2 * q[27] * q[28] + -q[25] + -q[27] + 2 * q[28] + q[2] * q[3] + -2 * q[2] * q[29] + -2 * q[3] * q[29] + -q[2] + -q[3] + 2 * q[29] + q[2] * q[20] + -2 * q[2] * q[30] + -2 * q[20] * q[30] + -q[2] + -q[20] + 2 * q[30] + q[3] * q[20] + -2 * q[3] * q[31] + -2 * q[20] * q[31] + -q[3] + -q[20] + 2 * q[31] + 5 + q[29] + -4 * q[32] + -2 * q[29] * q[32] + -q[30] * q[31] + -q[30] * q[32] + -q[31] * q[32] + q[4] * q[5] + -2 * q[4] * q[33] + -2 * q[5] * q[33] + q[4] + q[5] + -2 * q[33] + q[4] * q[5] + -2 * q[4] * q[34] + -2 * q[5] * q[34] + -q[4] + -q[5] + 2 * q[34] + 2 * q[34] * q[35] + q[33] * q[35] + -2 * q[33] * q[36] + -2 * q[35] * q[36] + -q[33] + -q[35] + 2 * q[36] + q[36] * q[32] + -2 * q[36] * q[37] + -2 * q[32] * q[37] + q[36] + q[32] + -2 * q[37] + q[36] * q[32] + -2 * q[36] * q[38] + -2 * q[32] * q[38] + -q[36] + -q[32] + 2 * q[38] + 2 * q[38] * q[39] + q[37] * q[39] + -2 * q[37] * q[40] + -2 * q[39] * q[40] + -q[37] + -q[39] + 2 * q[40] + q[4] * q[5] + -2 * q[4] * q[41] + -2 * q[5] * q[41] + -q[4] + -q[5] + 2 * q[41] + q[4] * q[32] + -2 * q[4] * q[42] + -2 * q[32] * q[42] + -q[4] + -q[32] + 2 * q[42] + q[5] * q[32] + -2 * q[5] * q[43] + -2 * q[32] * q[43] + -q[5] + -q[32] + 2 * q[43] + 5 + q[41] + -4 * q[44] + -2 * q[41] * q[44] + -q[42] * q[43] + -q[42] * q[44] + -q[43] * q[44] + q[6] * q[7] + -2 * q[6] * q[45] + -2 * q[7] * q[45] + q[6] + q[7] + -2 * q[45] + q[6] * q[7] + -2 * q[6] * q[46] + -2 * q[7] * q[46] + -q[6] + -q[7] + 2 * q[46] + 2 * q[46] * q[47] + q[45] * q[47] + -2 * q[45] * q[48] + -2 * q[47] * q[48] + -q[45] + -q[47] + 2 * q[48] + q[48] * q[44] + -2 * q[48] * q[49] + -2 * q[44] * q[49] + q[48] + q[44] + -2 * q[49] + q[48] * q[44] + -2 * q[48] * q[50] + -2 * q[44] * q[50] + -q[48] + -q[44] + 2 * q[50] + 2 * q[50] * q[51] + q[49] * q[51] + -2 * q[49] * q[52] + -2 * q[51] * q[52] + -q[49] + -q[51] + 2 * q[52] + q[6] * q[7] + -2 * q[6] * q[53] + -2 * q[7] * q[53] + -q[6] + -q[7] + 2 * q[53] + q[6] * q[44] + -2 * q[6] * q[54] + -2 * q[44] * q[54] + -q[6] + -q[44] + 2 * q[54] + q[7] * q[44] + -2 * q[7] * q[55] + -2 * q[44] * q[55] + -q[7] + -q[44] + 2 * q[55] + 5 + q[53] + -4 * q[56] + -2 * q[53] * q[56] + -q[54] * q[55] + -q[54] * q[56] + -q[55] * q[56] + q[0] * q[1] + -2 * q[0] * q[57] + -2 * q[1] * q[57] + -q[0] + -q[1] + 2 * q[57] + q[2] * q[3] + -2 * q[2] * q[58] + -2 * q[3] * q[58] + -q[2] + -q[3] + 2 * q[58] + q[4] * q[5] + -2 * q[4] * q[59] + -2 * q[5] * q[59] + -q[4] + -q[5] + 2 * q[59] + q[6] * q[7] + -2 * q[6] * q[60] + -2 * q[7] * q[60] + -q[6] + -q[7] + 2 * q[60] + q[0] * q[1] + -2 * q[0] * q[61] + -2 * q[1] * q[61] + q[0] + q[1] + -2 * q[61] + q[0] * q[1] + -2 * q[0] * q[62] + -2 * q[1] * q[62] + -q[0] + -q[1] + 2 * q[62] + 2 * q[62] * q[63] + q[61] * q[63] + -2 * q[61] * q[64] + -2 * q[63] * q[64] + -q[61] + -q[63] + 2 * q[64] + q[2] * q[3] + -2 * q[2] * q[65] + -2 * q[3] * q[65] + q[2] + q[3] + -2 * q[65] + q[2] * q[3] + -2 * q[2] * q[66] + -2 * q[3] * q[66] + -q[2] + -q[3] + 2 * q[66] + 2 * q[66] * q[67] + q[65] * q[67] + -2 * q[65] * q[68] + -2 * q[67] * q[68] + -q[65] + -q[67] + 2 * q[68] + q[4] * q[5] + -2 * q[4] * q[69] + -2 * q[5] * q[69] + q[4] + q[5] + -2 * q[69] + q[4] * q[5] + -2 * q[4] * q[70] + -2 * q[5] * q[70] + -q[4] + -q[5] + 2 * q[70] + 2 * q[70] * q[71] + q[69] * q[71] + -2 * q[69] * q[72] + -2 * q[71] * q[72] + -q[69] + -q[71] + 2 * q[72] + q[6] * q[7] + -2 * q[6] * q[73] + -2 * q[7] * q[73] + q[6] + q[7] + -2 * q[73] + q[6] * q[7] + -2 * q[6] * q[74] + -2 * q[7] * q[74] + -q[6] + -q[7] + 2 * q[74] + 2 * q[74] * q[75] + q[73] * q[75] + -2 * q[73] * q[76] + -2 * q[75] * q[76] + -q[73] + -q[75] + 2 * q[76] + q[64] * q[8] + -2 * q[64] * q[77] + -2 * q[8] * q[77] + -q[64] + -q[8] + 2 * q[77] + q[57] * q[77] + -2 * q[57] * q[78] + -2 * q[77] * q[78] + q[57] + q[77] + -2 * q[78] + q[68] * q[78] + -2 * q[68] * q[79] + -2 * q[78] * q[79] + -q[68] + -q[78] + 2 * q[79] + q[58] * q[79] + -2 * q[58] * q[80] + -2 * q[79] * q[80] + q[58] + q[79] + -2 * q[80] + q[72] * q[80] + -2 * q[72] * q[81] + -2 * q[80] * q[81] + -q[72] + -q[80] + 2 * q[81] + q[59] * q[81] + -2 * q[59] * q[82] + -2 * q[81] * q[82] + q[59] + q[81] + -2 * q[82] + q[76] * q[82] + -2 * q[76] * q[83] + -2 * q[82] * q[83] + -q[76] + -q[82] + 2 * q[83] + q[60] * q[83] + -2 * q[60] * q[84] + -2 * q[83] * q[84] + q[60] + q[83] + -2 * q[84] + q[64] * q[8] + -2 * q[64] * q[85] + -2 * q[8] * q[85] + q[64] + q[8] + -2 * q[85] + q[64] * q[8] + -2 * q[64] * q[86] + -2 * q[8] * q[86] + -q[64] + -q[8] + 2 * q[86] + 2 * q[86] * q[87] + q[85] * q[87] + -2 * q[85] * q[88] + -2 * q[87] * q[88] + -q[85] + -q[87] + 2 * q[88] + q[68] * q[78] + -2 * q[68] * q[89] + -2 * q[78] * q[89] + q[68] + q[78] + -2 * q[89] + q[68] * q[78] + -2 * q[68] * q[90] + -2 * q[78] * q[90] + -q[68] + -q[78] + 2 * q[90] + 2 * q[90] * q[91] + q[89] * q[91] + -2 * q[89] * q[92] + -2 * q[91] * q[92] + -q[89] + -q[91] + 2 * q[92] + q[72] * q[80] + -2 * q[72] * q[93] + -2 * q[80] * q[93] + q[72] + q[80] + -2 * q[93] + q[72] * q[80] + -2 * q[72] * q[94] + -2 * q[80] * q[94] + -q[72] + -q[80] + 2 * q[94] + 2 * q[94] * q[95] + q[93] * q[95] + -2 * q[93] * q[96] + -2 * q[95] * q[96] + -q[93] + -q[95] + 2 * q[96] + q[76] * q[82] + -2 * q[76] * q[97] + -2 * q[82] * q[97] + q[76] + q[82] + -2 * q[97] + q[76] * q[82] + -2 * q[76] * q[98] + -2 * q[82] * q[98] + -q[76] + -q[82] + 2 * q[98] + 2 * q[98] * q[99] + q[97] * q[99] + -2 * q[97] * q[100] + -2 * q[99] * q[100] + -q[97] + -q[99] + 2 * q[100] + q[16] * q[88] + -2 * q[16] * q[101] + -2 * q[88] * q[101] + q[16] + q[88] + -2 * q[101] + q[16] * q[88] + -2 * q[16] * q[102] + -2 * q[88] * q[102] + -q[16] + -q[88] + 2 * q[102] + 2 * q[102] * q[103] + q[101] * q[103] + -2 * q[101] * q[104] + -2 * q[103] * q[104] + -q[101] + -q[103] + 2 * q[104] + q[28] * q[92] + -2 * q[28] * q[105] + -2 * q[92] * q[105] + q[28] + q[92] + -2 * q[105] + q[28] * q[92] + -2 * q[28] * q[106] + -2 * q[92] * q[106] + -q[28] + -q[92] + 2 * q[106] + 2 * q[106] * q[107] + q[105] * q[107] + -2 * q[105] * q[108] + -2 * q[107] * q[108] + -q[105] + -q[107] + 2 * q[108] + q[40] * q[96] + -2 * q[40] * q[109] + -2 * q[96] * q[109] + q[40] + q[96] + -2 * q[109] + q[40] * q[96] + -2 * q[40] * q[110] + -2 * q[96] * q[110] + -q[40] + -q[96] + 2 * q[110] + 2 * q[110] * q[111] + q[109] * q[111] + -2 * q[109] * q[112] + -2 * q[111] * q[112] + -q[109] + -q[111] + 2 * q[112] + q[52] * q[100] + -2 * q[52] * q[113] + -2 * q[100] * q[113] + q[52] + q[100] + -2 * q[113] + q[52] * q[100] + -2 * q[52] * q[114] + -2 * q[100] * q[114] + -q[52] + -q[100] + 2 * q[114] + 2 * q[114] * q[115] + q[113] * q[115] + -2 * q[113] * q[116] + -2 * q[115] * q[116] + -q[113] + -q[115] + 2 * q[116] + q[56] * q[84] + -2 * q[56] * q[117] + -2 * q[84] * q[117] + q[56] + q[84] + -2 * q[117] + q[56] * q[84] + -2 * q[56] * q[118] + -2 * q[84] * q[118] + -q[56] + -q[84] + 2 * q[118] + 2 * q[118] * q[119] + q[117] * q[119] + -2 * q[117] * q[120] + -2 * q[119] * q[120] + -q[117] + -q[119] + 2 * q[120] + 5 + q[104] + -4 * q[121] + -2 * q[104] * q[121] + -q[108] * q[112] + -q[108] * q[121] + -q[112] * q[121] + q[116] * q[120] + -2 * q[116] * q[122] + -2 * q[120] * q[122] + q[116] + q[120] + -2 * q[122] + q[121] * q[122] + -2 * q[121] * q[123] + -2 * q[122] * q[123] + q[121] + q[122] + -2 * q[123]

    THEORETICAL_MIN_ENERGY = -309
    manual_fixed_vars = {123: -1}

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
    trials = 100 # 重复测试 30 次以满足统计学要求
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