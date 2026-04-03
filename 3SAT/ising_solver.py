from amplify import IsingPoly, SymbolGenerator, IsingQuadraticModel
from amplify.client import FixstarsClient
from amplify import Solver
import numpy as np
import re


# ==========================================
# 1. ADMM 求解器类 (完全修复版)
# ==========================================
class ADMMSolver:
    def __init__(self, client, base_poly, cubic_terms, q_array, rho=2.0, fixed_vars=None, target_min_energy=0):
        """
        q_array: 必须传入外部用于构建 f_base 的那个 q 变量数组 (GenSymbol生成的对象)
        """
        self.client = client
        self.solver = Solver(client)
        self.base_poly = base_poly
        self.q = q_array  # 【关键修复1】直接复用传入的 q，解决 variable allocator 报错
        self.num_qubits = len(q_array)
        self.rho = rho
        self.target_min_energy = target_min_energy

        self.fixed_vars = fixed_vars if fixed_vars is not None else {}
        self.triplets = self._parse_cubic_terms(cubic_terms)
        self.n_aux = len(self.triplets)

        # 初始化辅助变量
        self.y = np.zeros(self.n_aux)
        self.u = np.zeros(self.n_aux)

        print(f"[ADMM] 初始化完成: 3次项数量={self.n_aux}, 理论最低能量={self.target_min_energy}")

#"3*q[0]*q[1]*q[2]" 会变成 (0, 1, 2, 3.0)
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
        # 直接使用 self.q
        q = self.q

        best_valid_energy = float('inf')
        best_solution = None

        print(f"\n=== 开始 ADMM 迭代 (目标: 归一化后电路能量 -> 0) ===")

        # 1. 构建固定变量 Bias
        M = 20.0#惩罚量
        fixed_bias_poly = 0
        for idx, val in self.fixed_vars.items():
            target_sign = 1 if val == 1 else -1
            fixed_bias_poly -= M * target_sign * q[idx]

        # 2. 能量 Offset
        energy_offset = -1.0 * self.target_min_energy

        for k in range(max_iter):
            # --- x-update ---
            admm_bias_poly = 0
            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                y_sign = 1.0 if self.y[idx] > 0 else -1.0
                admm_bias_poly += coeff * y_sign * q[k_idx]
            #引入一个动态耦合力 $J_{ij} = -\rho (y+u)$。
                penalty = -1.0 * self.rho * (self.y[idx] + self.u[idx])
                admm_bias_poly += penalty * q[i] * q[j]

            # 合并模型
            total_poly = (self.base_poly + energy_offset) + admm_bias_poly + fixed_bias_poly
            #q[123] = -1
            total_model = IsingQuadraticModel(total_poly)

            result = self.solver.solve(total_model)

            if len(result) == 0:
                print(f"Iter {k}: 无解")
                continue


            # q.decode() 会返回一个包含所有变量值的列表/数组 [-1, 1, 1, -1 ...]
            for solution in result:
                solution_energy = solution.energy
                q_val_list = self.q.decode(solution.values)
            q_val = np.array(q_val_list)  # 转为 numpy array 方便后续计算

            # 计算纯电路能量
            try:

                # 3. 总能量 = 二次 + 三次
                total_real_energy = q_val[0]*q_val[1] + -2*q_val[0]*q_val[9] + -2*q_val[1]*q_val[9] + q_val[0] + q_val[1] + -2*q_val[9] + q_val[0]*q_val[1] + -2*q_val[0]*q_val[10] + -2*q_val[1]*q_val[10] + -q_val[0] + -q_val[1] + 2*q_val[10] + 2*q_val[10]*q_val[11] + q_val[9]*q_val[11] + -2*q_val[9]*q_val[12] + -2*q_val[11]*q_val[12] + -q_val[9] + -q_val[11] + 2*q_val[12] + q_val[12]*q_val[8] + -2*q_val[12]*q_val[13] + -2*q_val[8]*q_val[13] + q_val[12] + q_val[8] + -2*q_val[13] + q_val[12]*q_val[8] + -2*q_val[12]*q_val[14] + -2*q_val[8]*q_val[14] + -q_val[12] + -q_val[8] + 2*q_val[14] + 2*q_val[14]*q_val[15] + q_val[13]*q_val[15] + -2*q_val[13]*q_val[16] + -2*q_val[15]*q_val[16] + -q_val[13] + -q_val[15] + 2*q_val[16] + q_val[0]*q_val[1] + -2*q_val[0]*q_val[17] + -2*q_val[1]*q_val[17] + -q_val[0] + -q_val[1] + 2*q_val[17] + q_val[0]*q_val[8] + -2*q_val[0]*q_val[18] + -2*q_val[8]*q_val[18] + -q_val[0] + -q_val[8] + 2*q_val[18] + q_val[1]*q_val[8] + -2*q_val[1]*q_val[19] + -2*q_val[8]*q_val[19] + -q_val[1] + -q_val[8] + 2*q_val[19] + 5 + q_val[17] + -4*q_val[20] + -2*q_val[17]*q_val[20] + -q_val[18]*q_val[19] + -q_val[18]*q_val[20] + -q_val[19]*q_val[20] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[21] + -2*q_val[3]*q_val[21] + q_val[2] + q_val[3] + -2*q_val[21] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[22] + -2*q_val[3]*q_val[22] + -q_val[2] + -q_val[3] + 2*q_val[22] + 2*q_val[22]*q_val[23] + q_val[21]*q_val[23] + -2*q_val[21]*q_val[24] + -2*q_val[23]*q_val[24] + -q_val[21] + -q_val[23] + 2*q_val[24] + q_val[24]*q_val[20] + -2*q_val[24]*q_val[25] + -2*q_val[20]*q_val[25] + q_val[24] + q_val[20] + -2*q_val[25] + q_val[24]*q_val[20] + -2*q_val[24]*q_val[26] + -2*q_val[20]*q_val[26] + -q_val[24] + -q_val[20] + 2*q_val[26] + 2*q_val[26]*q_val[27] + q_val[25]*q_val[27] + -2*q_val[25]*q_val[28] + -2*q_val[27]*q_val[28] + -q_val[25] + -q_val[27] + 2*q_val[28] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[29] + -2*q_val[3]*q_val[29] + -q_val[2] + -q_val[3] + 2*q_val[29] + q_val[2]*q_val[20] + -2*q_val[2]*q_val[30] + -2*q_val[20]*q_val[30] + -q_val[2] + -q_val[20] + 2*q_val[30] + q_val[3]*q_val[20] + -2*q_val[3]*q_val[31] + -2*q_val[20]*q_val[31] + -q_val[3] + -q_val[20] + 2*q_val[31] + 5 + q_val[29] + -4*q_val[32] + -2*q_val[29]*q_val[32] + -q_val[30]*q_val[31] + -q_val[30]*q_val[32] + -q_val[31]*q_val[32] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[33] + -2*q_val[5]*q_val[33] + q_val[4] + q_val[5] + -2*q_val[33] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[34] + -2*q_val[5]*q_val[34] + -q_val[4] + -q_val[5] + 2*q_val[34] + 2*q_val[34]*q_val[35] + q_val[33]*q_val[35] + -2*q_val[33]*q_val[36] + -2*q_val[35]*q_val[36] + -q_val[33] + -q_val[35] + 2*q_val[36] + q_val[36]*q_val[32] + -2*q_val[36]*q_val[37] + -2*q_val[32]*q_val[37] + q_val[36] + q_val[32] + -2*q_val[37] + q_val[36]*q_val[32] + -2*q_val[36]*q_val[38] + -2*q_val[32]*q_val[38] + -q_val[36] + -q_val[32] + 2*q_val[38] + 2*q_val[38]*q_val[39] + q_val[37]*q_val[39] + -2*q_val[37]*q_val[40] + -2*q_val[39]*q_val[40] + -q_val[37] + -q_val[39] + 2*q_val[40] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[41] + -2*q_val[5]*q_val[41] + -q_val[4] + -q_val[5] + 2*q_val[41] + q_val[4]*q_val[32] + -2*q_val[4]*q_val[42] + -2*q_val[32]*q_val[42] + -q_val[4] + -q_val[32] + 2*q_val[42] + q_val[5]*q_val[32] + -2*q_val[5]*q_val[43] + -2*q_val[32]*q_val[43] + -q_val[5] + -q_val[32] + 2*q_val[43] + 5 + q_val[41] + -4*q_val[44] + -2*q_val[41]*q_val[44] + -q_val[42]*q_val[43] + -q_val[42]*q_val[44] + -q_val[43]*q_val[44] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[45] + -2*q_val[7]*q_val[45] + q_val[6] + q_val[7] + -2*q_val[45] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[46] + -2*q_val[7]*q_val[46] + -q_val[6] + -q_val[7] + 2*q_val[46] + 2*q_val[46]*q_val[47] + q_val[45]*q_val[47] + -2*q_val[45]*q_val[48] + -2*q_val[47]*q_val[48] + -q_val[45] + -q_val[47] + 2*q_val[48] + q_val[48]*q_val[44] + -2*q_val[48]*q_val[49] + -2*q_val[44]*q_val[49] + q_val[48] + q_val[44] + -2*q_val[49] + q_val[48]*q_val[44] + -2*q_val[48]*q_val[50] + -2*q_val[44]*q_val[50] + -q_val[48] + -q_val[44] + 2*q_val[50] + 2*q_val[50]*q_val[51] + q_val[49]*q_val[51] + -2*q_val[49]*q_val[52] + -2*q_val[51]*q_val[52] + -q_val[49] + -q_val[51] + 2*q_val[52] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[53] + -2*q_val[7]*q_val[53] + -q_val[6] + -q_val[7] + 2*q_val[53] + q_val[6]*q_val[44] + -2*q_val[6]*q_val[54] + -2*q_val[44]*q_val[54] + -q_val[6] + -q_val[44] + 2*q_val[54] + q_val[7]*q_val[44] + -2*q_val[7]*q_val[55] + -2*q_val[44]*q_val[55] + -q_val[7] + -q_val[44] + 2*q_val[55] + 5 + q_val[53] + -4*q_val[56] + -2*q_val[53]*q_val[56] + -q_val[54]*q_val[55] + -q_val[54]*q_val[56] + -q_val[55]*q_val[56] + q_val[0]*q_val[1] + -2*q_val[0]*q_val[57] + -2*q_val[1]*q_val[57] + -q_val[0] + -q_val[1] + 2*q_val[57] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[58] + -2*q_val[3]*q_val[58] + -q_val[2] + -q_val[3] + 2*q_val[58] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[59] + -2*q_val[5]*q_val[59] + -q_val[4] + -q_val[5] + 2*q_val[59] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[60] + -2*q_val[7]*q_val[60] + -q_val[6] + -q_val[7] + 2*q_val[60] + q_val[0]*q_val[1] + -2*q_val[0]*q_val[61] + -2*q_val[1]*q_val[61] + q_val[0] + q_val[1] + -2*q_val[61] + q_val[0]*q_val[1] + -2*q_val[0]*q_val[62] + -2*q_val[1]*q_val[62] + -q_val[0] + -q_val[1] + 2*q_val[62] + 2*q_val[62]*q_val[63] + q_val[61]*q_val[63] + -2*q_val[61]*q_val[64] + -2*q_val[63]*q_val[64] + -q_val[61] + -q_val[63] + 2*q_val[64] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[65] + -2*q_val[3]*q_val[65] + q_val[2] + q_val[3] + -2*q_val[65] + q_val[2]*q_val[3] + -2*q_val[2]*q_val[66] + -2*q_val[3]*q_val[66] + -q_val[2] + -q_val[3] + 2*q_val[66] + 2*q_val[66]*q_val[67] + q_val[65]*q_val[67] + -2*q_val[65]*q_val[68] + -2*q_val[67]*q_val[68] + -q_val[65] + -q_val[67] + 2*q_val[68] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[69] + -2*q_val[5]*q_val[69] + q_val[4] + q_val[5] + -2*q_val[69] + q_val[4]*q_val[5] + -2*q_val[4]*q_val[70] + -2*q_val[5]*q_val[70] + -q_val[4] + -q_val[5] + 2*q_val[70] + 2*q_val[70]*q_val[71] + q_val[69]*q_val[71] + -2*q_val[69]*q_val[72] + -2*q_val[71]*q_val[72] + -q_val[69] + -q_val[71] + 2*q_val[72] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[73] + -2*q_val[7]*q_val[73] + q_val[6] + q_val[7] + -2*q_val[73] + q_val[6]*q_val[7] + -2*q_val[6]*q_val[74] + -2*q_val[7]*q_val[74] + -q_val[6] + -q_val[7] + 2*q_val[74] + 2*q_val[74]*q_val[75] + q_val[73]*q_val[75] + -2*q_val[73]*q_val[76] + -2*q_val[75]*q_val[76] + -q_val[73] + -q_val[75] + 2*q_val[76] + q_val[64]*q_val[8] + -2*q_val[64]*q_val[77] + -2*q_val[8]*q_val[77] + -q_val[64] + -q_val[8] + 2*q_val[77] + q_val[57]*q_val[77] + -2*q_val[57]*q_val[78] + -2*q_val[77]*q_val[78] + q_val[57] + q_val[77] + -2*q_val[78] + q_val[68]*q_val[78] + -2*q_val[68]*q_val[79] + -2*q_val[78]*q_val[79] + -q_val[68] + -q_val[78] + 2*q_val[79] + q_val[58]*q_val[79] + -2*q_val[58]*q_val[80] + -2*q_val[79]*q_val[80] + q_val[58] + q_val[79] + -2*q_val[80] + q_val[72]*q_val[80] + -2*q_val[72]*q_val[81] + -2*q_val[80]*q_val[81] + -q_val[72] + -q_val[80] + 2*q_val[81] + q_val[59]*q_val[81] + -2*q_val[59]*q_val[82] + -2*q_val[81]*q_val[82] + q_val[59] + q_val[81] + -2*q_val[82] + q_val[76]*q_val[82] + -2*q_val[76]*q_val[83] + -2*q_val[82]*q_val[83] + -q_val[76] + -q_val[82] + 2*q_val[83] + q_val[60]*q_val[83] + -2*q_val[60]*q_val[84] + -2*q_val[83]*q_val[84] + q_val[60] + q_val[83] + -2*q_val[84] + q_val[64]*q_val[8] + -2*q_val[64]*q_val[85] + -2*q_val[8]*q_val[85] + q_val[64] + q_val[8] + -2*q_val[85] + q_val[64]*q_val[8] + -2*q_val[64]*q_val[86] + -2*q_val[8]*q_val[86] + -q_val[64] + -q_val[8] + 2*q_val[86] + 2*q_val[86]*q_val[87] + q_val[85]*q_val[87] + -2*q_val[85]*q_val[88] + -2*q_val[87]*q_val[88] + -q_val[85] + -q_val[87] + 2*q_val[88] + q_val[68]*q_val[78] + -2*q_val[68]*q_val[89] + -2*q_val[78]*q_val[89] + q_val[68] + q_val[78] + -2*q_val[89] + q_val[68]*q_val[78] + -2*q_val[68]*q_val[90] + -2*q_val[78]*q_val[90] + -q_val[68] + -q_val[78] + 2*q_val[90] + 2*q_val[90]*q_val[91] + q_val[89]*q_val[91] + -2*q_val[89]*q_val[92] + -2*q_val[91]*q_val[92] + -q_val[89] + -q_val[91] + 2*q_val[92] + q_val[72]*q_val[80] + -2*q_val[72]*q_val[93] + -2*q_val[80]*q_val[93] + q_val[72] + q_val[80] + -2*q_val[93] + q_val[72]*q_val[80] + -2*q_val[72]*q_val[94] + -2*q_val[80]*q_val[94] + -q_val[72] + -q_val[80] + 2*q_val[94] + 2*q_val[94]*q_val[95] + q_val[93]*q_val[95] + -2*q_val[93]*q_val[96] + -2*q_val[95]*q_val[96] + -q_val[93] + -q_val[95] + 2*q_val[96] + q_val[76]*q_val[82] + -2*q_val[76]*q_val[97] + -2*q_val[82]*q_val[97] + q_val[76] + q_val[82] + -2*q_val[97] + q_val[76]*q_val[82] + -2*q_val[76]*q_val[98] + -2*q_val[82]*q_val[98] + -q_val[76] + -q_val[82] + 2*q_val[98] + 2*q_val[98]*q_val[99] + q_val[97]*q_val[99] + -2*q_val[97]*q_val[100] + -2*q_val[99]*q_val[100] + -q_val[97] + -q_val[99] + 2*q_val[100] + q_val[16]*q_val[88] + -2*q_val[16]*q_val[101] + -2*q_val[88]*q_val[101] + q_val[16] + q_val[88] + -2*q_val[101] + q_val[16]*q_val[88] + -2*q_val[16]*q_val[102] + -2*q_val[88]*q_val[102] + -q_val[16] + -q_val[88] + 2*q_val[102] + 2*q_val[102]*q_val[103] + q_val[101]*q_val[103] + -2*q_val[101]*q_val[104] + -2*q_val[103]*q_val[104] + -q_val[101] + -q_val[103] + 2*q_val[104] + q_val[28]*q_val[92] + -2*q_val[28]*q_val[105] + -2*q_val[92]*q_val[105] + q_val[28] + q_val[92] + -2*q_val[105] + q_val[28]*q_val[92] + -2*q_val[28]*q_val[106] + -2*q_val[92]*q_val[106] + -q_val[28] + -q_val[92] + 2*q_val[106] + 2*q_val[106]*q_val[107] + q_val[105]*q_val[107] + -2*q_val[105]*q_val[108] + -2*q_val[107]*q_val[108] + -q_val[105] + -q_val[107] + 2*q_val[108] + q_val[40]*q_val[96] + -2*q_val[40]*q_val[109] + -2*q_val[96]*q_val[109] + q_val[40] + q_val[96] + -2*q_val[109] + q_val[40]*q_val[96] + -2*q_val[40]*q_val[110] + -2*q_val[96]*q_val[110] + -q_val[40] + -q_val[96] + 2*q_val[110] + 2*q_val[110]*q_val[111] + q_val[109]*q_val[111] + -2*q_val[109]*q_val[112] + -2*q_val[111]*q_val[112] + -q_val[109] + -q_val[111] + 2*q_val[112] + q_val[52]*q_val[100] + -2*q_val[52]*q_val[113] + -2*q_val[100]*q_val[113] + q_val[52] + q_val[100] + -2*q_val[113] + q_val[52]*q_val[100] + -2*q_val[52]*q_val[114] + -2*q_val[100]*q_val[114] + -q_val[52] + -q_val[100] + 2*q_val[114] + 2*q_val[114]*q_val[115] + q_val[113]*q_val[115] + -2*q_val[113]*q_val[116] + -2*q_val[115]*q_val[116] + -q_val[113] + -q_val[115] + 2*q_val[116] + q_val[56]*q_val[84] + -2*q_val[56]*q_val[117] + -2*q_val[84]*q_val[117] + q_val[56] + q_val[84] + -2*q_val[117] + q_val[56]*q_val[84] + -2*q_val[56]*q_val[118] + -2*q_val[84]*q_val[118] + -q_val[56] + -q_val[84] + 2*q_val[118] + 2*q_val[118]*q_val[119] + q_val[117]*q_val[119] + -2*q_val[117]*q_val[120] + -2*q_val[119]*q_val[120] + -q_val[117] + -q_val[119] + 2*q_val[120] + 5 + q_val[104] + -4*q_val[121] + -2*q_val[104]*q_val[121] + -q_val[108]*q_val[112] + -q_val[108]*q_val[121] + -q_val[112]*q_val[121] + q_val[116]*q_val[120] + -2*q_val[116]*q_val[122] + -2*q_val[120]*q_val[122] + q_val[116] + q_val[120] + -2*q_val[122] + q_val[121]*q_val[122] + -2*q_val[121]*q_val[123] + -2*q_val[122]*q_val[123] + q_val[121] + q_val[122] + -2*q_val[123] + -q_val[17]*q_val[18]*q_val[19] + q_val[17]*q_val[18]*q_val[20] + q_val[17]*q_val[19]*q_val[20] + 2*q_val[18]*q_val[19]*q_val[20] + -q_val[29]*q_val[30]*q_val[31] + q_val[29]*q_val[30]*q_val[32] + q_val[29]*q_val[31]*q_val[32] + 2*q_val[30]*q_val[31]*q_val[32] + -q_val[41]*q_val[42]*q_val[43] + q_val[41]*q_val[42]*q_val[44] + q_val[41]*q_val[43]*q_val[44] + 2*q_val[42]*q_val[43]*q_val[44] + -q_val[53]*q_val[54]*q_val[55] + q_val[53]*q_val[54]*q_val[56] + q_val[53]*q_val[55]*q_val[56] + 2*q_val[54]*q_val[55]*q_val[56] + -q_val[104]*q_val[108]*q_val[112] + q_val[104]*q_val[108]*q_val[121] + q_val[104]*q_val[112]*q_val[121] + 2*q_val[108]*q_val[112]*q_val[121]
                # 4. 归一化 (减去理论最小值)
                normalized_base_energy = total_real_energy - self.target_min_energy
               # normalized_base_energy = total_real_energy + 349
            except Exception as e:
                print(f"能量计算警告: {e}")
                normalized_base_energy = 999.0

            print(f"Iter {k + 1}: 电路能量(归一化)={normalized_base_energy:.1f} | ADMM总能量={solution_energy:.1f}")

            if abs(normalized_base_energy) < abs(best_valid_energy):
                best_valid_energy = normalized_base_energy
                best_solution = q_val

            # --- y-update & u-update ---
            for idx, (i, j, k_idx, coeff) in enumerate(self.triplets):
                prod = q_val[i] * q_val[j]
                self.y[idx] = 0.8 * prod + 0.2 * self.y[idx]
                self.u[idx] += (self.y[idx] - prod)

        return best_solution, best_valid_energy


# ==========================================
# 2. 执行脚本
# ==========================================

client = FixstarsClient()
client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
client.parameters.timeout = 5000

# 【核心】全局唯一定义 q
gen = SymbolGenerator(IsingPoly)
q = gen.array(124)

# 1. 粘贴你的三次项列表
cubic_terms_list = [
    '-q[17]*q[18]*q[19]',
    'q[17]*q[18]*q[20]',
    'q[17]*q[19]*q[20]',
    '2*q[18]*q[19]*q[20]',
    '-q[29]*q[30]*q[31]',
    'q[29]*q[30]*q[32]',
    'q[29]*q[31]*q[32]',
    '2*q[30]*q[31]*q[32]',
    '-q[41]*q[42]*q[43]',
    'q[41]*q[42]*q[44]',
    'q[41]*q[43]*q[44]',
    '2*q[42]*q[43]*q[44]',
    '-q[53]*q[54]*q[55]',
    'q[53]*q[54]*q[56]',
    'q[53]*q[55]*q[56]',
    '2*q[54]*q[55]*q[56]',
    '-q[104]*q[108]*q[112]',
    'q[104]*q[108]*q[121]',
    'q[104]*q[112]*q[121]',
    '2*q[108]*q[112]*q[121]'
]

# 2. 粘贴你的 f_base
f_base = q[0]*q[1] + -2*q[0]*q[9] + -2*q[1]*q[9] + q[0] + q[1] + -2*q[9] + q[0]*q[1] + -2*q[0]*q[10] + -2*q[1]*q[10] + -q[0] + -q[1] + 2*q[10] + 2*q[10]*q[11] + q[9]*q[11] + -2*q[9]*q[12] + -2*q[11]*q[12] + -q[9] + -q[11] + 2*q[12] + q[12]*q[8] + -2*q[12]*q[13] + -2*q[8]*q[13] + q[12] + q[8] + -2*q[13] + q[12]*q[8] + -2*q[12]*q[14] + -2*q[8]*q[14] + -q[12] + -q[8] + 2*q[14] + 2*q[14]*q[15] + q[13]*q[15] + -2*q[13]*q[16] + -2*q[15]*q[16] + -q[13] + -q[15] + 2*q[16] + q[0]*q[1] + -2*q[0]*q[17] + -2*q[1]*q[17] + -q[0] + -q[1] + 2*q[17] + q[0]*q[8] + -2*q[0]*q[18] + -2*q[8]*q[18] + -q[0] + -q[8] + 2*q[18] + q[1]*q[8] + -2*q[1]*q[19] + -2*q[8]*q[19] + -q[1] + -q[8] + 2*q[19] + 5 + q[17] + -4*q[20] + -2*q[17]*q[20] + -q[18]*q[19] + -q[18]*q[20] + -q[19]*q[20] + q[2]*q[3] + -2*q[2]*q[21] + -2*q[3]*q[21] + q[2] + q[3] + -2*q[21] + q[2]*q[3] + -2*q[2]*q[22] + -2*q[3]*q[22] + -q[2] + -q[3] + 2*q[22] + 2*q[22]*q[23] + q[21]*q[23] + -2*q[21]*q[24] + -2*q[23]*q[24] + -q[21] + -q[23] + 2*q[24] + q[24]*q[20] + -2*q[24]*q[25] + -2*q[20]*q[25] + q[24] + q[20] + -2*q[25] + q[24]*q[20] + -2*q[24]*q[26] + -2*q[20]*q[26] + -q[24] + -q[20] + 2*q[26] + 2*q[26]*q[27] + q[25]*q[27] + -2*q[25]*q[28] + -2*q[27]*q[28] + -q[25] + -q[27] + 2*q[28] + q[2]*q[3] + -2*q[2]*q[29] + -2*q[3]*q[29] + -q[2] + -q[3] + 2*q[29] + q[2]*q[20] + -2*q[2]*q[30] + -2*q[20]*q[30] + -q[2] + -q[20] + 2*q[30] + q[3]*q[20] + -2*q[3]*q[31] + -2*q[20]*q[31] + -q[3] + -q[20] + 2*q[31] + 5 + q[29] + -4*q[32] + -2*q[29]*q[32] + -q[30]*q[31] + -q[30]*q[32] + -q[31]*q[32] + q[4]*q[5] + -2*q[4]*q[33] + -2*q[5]*q[33] + q[4] + q[5] + -2*q[33] + q[4]*q[5] + -2*q[4]*q[34] + -2*q[5]*q[34] + -q[4] + -q[5] + 2*q[34] + 2*q[34]*q[35] + q[33]*q[35] + -2*q[33]*q[36] + -2*q[35]*q[36] + -q[33] + -q[35] + 2*q[36] + q[36]*q[32] + -2*q[36]*q[37] + -2*q[32]*q[37] + q[36] + q[32] + -2*q[37] + q[36]*q[32] + -2*q[36]*q[38] + -2*q[32]*q[38] + -q[36] + -q[32] + 2*q[38] + 2*q[38]*q[39] + q[37]*q[39] + -2*q[37]*q[40] + -2*q[39]*q[40] + -q[37] + -q[39] + 2*q[40] + q[4]*q[5] + -2*q[4]*q[41] + -2*q[5]*q[41] + -q[4] + -q[5] + 2*q[41] + q[4]*q[32] + -2*q[4]*q[42] + -2*q[32]*q[42] + -q[4] + -q[32] + 2*q[42] + q[5]*q[32] + -2*q[5]*q[43] + -2*q[32]*q[43] + -q[5] + -q[32] + 2*q[43] + 5 + q[41] + -4*q[44] + -2*q[41]*q[44] + -q[42]*q[43] + -q[42]*q[44] + -q[43]*q[44] + q[6]*q[7] + -2*q[6]*q[45] + -2*q[7]*q[45] + q[6] + q[7] + -2*q[45] + q[6]*q[7] + -2*q[6]*q[46] + -2*q[7]*q[46] + -q[6] + -q[7] + 2*q[46] + 2*q[46]*q[47] + q[45]*q[47] + -2*q[45]*q[48] + -2*q[47]*q[48] + -q[45] + -q[47] + 2*q[48] + q[48]*q[44] + -2*q[48]*q[49] + -2*q[44]*q[49] + q[48] + q[44] + -2*q[49] + q[48]*q[44] + -2*q[48]*q[50] + -2*q[44]*q[50] + -q[48] + -q[44] + 2*q[50] + 2*q[50]*q[51] + q[49]*q[51] + -2*q[49]*q[52] + -2*q[51]*q[52] + -q[49] + -q[51] + 2*q[52] + q[6]*q[7] + -2*q[6]*q[53] + -2*q[7]*q[53] + -q[6] + -q[7] + 2*q[53] + q[6]*q[44] + -2*q[6]*q[54] + -2*q[44]*q[54] + -q[6] + -q[44] + 2*q[54] + q[7]*q[44] + -2*q[7]*q[55] + -2*q[44]*q[55] + -q[7] + -q[44] + 2*q[55] + 5 + q[53] + -4*q[56] + -2*q[53]*q[56] + -q[54]*q[55] + -q[54]*q[56] + -q[55]*q[56] + q[0]*q[1] + -2*q[0]*q[57] + -2*q[1]*q[57] + -q[0] + -q[1] + 2*q[57] + q[2]*q[3] + -2*q[2]*q[58] + -2*q[3]*q[58] + -q[2] + -q[3] + 2*q[58] + q[4]*q[5] + -2*q[4]*q[59] + -2*q[5]*q[59] + -q[4] + -q[5] + 2*q[59] + q[6]*q[7] + -2*q[6]*q[60] + -2*q[7]*q[60] + -q[6] + -q[7] + 2*q[60] + q[0]*q[1] + -2*q[0]*q[61] + -2*q[1]*q[61] + q[0] + q[1] + -2*q[61] + q[0]*q[1] + -2*q[0]*q[62] + -2*q[1]*q[62] + -q[0] + -q[1] + 2*q[62] + 2*q[62]*q[63] + q[61]*q[63] + -2*q[61]*q[64] + -2*q[63]*q[64] + -q[61] + -q[63] + 2*q[64] + q[2]*q[3] + -2*q[2]*q[65] + -2*q[3]*q[65] + q[2] + q[3] + -2*q[65] + q[2]*q[3] + -2*q[2]*q[66] + -2*q[3]*q[66] + -q[2] + -q[3] + 2*q[66] + 2*q[66]*q[67] + q[65]*q[67] + -2*q[65]*q[68] + -2*q[67]*q[68] + -q[65] + -q[67] + 2*q[68] + q[4]*q[5] + -2*q[4]*q[69] + -2*q[5]*q[69] + q[4] + q[5] + -2*q[69] + q[4]*q[5] + -2*q[4]*q[70] + -2*q[5]*q[70] + -q[4] + -q[5] + 2*q[70] + 2*q[70]*q[71] + q[69]*q[71] + -2*q[69]*q[72] + -2*q[71]*q[72] + -q[69] + -q[71] + 2*q[72] + q[6]*q[7] + -2*q[6]*q[73] + -2*q[7]*q[73] + q[6] + q[7] + -2*q[73] + q[6]*q[7] + -2*q[6]*q[74] + -2*q[7]*q[74] + -q[6] + -q[7] + 2*q[74] + 2*q[74]*q[75] + q[73]*q[75] + -2*q[73]*q[76] + -2*q[75]*q[76] + -q[73] + -q[75] + 2*q[76] + q[64]*q[8] + -2*q[64]*q[77] + -2*q[8]*q[77] + -q[64] + -q[8] + 2*q[77] + q[57]*q[77] + -2*q[57]*q[78] + -2*q[77]*q[78] + q[57] + q[77] + -2*q[78] + q[68]*q[78] + -2*q[68]*q[79] + -2*q[78]*q[79] + -q[68] + -q[78] + 2*q[79] + q[58]*q[79] + -2*q[58]*q[80] + -2*q[79]*q[80] + q[58] + q[79] + -2*q[80] + q[72]*q[80] + -2*q[72]*q[81] + -2*q[80]*q[81] + -q[72] + -q[80] + 2*q[81] + q[59]*q[81] + -2*q[59]*q[82] + -2*q[81]*q[82] + q[59] + q[81] + -2*q[82] + q[76]*q[82] + -2*q[76]*q[83] + -2*q[82]*q[83] + -q[76] + -q[82] + 2*q[83] + q[60]*q[83] + -2*q[60]*q[84] + -2*q[83]*q[84] + q[60] + q[83] + -2*q[84] + q[64]*q[8] + -2*q[64]*q[85] + -2*q[8]*q[85] + q[64] + q[8] + -2*q[85] + q[64]*q[8] + -2*q[64]*q[86] + -2*q[8]*q[86] + -q[64] + -q[8] + 2*q[86] + 2*q[86]*q[87] + q[85]*q[87] + -2*q[85]*q[88] + -2*q[87]*q[88] + -q[85] + -q[87] + 2*q[88] + q[68]*q[78] + -2*q[68]*q[89] + -2*q[78]*q[89] + q[68] + q[78] + -2*q[89] + q[68]*q[78] + -2*q[68]*q[90] + -2*q[78]*q[90] + -q[68] + -q[78] + 2*q[90] + 2*q[90]*q[91] + q[89]*q[91] + -2*q[89]*q[92] + -2*q[91]*q[92] + -q[89] + -q[91] + 2*q[92] + q[72]*q[80] + -2*q[72]*q[93] + -2*q[80]*q[93] + q[72] + q[80] + -2*q[93] + q[72]*q[80] + -2*q[72]*q[94] + -2*q[80]*q[94] + -q[72] + -q[80] + 2*q[94] + 2*q[94]*q[95] + q[93]*q[95] + -2*q[93]*q[96] + -2*q[95]*q[96] + -q[93] + -q[95] + 2*q[96] + q[76]*q[82] + -2*q[76]*q[97] + -2*q[82]*q[97] + q[76] + q[82] + -2*q[97] + q[76]*q[82] + -2*q[76]*q[98] + -2*q[82]*q[98] + -q[76] + -q[82] + 2*q[98] + 2*q[98]*q[99] + q[97]*q[99] + -2*q[97]*q[100] + -2*q[99]*q[100] + -q[97] + -q[99] + 2*q[100] + q[16]*q[88] + -2*q[16]*q[101] + -2*q[88]*q[101] + q[16] + q[88] + -2*q[101] + q[16]*q[88] + -2*q[16]*q[102] + -2*q[88]*q[102] + -q[16] + -q[88] + 2*q[102] + 2*q[102]*q[103] + q[101]*q[103] + -2*q[101]*q[104] + -2*q[103]*q[104] + -q[101] + -q[103] + 2*q[104] + q[28]*q[92] + -2*q[28]*q[105] + -2*q[92]*q[105] + q[28] + q[92] + -2*q[105] + q[28]*q[92] + -2*q[28]*q[106] + -2*q[92]*q[106] + -q[28] + -q[92] + 2*q[106] + 2*q[106]*q[107] + q[105]*q[107] + -2*q[105]*q[108] + -2*q[107]*q[108] + -q[105] + -q[107] + 2*q[108] + q[40]*q[96] + -2*q[40]*q[109] + -2*q[96]*q[109] + q[40] + q[96] + -2*q[109] + q[40]*q[96] + -2*q[40]*q[110] + -2*q[96]*q[110] + -q[40] + -q[96] + 2*q[110] + 2*q[110]*q[111] + q[109]*q[111] + -2*q[109]*q[112] + -2*q[111]*q[112] + -q[109] + -q[111] + 2*q[112] + q[52]*q[100] + -2*q[52]*q[113] + -2*q[100]*q[113] + q[52] + q[100] + -2*q[113] + q[52]*q[100] + -2*q[52]*q[114] + -2*q[100]*q[114] + -q[52] + -q[100] + 2*q[114] + 2*q[114]*q[115] + q[113]*q[115] + -2*q[113]*q[116] + -2*q[115]*q[116] + -q[113] + -q[115] + 2*q[116] + q[56]*q[84] + -2*q[56]*q[117] + -2*q[84]*q[117] + q[56] + q[84] + -2*q[117] + q[56]*q[84] + -2*q[56]*q[118] + -2*q[84]*q[118] + -q[56] + -q[84] + 2*q[118] + 2*q[118]*q[119] + q[117]*q[119] + -2*q[117]*q[120] + -2*q[119]*q[120] + -q[117] + -q[119] + 2*q[120] + 5 + q[104] + -4*q[121] + -2*q[104]*q[121] + -q[108]*q[112] + -q[108]*q[121] + -q[112]*q[121] + q[116]*q[120] + -2*q[116]*q[122] + -2*q[120]*q[122] + q[116] + q[120] + -2*q[122] + q[121]*q[122] + -2*q[121]*q[123] + -2*q[122]*q[123] + q[121] + q[122] + -2*q[123]

# 3. 能量偏移
THEORETICAL_MIN_ENERGY = -309

# 4. 固定变量
manual_fixed_vars = {
    123: -1
}

# ==========================================
# 3. 执行
# ==========================================

admm = ADMMSolver(
    client,
    f_base,
    cubic_terms_list,
    q_array=q,  # 【核心修复】传入全局 q
    rho=2.0,
    fixed_vars=manual_fixed_vars,
    target_min_energy=THEORETICAL_MIN_ENERGY
)

final_q_values, final_energy = admm.solve(max_iter=15)

# ... (上面的代码保持不变)

print("\n=== 最终结果分析 ===")
if final_q_values is not None:
    print(f"最优解的电路归一化能量: {final_energy:.2f}")
    if abs(final_energy) < 0.1:
        print("✅ 完美！能量归零，电路逻辑完全满足！")
    else:
        print(f"⚠️ 警告：能量未归零 (Diff={final_energy:.2f})，可能存在违反的约束。")

    print("\n变量检查:")
    for idx, target in manual_fixed_vars.items():
        val = 1 if final_q_values[idx] > 0 else -1
        res = "OK" if val == target else "FAIL"
        print(f"  q[{idx}]: {val} (目标{target}) -> {res}")

    # ==============================================
    # ⬇️⬇️⬇️ 在这里添加代码输出完整的 q_val ⬇️⬇️⬇️
    # ==============================================

    print("\n=== 最优解 q_val 详细数据 ===")

    # 方式1：按索引打印每个变量 (Ising值: 1 或 -1)
    for i, val in enumerate(final_q_values):
        spin_val = 1 if val > 0 else -1
        print(f"q[{i}] = {spin_val}")

    # 方式2：打印成可以直接复制的列表
    all_values = [1 if x > 0 else -1 for x in final_q_values]
    print(f"\n完整列表 (用于复制): {all_values}")

    # ==============================================
    # ⬆️⬆️⬆️ 修改结束 ⬆️⬆️⬆️
    # ==============================================

else:
    print("未找到解。")