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
                total_real_energy = 1 + -0.5*q_val[2] + 0.5*q_val[0]*q_val[2] + 0.5*q_val[1]*q_val[2] + 1 + -0.5*q_val[3] + 0.5*q_val[0]*q_val[3] + 0.5*q_val[2]*q_val[3] + 1 + -0.5*q_val[4] + 0.5*q_val[1]*q_val[4] + 0.5*q_val[2]*q_val[4] + 1 + -0.5*q_val[5] + 0.5*q_val[3]*q_val[5] + 0.5*q_val[4]*q_val[5] + 1 + -0.5*q_val[8] + 0.5*q_val[6]*q_val[8] + 0.5*q_val[7]*q_val[8] + 1 + -0.5*q_val[9] + 0.5*q_val[6]*q_val[9] + 0.5*q_val[8]*q_val[9] + 1 + -0.5*q_val[10] + 0.5*q_val[7]*q_val[10] + 0.5*q_val[8]*q_val[10] + 1 + -0.5*q_val[11] + 0.5*q_val[9]*q_val[11] + 0.5*q_val[10]*q_val[11] + 1 + -0.5*q_val[14] + 0.5*q_val[12]*q_val[14] + 0.5*q_val[13]*q_val[14] + 1 + -0.5*q_val[15] + 0.5*q_val[12]*q_val[15] + 0.5*q_val[14]*q_val[15] + 1 + -0.5*q_val[16] + 0.5*q_val[13]*q_val[16] + 0.5*q_val[14]*q_val[16] + 1 + -0.5*q_val[17] + 0.5*q_val[15]*q_val[17] + 0.5*q_val[16]*q_val[17] + 1 + -0.5*q_val[20] + 0.5*q_val[18]*q_val[20] + 0.5*q_val[19]*q_val[20] + 1 + -0.5*q_val[21] + 0.5*q_val[18]*q_val[21] + 0.5*q_val[20]*q_val[21] + 1 + -0.5*q_val[22] + 0.5*q_val[19]*q_val[22] + 0.5*q_val[20]*q_val[22] + 1 + -0.5*q_val[23] + 0.5*q_val[21]*q_val[23] + 0.5*q_val[22]*q_val[23] + 1 + -0.5*q_val[26] + 0.5*q_val[24]*q_val[26] + 0.5*q_val[25]*q_val[26] + 1 + -0.5*q_val[27] + 0.5*q_val[24]*q_val[27] + 0.5*q_val[26]*q_val[27] + 1 + -0.5*q_val[28] + 0.5*q_val[25]*q_val[28] + 0.5*q_val[26]*q_val[28] + 1 + -0.5*q_val[29] + 0.5*q_val[27]*q_val[29] + 0.5*q_val[28]*q_val[29] + 1 + -0.5*q_val[32] + 0.5*q_val[30]*q_val[32] + 0.5*q_val[31]*q_val[32] + 1 + -0.5*q_val[33] + 0.5*q_val[30]*q_val[33] + 0.5*q_val[32]*q_val[33] + 1 + -0.5*q_val[34] + 0.5*q_val[31]*q_val[34] + 0.5*q_val[32]*q_val[34] + 1 + -0.5*q_val[35] + 0.5*q_val[33]*q_val[35] + 0.5*q_val[34]*q_val[35] + 1 + -0.5*q_val[38] + 0.5*q_val[36]*q_val[38] + 0.5*q_val[37]*q_val[38] + 1 + -0.5*q_val[39] + 0.5*q_val[36]*q_val[39] + 0.5*q_val[38]*q_val[39] + 1 + -0.5*q_val[40] + 0.5*q_val[37]*q_val[40] + 0.5*q_val[38]*q_val[40] + 1 + -0.5*q_val[41] + 0.5*q_val[39]*q_val[41] + 0.5*q_val[40]*q_val[41] + 1 + -0.5*q_val[44] + 0.5*q_val[42]*q_val[44] + 0.5*q_val[43]*q_val[44] + 1 + -0.5*q_val[45] + 0.5*q_val[42]*q_val[45] + 0.5*q_val[44]*q_val[45] + 1 + -0.5*q_val[46] + 0.5*q_val[43]*q_val[46] + 0.5*q_val[44]*q_val[46] + 1 + -0.5*q_val[47] + 0.5*q_val[45]*q_val[47] + 0.5*q_val[46]*q_val[47] + 1 + -0.5*q_val[50] + 0.5*q_val[48]*q_val[50] + 0.5*q_val[49]*q_val[50] + 1 + -0.5*q_val[51] + 0.5*q_val[48]*q_val[51] + 0.5*q_val[50]*q_val[51] + 1 + -0.5*q_val[52] + 0.5*q_val[49]*q_val[52] + 0.5*q_val[50]*q_val[52] + 1 + -0.5*q_val[53] + 0.5*q_val[51]*q_val[53] + 0.5*q_val[52]*q_val[53] + 1 + -0.5*q_val[56] + 0.5*q_val[54]*q_val[56] + 0.5*q_val[55]*q_val[56] + 1 + -0.5*q_val[57] + 0.5*q_val[54]*q_val[57] + 0.5*q_val[56]*q_val[57] + 1 + -0.5*q_val[58] + 0.5*q_val[55]*q_val[58] + 0.5*q_val[56]*q_val[58] + 1 + -0.5*q_val[59] + 0.5*q_val[57]*q_val[59] + 0.5*q_val[58]*q_val[59] + 1 + -0.5*q_val[62] + 0.5*q_val[60]*q_val[62] + 0.5*q_val[61]*q_val[62] + 1 + -0.5*q_val[63] + 0.5*q_val[60]*q_val[63] + 0.5*q_val[62]*q_val[63] + 1 + -0.5*q_val[64] + 0.5*q_val[61]*q_val[64] + 0.5*q_val[62]*q_val[64] + 1 + -0.5*q_val[65] + 0.5*q_val[63]*q_val[65] + 0.5*q_val[64]*q_val[65] + 1 + -0.5*q_val[68] + 0.5*q_val[66]*q_val[68] + 0.5*q_val[67]*q_val[68] + 1 + -0.5*q_val[69] + 0.5*q_val[66]*q_val[69] + 0.5*q_val[68]*q_val[69] + 1 + -0.5*q_val[70] + 0.5*q_val[67]*q_val[70] + 0.5*q_val[68]*q_val[70] + 1 + -0.5*q_val[71] + 0.5*q_val[69]*q_val[71] + 0.5*q_val[70]*q_val[71] + 1 + -0.5*q_val[74] + 0.5*q_val[72]*q_val[74] + 0.5*q_val[73]*q_val[74] + 1 + -0.5*q_val[75] + 0.5*q_val[72]*q_val[75] + 0.5*q_val[74]*q_val[75] + 1 + -0.5*q_val[76] + 0.5*q_val[73]*q_val[76] + 0.5*q_val[74]*q_val[76] + 1 + -0.5*q_val[77] + 0.5*q_val[75]*q_val[77] + 0.5*q_val[76]*q_val[77] + 1 + -0.5*q_val[80] + 0.5*q_val[78]*q_val[80] + 0.5*q_val[79]*q_val[80] + 1 + -0.5*q_val[81] + 0.5*q_val[78]*q_val[81] + 0.5*q_val[80]*q_val[81] + 1 + -0.5*q_val[82] + 0.5*q_val[79]*q_val[82] + 0.5*q_val[80]*q_val[82] + 1 + -0.5*q_val[83] + 0.5*q_val[81]*q_val[83] + 0.5*q_val[82]*q_val[83] + 1 + -0.5*q_val[86] + 0.5*q_val[84]*q_val[86] + 0.5*q_val[85]*q_val[86] + 1 + -0.5*q_val[87] + 0.5*q_val[84]*q_val[87] + 0.5*q_val[86]*q_val[87] + 1 + -0.5*q_val[88] + 0.5*q_val[85]*q_val[88] + 0.5*q_val[86]*q_val[88] + 1 + -0.5*q_val[89] + 0.5*q_val[87]*q_val[89] + 0.5*q_val[88]*q_val[89] + 1 + -0.5*q_val[92] + 0.5*q_val[90]*q_val[92] + 0.5*q_val[91]*q_val[92] + 1 + -0.5*q_val[93] + 0.5*q_val[90]*q_val[93] + 0.5*q_val[92]*q_val[93] + 1 + -0.5*q_val[94] + 0.5*q_val[91]*q_val[94] + 0.5*q_val[92]*q_val[94] + 1 + -0.5*q_val[95] + 0.5*q_val[93]*q_val[95] + 0.5*q_val[94]*q_val[95] + 1 + -0.5*q_val[98] + 0.5*q_val[96]*q_val[98] + 0.5*q_val[97]*q_val[98] + 1 + -0.5*q_val[99] + 0.5*q_val[96]*q_val[99] + 0.5*q_val[98]*q_val[99] + 1 + -0.5*q_val[100] + 0.5*q_val[97]*q_val[100] + 0.5*q_val[98]*q_val[100] + 1 + -0.5*q_val[101] + 0.5*q_val[99]*q_val[101] + 0.5*q_val[100]*q_val[101] + 1 + -0.5*q_val[104] + 0.5*q_val[102]*q_val[104] + 0.5*q_val[103]*q_val[104] + 1 + -0.5*q_val[105] + 0.5*q_val[102]*q_val[105] + 0.5*q_val[104]*q_val[105] + 1 + -0.5*q_val[106] + 0.5*q_val[103]*q_val[106] + 0.5*q_val[104]*q_val[106] + 1 + -0.5*q_val[107] + 0.5*q_val[105]*q_val[107] + 0.5*q_val[106]*q_val[107] + 1 + -0.5*q_val[110] + 0.5*q_val[108]*q_val[110] + 0.5*q_val[109]*q_val[110] + 1 + -0.5*q_val[111] + 0.5*q_val[108]*q_val[111] + 0.5*q_val[110]*q_val[111] + 1 + -0.5*q_val[112] + 0.5*q_val[109]*q_val[112] + 0.5*q_val[110]*q_val[112] + 1 + -0.5*q_val[113] + 0.5*q_val[111]*q_val[113] + 0.5*q_val[112]*q_val[113] + 1 + -0.5*q_val[116] + 0.5*q_val[114]*q_val[116] + 0.5*q_val[115]*q_val[116] + 1 + -0.5*q_val[117] + 0.5*q_val[114]*q_val[117] + 0.5*q_val[116]*q_val[117] + 1 + -0.5*q_val[118] + 0.5*q_val[115]*q_val[118] + 0.5*q_val[116]*q_val[118] + 1 + -0.5*q_val[119] + 0.5*q_val[117]*q_val[119] + 0.5*q_val[118]*q_val[119] + 1 + -0.5*q_val[122] + 0.5*q_val[120]*q_val[122] + 0.5*q_val[121]*q_val[122] + 1 + -0.5*q_val[123] + 0.5*q_val[120]*q_val[123] + 0.5*q_val[122]*q_val[123] + 1 + -0.5*q_val[124] + 0.5*q_val[121]*q_val[124] + 0.5*q_val[122]*q_val[124] + 1 + -0.5*q_val[125] + 0.5*q_val[123]*q_val[125] + 0.5*q_val[124]*q_val[125] + 1 + -0.5*q_val[128] + 0.5*q_val[126]*q_val[128] + 0.5*q_val[127]*q_val[128] + 1 + -0.5*q_val[129] + 0.5*q_val[126]*q_val[129] + 0.5*q_val[128]*q_val[129] + 1 + -0.5*q_val[130] + 0.5*q_val[127]*q_val[130] + 0.5*q_val[128]*q_val[130] + 1 + -0.5*q_val[131] + 0.5*q_val[129]*q_val[131] + 0.5*q_val[130]*q_val[131] + 1 + -0.5*q_val[134] + 0.5*q_val[132]*q_val[134] + 0.5*q_val[133]*q_val[134] + 1 + -0.5*q_val[135] + 0.5*q_val[132]*q_val[135] + 0.5*q_val[134]*q_val[135] + 1 + -0.5*q_val[136] + 0.5*q_val[133]*q_val[136] + 0.5*q_val[134]*q_val[136] + 1 + -0.5*q_val[137] + 0.5*q_val[135]*q_val[137] + 0.5*q_val[136]*q_val[137] + 1 + -0.5*q_val[140] + 0.5*q_val[138]*q_val[140] + 0.5*q_val[139]*q_val[140] + 1 + -0.5*q_val[141] + 0.5*q_val[138]*q_val[141] + 0.5*q_val[140]*q_val[141] + 1 + -0.5*q_val[142] + 0.5*q_val[139]*q_val[142] + 0.5*q_val[140]*q_val[142] + 1 + -0.5*q_val[143] + 0.5*q_val[141]*q_val[143] + 0.5*q_val[142]*q_val[143] + 1 + -0.5*q_val[146] + 0.5*q_val[144]*q_val[146] + 0.5*q_val[145]*q_val[146] + 1 + -0.5*q_val[147] + 0.5*q_val[144]*q_val[147] + 0.5*q_val[146]*q_val[147] + 1 + -0.5*q_val[148] + 0.5*q_val[145]*q_val[148] + 0.5*q_val[146]*q_val[148] + 1 + -0.5*q_val[149] + 0.5*q_val[147]*q_val[149] + 0.5*q_val[148]*q_val[149] + 1 + -0.5*q_val[152] + 0.5*q_val[150]*q_val[152] + 0.5*q_val[151]*q_val[152] + 1 + -0.5*q_val[153] + 0.5*q_val[150]*q_val[153] + 0.5*q_val[152]*q_val[153] + 1 + -0.5*q_val[154] + 0.5*q_val[151]*q_val[154] + 0.5*q_val[152]*q_val[154] + 1 + -0.5*q_val[155] + 0.5*q_val[153]*q_val[155] + 0.5*q_val[154]*q_val[155] + 1 + -0.5*q_val[158] + 0.5*q_val[156]*q_val[158] + 0.5*q_val[157]*q_val[158] + 1 + -0.5*q_val[159] + 0.5*q_val[156]*q_val[159] + 0.5*q_val[158]*q_val[159] + 1 + -0.5*q_val[160] + 0.5*q_val[157]*q_val[160] + 0.5*q_val[158]*q_val[160] + 1 + -0.5*q_val[161] + 0.5*q_val[159]*q_val[161] + 0.5*q_val[160]*q_val[161] + 1 + -0.5*q_val[164] + 0.5*q_val[162]*q_val[164] + 0.5*q_val[163]*q_val[164] + 1 + -0.5*q_val[165] + 0.5*q_val[162]*q_val[165] + 0.5*q_val[164]*q_val[165] + 1 + -0.5*q_val[166] + 0.5*q_val[163]*q_val[166] + 0.5*q_val[164]*q_val[166] + 1 + -0.5*q_val[167] + 0.5*q_val[165]*q_val[167] + 0.5*q_val[166]*q_val[167] + 1 + -0.5*q_val[170] + 0.5*q_val[168]*q_val[170] + 0.5*q_val[169]*q_val[170] + 1 + -0.5*q_val[171] + 0.5*q_val[168]*q_val[171] + 0.5*q_val[170]*q_val[171] + 1 + -0.5*q_val[172] + 0.5*q_val[169]*q_val[172] + 0.5*q_val[170]*q_val[172] + 1 + -0.5*q_val[173] + 0.5*q_val[171]*q_val[173] + 0.5*q_val[172]*q_val[173] + 1 + -0.5*q_val[176] + 0.5*q_val[174]*q_val[176] + 0.5*q_val[175]*q_val[176] + 1 + -0.5*q_val[177] + 0.5*q_val[174]*q_val[177] + 0.5*q_val[176]*q_val[177] + 1 + -0.5*q_val[178] + 0.5*q_val[175]*q_val[178] + 0.5*q_val[176]*q_val[178] + 1 + -0.5*q_val[179] + 0.5*q_val[177]*q_val[179] + 0.5*q_val[178]*q_val[179] + 1 + -0.5*q_val[182] + 0.5*q_val[180]*q_val[182] + 0.5*q_val[181]*q_val[182] + 1 + -0.5*q_val[183] + 0.5*q_val[180]*q_val[183] + 0.5*q_val[182]*q_val[183] + 1 + -0.5*q_val[184] + 0.5*q_val[181]*q_val[184] + 0.5*q_val[182]*q_val[184] + 1 + -0.5*q_val[185] + 0.5*q_val[183]*q_val[185] + 0.5*q_val[184]*q_val[185] + 1 + -0.5*q_val[188] + 0.5*q_val[186]*q_val[188] + 0.5*q_val[187]*q_val[188] + 1 + -0.5*q_val[189] + 0.5*q_val[186]*q_val[189] + 0.5*q_val[188]*q_val[189] + 1 + -0.5*q_val[190] + 0.5*q_val[187]*q_val[190] + 0.5*q_val[188]*q_val[190] + 1 + -0.5*q_val[191] + 0.5*q_val[189]*q_val[191] + 0.5*q_val[190]*q_val[191] + 1 + -0.5*q_val[194] + 0.5*q_val[192]*q_val[194] + 0.5*q_val[193]*q_val[194] + 1 + -0.5*q_val[195] + 0.5*q_val[192]*q_val[195] + 0.5*q_val[194]*q_val[195] + 1 + -0.5*q_val[196] + 0.5*q_val[193]*q_val[196] + 0.5*q_val[194]*q_val[196] + 1 + -0.5*q_val[197] + 0.5*q_val[195]*q_val[197] + 0.5*q_val[196]*q_val[197] + 1 + -0.5*q_val[200] + 0.5*q_val[198]*q_val[200] + 0.5*q_val[199]*q_val[200] + 1 + -0.5*q_val[201] + 0.5*q_val[198]*q_val[201] + 0.5*q_val[200]*q_val[201] + 1 + -0.5*q_val[202] + 0.5*q_val[199]*q_val[202] + 0.5*q_val[200]*q_val[202] + 1 + -0.5*q_val[203] + 0.5*q_val[201]*q_val[203] + 0.5*q_val[202]*q_val[203] + 1 + -0.5*q_val[206] + 0.5*q_val[204]*q_val[206] + 0.5*q_val[205]*q_val[206] + 1 + -0.5*q_val[207] + 0.5*q_val[204]*q_val[207] + 0.5*q_val[206]*q_val[207] + 1 + -0.5*q_val[208] + 0.5*q_val[205]*q_val[208] + 0.5*q_val[206]*q_val[208] + 1 + -0.5*q_val[209] + 0.5*q_val[207]*q_val[209] + 0.5*q_val[208]*q_val[209] + 1 + -0.5*q_val[212] + 0.5*q_val[210]*q_val[212] + 0.5*q_val[211]*q_val[212] + 1 + -0.5*q_val[213] + 0.5*q_val[210]*q_val[213] + 0.5*q_val[212]*q_val[213] + 1 + -0.5*q_val[214] + 0.5*q_val[211]*q_val[214] + 0.5*q_val[212]*q_val[214] + 1 + -0.5*q_val[215] + 0.5*q_val[213]*q_val[215] + 0.5*q_val[214]*q_val[215] + 1 + -0.5*q_val[218] + 0.5*q_val[216]*q_val[218] + 0.5*q_val[217]*q_val[218] + 1 + -0.5*q_val[219] + 0.5*q_val[216]*q_val[219] + 0.5*q_val[218]*q_val[219] + 1 + -0.5*q_val[220] + 0.5*q_val[217]*q_val[220] + 0.5*q_val[218]*q_val[220] + 1 + -0.5*q_val[221] + 0.5*q_val[219]*q_val[221] + 0.5*q_val[220]*q_val[221] + 1 + -0.5*q_val[224] + 0.5*q_val[222]*q_val[224] + 0.5*q_val[223]*q_val[224] + 1 + -0.5*q_val[225] + 0.5*q_val[222]*q_val[225] + 0.5*q_val[224]*q_val[225] + 1 + -0.5*q_val[226] + 0.5*q_val[223]*q_val[226] + 0.5*q_val[224]*q_val[226] + 1 + -0.5*q_val[227] + 0.5*q_val[225]*q_val[227] + 0.5*q_val[226]*q_val[227] + 1 + -0.5*q_val[230] + 0.5*q_val[228]*q_val[230] + 0.5*q_val[229]*q_val[230] + 1 + -0.5*q_val[231] + 0.5*q_val[228]*q_val[231] + 0.5*q_val[230]*q_val[231] + 1 + -0.5*q_val[232] + 0.5*q_val[229]*q_val[232] + 0.5*q_val[230]*q_val[232] + 1 + -0.5*q_val[233] + 0.5*q_val[231]*q_val[233] + 0.5*q_val[232]*q_val[233] + 1 + -0.5*q_val[236] + 0.5*q_val[234]*q_val[236] + 0.5*q_val[235]*q_val[236] + 1 + -0.5*q_val[237] + 0.5*q_val[234]*q_val[237] + 0.5*q_val[236]*q_val[237] + 1 + -0.5*q_val[238] + 0.5*q_val[235]*q_val[238] + 0.5*q_val[236]*q_val[238] + 1 + -0.5*q_val[239] + 0.5*q_val[237]*q_val[239] + 0.5*q_val[238]*q_val[239] + 1 + -0.5*q_val[242] + 0.5*q_val[240]*q_val[242] + 0.5*q_val[241]*q_val[242] + 1 + -0.5*q_val[243] + 0.5*q_val[240]*q_val[243] + 0.5*q_val[242]*q_val[243] + 1 + -0.5*q_val[244] + 0.5*q_val[241]*q_val[244] + 0.5*q_val[242]*q_val[244] + 1 + -0.5*q_val[245] + 0.5*q_val[243]*q_val[245] + 0.5*q_val[244]*q_val[245] + 1 + -0.5*q_val[248] + 0.5*q_val[246]*q_val[248] + 0.5*q_val[247]*q_val[248] + 1 + -0.5*q_val[249] + 0.5*q_val[246]*q_val[249] + 0.5*q_val[248]*q_val[249] + 1 + -0.5*q_val[250] + 0.5*q_val[247]*q_val[250] + 0.5*q_val[248]*q_val[250] + 1 + -0.5*q_val[251] + 0.5*q_val[249]*q_val[251] + 0.5*q_val[250]*q_val[251] + 1 + -0.5*q_val[254] + 0.5*q_val[252]*q_val[254] + 0.5*q_val[253]*q_val[254] + 1 + -0.5*q_val[255] + 0.5*q_val[252]*q_val[255] + 0.5*q_val[254]*q_val[255] + 1 + -0.5*q_val[256] + 0.5*q_val[253]*q_val[256] + 0.5*q_val[254]*q_val[256] + 1 + -0.5*q_val[257] + 0.5*q_val[255]*q_val[257] + 0.5*q_val[256]*q_val[257] + 1 + -0.5*q_val[260] + 0.5*q_val[258]*q_val[260] + 0.5*q_val[259]*q_val[260] + 1 + -0.5*q_val[261] + 0.5*q_val[258]*q_val[261] + 0.5*q_val[260]*q_val[261] + 1 + -0.5*q_val[262] + 0.5*q_val[259]*q_val[262] + 0.5*q_val[260]*q_val[262] + 1 + -0.5*q_val[263] + 0.5*q_val[261]*q_val[263] + 0.5*q_val[262]*q_val[263] + 1 + -0.5*q_val[266] + 0.5*q_val[264]*q_val[266] + 0.5*q_val[265]*q_val[266] + 1 + -0.5*q_val[267] + 0.5*q_val[264]*q_val[267] + 0.5*q_val[266]*q_val[267] + 1 + -0.5*q_val[268] + 0.5*q_val[265]*q_val[268] + 0.5*q_val[266]*q_val[268] + 1 + -0.5*q_val[269] + 0.5*q_val[267]*q_val[269] + 0.5*q_val[268]*q_val[269] + 1 + -0.5*q_val[272] + 0.5*q_val[270]*q_val[272] + 0.5*q_val[271]*q_val[272] + 1 + -0.5*q_val[273] + 0.5*q_val[270]*q_val[273] + 0.5*q_val[272]*q_val[273] + 1 + -0.5*q_val[274] + 0.5*q_val[271]*q_val[274] + 0.5*q_val[272]*q_val[274] + 1 + -0.5*q_val[275] + 0.5*q_val[273]*q_val[275] + 0.5*q_val[274]*q_val[275] + 1 + -0.5*q_val[278] + 0.5*q_val[276]*q_val[278] + 0.5*q_val[277]*q_val[278] + 1 + -0.5*q_val[279] + 0.5*q_val[276]*q_val[279] + 0.5*q_val[278]*q_val[279] + 1 + -0.5*q_val[280] + 0.5*q_val[277]*q_val[280] + 0.5*q_val[278]*q_val[280] + 1 + -0.5*q_val[281] + 0.5*q_val[279]*q_val[281] + 0.5*q_val[280]*q_val[281] + 1 + -0.5*q_val[284] + 0.5*q_val[282]*q_val[284] + 0.5*q_val[283]*q_val[284] + 1 + -0.5*q_val[285] + 0.5*q_val[282]*q_val[285] + 0.5*q_val[284]*q_val[285] + 1 + -0.5*q_val[286] + 0.5*q_val[283]*q_val[286] + 0.5*q_val[284]*q_val[286] + 1 + -0.5*q_val[287] + 0.5*q_val[285]*q_val[287] + 0.5*q_val[286]*q_val[287] + 1 + -0.5*q_val[290] + 0.5*q_val[288]*q_val[290] + 0.5*q_val[289]*q_val[290] + 1 + -0.5*q_val[291] + 0.5*q_val[288]*q_val[291] + 0.5*q_val[290]*q_val[291] + 1 + -0.5*q_val[292] + 0.5*q_val[289]*q_val[292] + 0.5*q_val[290]*q_val[292] + 1 + -0.5*q_val[293] + 0.5*q_val[291]*q_val[293] + 0.5*q_val[292]*q_val[293] + 1 + -0.5*q_val[296] + 0.5*q_val[294]*q_val[296] + 0.5*q_val[295]*q_val[296] + 1 + -0.5*q_val[297] + 0.5*q_val[294]*q_val[297] + 0.5*q_val[296]*q_val[297] + 1 + -0.5*q_val[298] + 0.5*q_val[295]*q_val[298] + 0.5*q_val[296]*q_val[298] + 1 + -0.5*q_val[299] + 0.5*q_val[297]*q_val[299] + 0.5*q_val[298]*q_val[299] + 1 + -0.5*q_val[302] + 0.5*q_val[300]*q_val[302] + 0.5*q_val[301]*q_val[302] + 1 + -0.5*q_val[303] + 0.5*q_val[300]*q_val[303] + 0.5*q_val[302]*q_val[303] + 1 + -0.5*q_val[304] + 0.5*q_val[301]*q_val[304] + 0.5*q_val[302]*q_val[304] + 1 + -0.5*q_val[305] + 0.5*q_val[303]*q_val[305] + 0.5*q_val[304]*q_val[305] + 1 + -0.5*q_val[308] + 0.5*q_val[306]*q_val[308] + 0.5*q_val[307]*q_val[308] + 1 + -0.5*q_val[309] + 0.5*q_val[306]*q_val[309] + 0.5*q_val[308]*q_val[309] + 1 + -0.5*q_val[310] + 0.5*q_val[307]*q_val[310] + 0.5*q_val[308]*q_val[310] + 1 + -0.5*q_val[311] + 0.5*q_val[309]*q_val[311] + 0.5*q_val[310]*q_val[311] + 1 + -0.5*q_val[314] + 0.5*q_val[312]*q_val[314] + 0.5*q_val[313]*q_val[314] + 1 + -0.5*q_val[315] + 0.5*q_val[312]*q_val[315] + 0.5*q_val[314]*q_val[315] + 1 + -0.5*q_val[316] + 0.5*q_val[313]*q_val[316] + 0.5*q_val[314]*q_val[316] + 1 + -0.5*q_val[317] + 0.5*q_val[315]*q_val[317] + 0.5*q_val[316]*q_val[317] + 1 + -0.5*q_val[320] + 0.5*q_val[318]*q_val[320] + 0.5*q_val[319]*q_val[320] + 1 + -0.5*q_val[321] + 0.5*q_val[318]*q_val[321] + 0.5*q_val[320]*q_val[321] + 1 + -0.5*q_val[322] + 0.5*q_val[319]*q_val[322] + 0.5*q_val[320]*q_val[322] + 1 + -0.5*q_val[323] + 0.5*q_val[321]*q_val[323] + 0.5*q_val[322]*q_val[323] + 1 + -0.5*q_val[326] + 0.5*q_val[324]*q_val[326] + 0.5*q_val[325]*q_val[326] + 1 + -0.5*q_val[327] + 0.5*q_val[324]*q_val[327] + 0.5*q_val[326]*q_val[327] + 1 + -0.5*q_val[328] + 0.5*q_val[325]*q_val[328] + 0.5*q_val[326]*q_val[328] + 1 + -0.5*q_val[329] + 0.5*q_val[327]*q_val[329] + 0.5*q_val[328]*q_val[329] + 1 + -0.5*q_val[332] + 0.5*q_val[330]*q_val[332] + 0.5*q_val[331]*q_val[332] + 1 + -0.5*q_val[333] + 0.5*q_val[330]*q_val[333] + 0.5*q_val[332]*q_val[333] + 1 + -0.5*q_val[334] + 0.5*q_val[331]*q_val[334] + 0.5*q_val[332]*q_val[334] + 1 + -0.5*q_val[335] + 0.5*q_val[333]*q_val[335] + 0.5*q_val[334]*q_val[335] + 1 + -0.5*q_val[338] + 0.5*q_val[336]*q_val[338] + 0.5*q_val[337]*q_val[338] + 1 + -0.5*q_val[339] + 0.5*q_val[336]*q_val[339] + 0.5*q_val[338]*q_val[339] + 1 + -0.5*q_val[340] + 0.5*q_val[337]*q_val[340] + 0.5*q_val[338]*q_val[340] + 1 + -0.5*q_val[341] + 0.5*q_val[339]*q_val[341] + 0.5*q_val[340]*q_val[341] + 1 + -0.5*q_val[344] + 0.5*q_val[342]*q_val[344] + 0.5*q_val[343]*q_val[344] + 1 + -0.5*q_val[345] + 0.5*q_val[342]*q_val[345] + 0.5*q_val[344]*q_val[345] + 1 + -0.5*q_val[346] + 0.5*q_val[343]*q_val[346] + 0.5*q_val[344]*q_val[346] + 1 + -0.5*q_val[347] + 0.5*q_val[345]*q_val[347] + 0.5*q_val[346]*q_val[347] + 1 + -0.5*q_val[350] + 0.5*q_val[348]*q_val[350] + 0.5*q_val[349]*q_val[350] + 1 + -0.5*q_val[351] + 0.5*q_val[348]*q_val[351] + 0.5*q_val[350]*q_val[351] + 1 + -0.5*q_val[352] + 0.5*q_val[349]*q_val[352] + 0.5*q_val[350]*q_val[352] + 1 + -0.5*q_val[353] + 0.5*q_val[351]*q_val[353] + 0.5*q_val[352]*q_val[353] + 1 + -0.5*q_val[356] + 0.5*q_val[354]*q_val[356] + 0.5*q_val[355]*q_val[356] + 1 + -0.5*q_val[357] + 0.5*q_val[354]*q_val[357] + 0.5*q_val[356]*q_val[357] + 1 + -0.5*q_val[358] + 0.5*q_val[355]*q_val[358] + 0.5*q_val[356]*q_val[358] + 1 + -0.5*q_val[359] + 0.5*q_val[357]*q_val[359] + 0.5*q_val[358]*q_val[359] + 1 + -0.5*q_val[362] + 0.5*q_val[360]*q_val[362] + 0.5*q_val[361]*q_val[362] + 1 + -0.5*q_val[363] + 0.5*q_val[360]*q_val[363] + 0.5*q_val[362]*q_val[363] + 1 + -0.5*q_val[364] + 0.5*q_val[361]*q_val[364] + 0.5*q_val[362]*q_val[364] + 1 + -0.5*q_val[365] + 0.5*q_val[363]*q_val[365] + 0.5*q_val[364]*q_val[365] + 1 + -0.5*q_val[368] + 0.5*q_val[366]*q_val[368] + 0.5*q_val[367]*q_val[368] + 1 + -0.5*q_val[369] + 0.5*q_val[366]*q_val[369] + 0.5*q_val[368]*q_val[369] + 1 + -0.5*q_val[370] + 0.5*q_val[367]*q_val[370] + 0.5*q_val[368]*q_val[370] + 1 + -0.5*q_val[371] + 0.5*q_val[369]*q_val[371] + 0.5*q_val[370]*q_val[371] + 1 + -0.5*q_val[374] + 0.5*q_val[372]*q_val[374] + 0.5*q_val[373]*q_val[374] + 1 + -0.5*q_val[375] + 0.5*q_val[372]*q_val[375] + 0.5*q_val[374]*q_val[375] + 1 + -0.5*q_val[376] + 0.5*q_val[373]*q_val[376] + 0.5*q_val[374]*q_val[376] + 1 + -0.5*q_val[377] + 0.5*q_val[375]*q_val[377] + 0.5*q_val[376]*q_val[377] + 1 + -0.5*q_val[380] + 0.5*q_val[378]*q_val[380] + 0.5*q_val[379]*q_val[380] + 1 + -0.5*q_val[381] + 0.5*q_val[378]*q_val[381] + 0.5*q_val[380]*q_val[381] + 1 + -0.5*q_val[382] + 0.5*q_val[379]*q_val[382] + 0.5*q_val[380]*q_val[382] + 1 + -0.5*q_val[383] + 0.5*q_val[381]*q_val[383] + 0.5*q_val[382]*q_val[383] + 1 + -0.5*q_val[386] + 0.5*q_val[384]*q_val[386] + 0.5*q_val[385]*q_val[386] + 1 + -0.5*q_val[387] + 0.5*q_val[384]*q_val[387] + 0.5*q_val[386]*q_val[387] + 1 + -0.5*q_val[388] + 0.5*q_val[385]*q_val[388] + 0.5*q_val[386]*q_val[388] + 1 + -0.5*q_val[389] + 0.5*q_val[387]*q_val[389] + 0.5*q_val[388]*q_val[389] + 1 + -0.5*q_val[392] + 0.5*q_val[390]*q_val[392] + 0.5*q_val[391]*q_val[392] + 1 + -0.5*q_val[393] + 0.5*q_val[390]*q_val[393] + 0.5*q_val[392]*q_val[393] + 1 + -0.5*q_val[394] + 0.5*q_val[391]*q_val[394] + 0.5*q_val[392]*q_val[394] + 1 + -0.5*q_val[395] + 0.5*q_val[393]*q_val[395] + 0.5*q_val[394]*q_val[395] + 1 + -0.5*q_val[398] + 0.5*q_val[396]*q_val[398] + 0.5*q_val[397]*q_val[398] + 1 + -0.5*q_val[399] + 0.5*q_val[396]*q_val[399] + 0.5*q_val[398]*q_val[399] + 1 + -0.5*q_val[400] + 0.5*q_val[397]*q_val[400] + 0.5*q_val[398]*q_val[400] + 1 + -0.5*q_val[401] + 0.5*q_val[399]*q_val[401] + 0.5*q_val[400]*q_val[401] + 1 + -0.5*q_val[404] + 0.5*q_val[402]*q_val[404] + 0.5*q_val[403]*q_val[404] + 1 + -0.5*q_val[405] + 0.5*q_val[402]*q_val[405] + 0.5*q_val[404]*q_val[405] + 1 + -0.5*q_val[406] + 0.5*q_val[403]*q_val[406] + 0.5*q_val[404]*q_val[406] + 1 + -0.5*q_val[407] + 0.5*q_val[405]*q_val[407] + 0.5*q_val[406]*q_val[407] + 1 + -0.5*q_val[410] + 0.5*q_val[408]*q_val[410] + 0.5*q_val[409]*q_val[410] + 1 + -0.5*q_val[411] + 0.5*q_val[408]*q_val[411] + 0.5*q_val[410]*q_val[411] + 1 + -0.5*q_val[412] + 0.5*q_val[409]*q_val[412] + 0.5*q_val[410]*q_val[412] + 1 + -0.5*q_val[413] + 0.5*q_val[411]*q_val[413] + 0.5*q_val[412]*q_val[413] + 1 + -0.5*q_val[416] + 0.5*q_val[414]*q_val[416] + 0.5*q_val[415]*q_val[416] + 1 + -0.5*q_val[417] + 0.5*q_val[414]*q_val[417] + 0.5*q_val[416]*q_val[417] + 1 + -0.5*q_val[418] + 0.5*q_val[415]*q_val[418] + 0.5*q_val[416]*q_val[418] + 1 + -0.5*q_val[419] + 0.5*q_val[417]*q_val[419] + 0.5*q_val[418]*q_val[419] + 1 + -0.5*q_val[422] + 0.5*q_val[420]*q_val[422] + 0.5*q_val[421]*q_val[422] + 1 + -0.5*q_val[423] + 0.5*q_val[420]*q_val[423] + 0.5*q_val[422]*q_val[423] + 1 + -0.5*q_val[424] + 0.5*q_val[421]*q_val[424] + 0.5*q_val[422]*q_val[424] + 1 + -0.5*q_val[425] + 0.5*q_val[423]*q_val[425] + 0.5*q_val[424]*q_val[425] + 1 + -0.5*q_val[428] + 0.5*q_val[426]*q_val[428] + 0.5*q_val[427]*q_val[428] + 1 + -0.5*q_val[429] + 0.5*q_val[426]*q_val[429] + 0.5*q_val[428]*q_val[429] + 1 + -0.5*q_val[430] + 0.5*q_val[427]*q_val[430] + 0.5*q_val[428]*q_val[430] + 1 + -0.5*q_val[431] + 0.5*q_val[429]*q_val[431] + 0.5*q_val[430]*q_val[431] + 1 + -0.5*q_val[434] + 0.5*q_val[432]*q_val[434] + 0.5*q_val[433]*q_val[434] + 1 + -0.5*q_val[435] + 0.5*q_val[432]*q_val[435] + 0.5*q_val[434]*q_val[435] + 1 + -0.5*q_val[436] + 0.5*q_val[433]*q_val[436] + 0.5*q_val[434]*q_val[436] + 1 + -0.5*q_val[437] + 0.5*q_val[435]*q_val[437] + 0.5*q_val[436]*q_val[437] + 1 + -0.5*q_val[440] + 0.5*q_val[438]*q_val[440] + 0.5*q_val[439]*q_val[440] + 1 + -0.5*q_val[441] + 0.5*q_val[438]*q_val[441] + 0.5*q_val[440]*q_val[441] + 1 + -0.5*q_val[442] + 0.5*q_val[439]*q_val[442] + 0.5*q_val[440]*q_val[442] + 1 + -0.5*q_val[443] + 0.5*q_val[441]*q_val[443] + 0.5*q_val[442]*q_val[443] + 1 + -0.5*q_val[446] + 0.5*q_val[444]*q_val[446] + 0.5*q_val[445]*q_val[446] + 1 + -0.5*q_val[447] + 0.5*q_val[444]*q_val[447] + 0.5*q_val[446]*q_val[447] + 1 + -0.5*q_val[448] + 0.5*q_val[445]*q_val[448] + 0.5*q_val[446]*q_val[448] + 1 + -0.5*q_val[449] + 0.5*q_val[447]*q_val[449] + 0.5*q_val[448]*q_val[449] + 1 + -0.5*q_val[452] + 0.5*q_val[450]*q_val[452] + 0.5*q_val[451]*q_val[452] + 1 + -0.5*q_val[453] + 0.5*q_val[450]*q_val[453] + 0.5*q_val[452]*q_val[453] + 1 + -0.5*q_val[454] + 0.5*q_val[451]*q_val[454] + 0.5*q_val[452]*q_val[454] + 1 + -0.5*q_val[455] + 0.5*q_val[453]*q_val[455] + 0.5*q_val[454]*q_val[455] + 1 + -0.5*q_val[458] + 0.5*q_val[456]*q_val[458] + 0.5*q_val[457]*q_val[458] + 1 + -0.5*q_val[459] + 0.5*q_val[456]*q_val[459] + 0.5*q_val[458]*q_val[459] + 1 + -0.5*q_val[460] + 0.5*q_val[457]*q_val[460] + 0.5*q_val[458]*q_val[460] + 1 + -0.5*q_val[461] + 0.5*q_val[459]*q_val[461] + 0.5*q_val[460]*q_val[461] + 1 + -0.5*q_val[464] + 0.5*q_val[462]*q_val[464] + 0.5*q_val[463]*q_val[464] + 1 + -0.5*q_val[465] + 0.5*q_val[462]*q_val[465] + 0.5*q_val[464]*q_val[465] + 1 + -0.5*q_val[466] + 0.5*q_val[463]*q_val[466] + 0.5*q_val[464]*q_val[466] + 1 + -0.5*q_val[467] + 0.5*q_val[465]*q_val[467] + 0.5*q_val[466]*q_val[467] + 1 + -0.5*q_val[470] + 0.5*q_val[468]*q_val[470] + 0.5*q_val[469]*q_val[470] + 1 + -0.5*q_val[471] + 0.5*q_val[468]*q_val[471] + 0.5*q_val[470]*q_val[471] + 1 + -0.5*q_val[472] + 0.5*q_val[469]*q_val[472] + 0.5*q_val[470]*q_val[472] + 1 + -0.5*q_val[473] + 0.5*q_val[471]*q_val[473] + 0.5*q_val[472]*q_val[473] + 1 + -0.5*q_val[476] + 0.5*q_val[474]*q_val[476] + 0.5*q_val[475]*q_val[476] + 1 + -0.5*q_val[477] + 0.5*q_val[474]*q_val[477] + 0.5*q_val[476]*q_val[477] + 1 + -0.5*q_val[478] + 0.5*q_val[475]*q_val[478] + 0.5*q_val[476]*q_val[478] + 1 + -0.5*q_val[479] + 0.5*q_val[477]*q_val[479] + 0.5*q_val[478]*q_val[479] + 1 + -0.5*q_val[482] + 0.5*q_val[480]*q_val[482] + 0.5*q_val[481]*q_val[482] + 1 + -0.5*q_val[483] + 0.5*q_val[480]*q_val[483] + 0.5*q_val[482]*q_val[483] + 1 + -0.5*q_val[484] + 0.5*q_val[481]*q_val[484] + 0.5*q_val[482]*q_val[484] + 1 + -0.5*q_val[485] + 0.5*q_val[483]*q_val[485] + 0.5*q_val[484]*q_val[485] + 1 + -0.5*q_val[488] + 0.5*q_val[486]*q_val[488] + 0.5*q_val[487]*q_val[488] + 1 + -0.5*q_val[489] + 0.5*q_val[486]*q_val[489] + 0.5*q_val[488]*q_val[489] + 1 + -0.5*q_val[490] + 0.5*q_val[487]*q_val[490] + 0.5*q_val[488]*q_val[490] + 1 + -0.5*q_val[491] + 0.5*q_val[489]*q_val[491] + 0.5*q_val[490]*q_val[491] + 1 + -0.5*q_val[494] + 0.5*q_val[492]*q_val[494] + 0.5*q_val[493]*q_val[494] + 1 + -0.5*q_val[495] + 0.5*q_val[492]*q_val[495] + 0.5*q_val[494]*q_val[495] + 1 + -0.5*q_val[496] + 0.5*q_val[493]*q_val[496] + 0.5*q_val[494]*q_val[496] + 1 + -0.5*q_val[497] + 0.5*q_val[495]*q_val[497] + 0.5*q_val[496]*q_val[497] + 1 + -0.5*q_val[500] + 0.5*q_val[498]*q_val[500] + 0.5*q_val[499]*q_val[500] + 1 + -0.5*q_val[501] + 0.5*q_val[498]*q_val[501] + 0.5*q_val[500]*q_val[501] + 1 + -0.5*q_val[502] + 0.5*q_val[499]*q_val[502] + 0.5*q_val[500]*q_val[502] + 1 + -0.5*q_val[503] + 0.5*q_val[501]*q_val[503] + 0.5*q_val[502]*q_val[503] + 1 + -0.5*q_val[506] + 0.5*q_val[504]*q_val[506] + 0.5*q_val[505]*q_val[506] + 1 + -0.5*q_val[507] + 0.5*q_val[504]*q_val[507] + 0.5*q_val[506]*q_val[507] + 1 + -0.5*q_val[508] + 0.5*q_val[505]*q_val[508] + 0.5*q_val[506]*q_val[508] + 1 + -0.5*q_val[509] + 0.5*q_val[507]*q_val[509] + 0.5*q_val[508]*q_val[509] + 1 + -0.5*q_val[512] + 0.5*q_val[510]*q_val[512] + 0.5*q_val[511]*q_val[512] + 1 + -0.5*q_val[513] + 0.5*q_val[510]*q_val[513] + 0.5*q_val[512]*q_val[513] + 1 + -0.5*q_val[514] + 0.5*q_val[511]*q_val[514] + 0.5*q_val[512]*q_val[514] + 1 + -0.5*q_val[515] + 0.5*q_val[513]*q_val[515] + 0.5*q_val[514]*q_val[515] + 1 + -0.5*q_val[518] + 0.5*q_val[516]*q_val[518] + 0.5*q_val[517]*q_val[518] + 1 + -0.5*q_val[519] + 0.5*q_val[516]*q_val[519] + 0.5*q_val[518]*q_val[519] + 1 + -0.5*q_val[520] + 0.5*q_val[517]*q_val[520] + 0.5*q_val[518]*q_val[520] + 1 + -0.5*q_val[521] + 0.5*q_val[519]*q_val[521] + 0.5*q_val[520]*q_val[521] + 1 + -0.5*q_val[524] + 0.5*q_val[522]*q_val[524] + 0.5*q_val[523]*q_val[524] + 1 + -0.5*q_val[525] + 0.5*q_val[522]*q_val[525] + 0.5*q_val[524]*q_val[525] + 1 + -0.5*q_val[526] + 0.5*q_val[523]*q_val[526] + 0.5*q_val[524]*q_val[526] + 1 + -0.5*q_val[527] + 0.5*q_val[525]*q_val[527] + 0.5*q_val[526]*q_val[527] + 1 + -0.5*q_val[530] + 0.5*q_val[528]*q_val[530] + 0.5*q_val[529]*q_val[530] + 1 + -0.5*q_val[531] + 0.5*q_val[528]*q_val[531] + 0.5*q_val[530]*q_val[531] + 1 + -0.5*q_val[532] + 0.5*q_val[529]*q_val[532] + 0.5*q_val[530]*q_val[532] + 1 + -0.5*q_val[533] + 0.5*q_val[531]*q_val[533] + 0.5*q_val[532]*q_val[533] + 1 + -0.5*q_val[536] + 0.5*q_val[534]*q_val[536] + 0.5*q_val[535]*q_val[536] + 1 + -0.5*q_val[537] + 0.5*q_val[534]*q_val[537] + 0.5*q_val[536]*q_val[537] + 1 + -0.5*q_val[538] + 0.5*q_val[535]*q_val[538] + 0.5*q_val[536]*q_val[538] + 1 + -0.5*q_val[539] + 0.5*q_val[537]*q_val[539] + 0.5*q_val[538]*q_val[539] + 1 + -0.5*q_val[542] + 0.5*q_val[540]*q_val[542] + 0.5*q_val[541]*q_val[542] + 1 + -0.5*q_val[543] + 0.5*q_val[540]*q_val[543] + 0.5*q_val[542]*q_val[543] + 1 + -0.5*q_val[544] + 0.5*q_val[541]*q_val[544] + 0.5*q_val[542]*q_val[544] + 1 + -0.5*q_val[545] + 0.5*q_val[543]*q_val[545] + 0.5*q_val[544]*q_val[545] + 1 + -0.5*q_val[548] + 0.5*q_val[546]*q_val[548] + 0.5*q_val[547]*q_val[548] + 1 + -0.5*q_val[549] + 0.5*q_val[546]*q_val[549] + 0.5*q_val[548]*q_val[549] + 1 + -0.5*q_val[550] + 0.5*q_val[547]*q_val[550] + 0.5*q_val[548]*q_val[550] + 1 + -0.5*q_val[551] + 0.5*q_val[549]*q_val[551] + 0.5*q_val[550]*q_val[551] + 1 + -0.5*q_val[554] + 0.5*q_val[552]*q_val[554] + 0.5*q_val[553]*q_val[554] + 1 + -0.5*q_val[555] + 0.5*q_val[552]*q_val[555] + 0.5*q_val[554]*q_val[555] + 1 + -0.5*q_val[556] + 0.5*q_val[553]*q_val[556] + 0.5*q_val[554]*q_val[556] + 1 + -0.5*q_val[557] + 0.5*q_val[555]*q_val[557] + 0.5*q_val[556]*q_val[557] + 1 + -0.5*q_val[560] + 0.5*q_val[558]*q_val[560] + 0.5*q_val[559]*q_val[560] + 1 + -0.5*q_val[561] + 0.5*q_val[558]*q_val[561] + 0.5*q_val[560]*q_val[561] + 1 + -0.5*q_val[562] + 0.5*q_val[559]*q_val[562] + 0.5*q_val[560]*q_val[562] + 1 + -0.5*q_val[563] + 0.5*q_val[561]*q_val[563] + 0.5*q_val[562]*q_val[563] + 1 + -0.5*q_val[566] + 0.5*q_val[564]*q_val[566] + 0.5*q_val[565]*q_val[566] + 1 + -0.5*q_val[567] + 0.5*q_val[564]*q_val[567] + 0.5*q_val[566]*q_val[567] + 1 + -0.5*q_val[568] + 0.5*q_val[565]*q_val[568] + 0.5*q_val[566]*q_val[568] + 1 + -0.5*q_val[569] + 0.5*q_val[567]*q_val[569] + 0.5*q_val[568]*q_val[569] + 1 + -0.5*q_val[572] + 0.5*q_val[570]*q_val[572] + 0.5*q_val[571]*q_val[572] + 1 + -0.5*q_val[573] + 0.5*q_val[570]*q_val[573] + 0.5*q_val[572]*q_val[573] + 1 + -0.5*q_val[574] + 0.5*q_val[571]*q_val[574] + 0.5*q_val[572]*q_val[574] + 1 + -0.5*q_val[575] + 0.5*q_val[573]*q_val[575] + 0.5*q_val[574]*q_val[575] + 1 + -0.5*q_val[578] + 0.5*q_val[576]*q_val[578] + 0.5*q_val[577]*q_val[578] + 1 + -0.5*q_val[579] + 0.5*q_val[576]*q_val[579] + 0.5*q_val[578]*q_val[579] + 1 + -0.5*q_val[580] + 0.5*q_val[577]*q_val[580] + 0.5*q_val[578]*q_val[580] + 1 + -0.5*q_val[581] + 0.5*q_val[579]*q_val[581] + 0.5*q_val[580]*q_val[581] + 1 + -0.5*q_val[584] + 0.5*q_val[582]*q_val[584] + 0.5*q_val[583]*q_val[584] + 1 + -0.5*q_val[585] + 0.5*q_val[582]*q_val[585] + 0.5*q_val[584]*q_val[585] + 1 + -0.5*q_val[586] + 0.5*q_val[583]*q_val[586] + 0.5*q_val[584]*q_val[586] + 1 + -0.5*q_val[587] + 0.5*q_val[585]*q_val[587] + 0.5*q_val[586]*q_val[587] + 1 + -0.5*q_val[590] + 0.5*q_val[588]*q_val[590] + 0.5*q_val[589]*q_val[590] + 1 + -0.5*q_val[591] + 0.5*q_val[588]*q_val[591] + 0.5*q_val[590]*q_val[591] + 1 + -0.5*q_val[592] + 0.5*q_val[589]*q_val[592] + 0.5*q_val[590]*q_val[592] + 1 + -0.5*q_val[593] + 0.5*q_val[591]*q_val[593] + 0.5*q_val[592]*q_val[593] + 1 + -0.5*q_val[596] + 0.5*q_val[594]*q_val[596] + 0.5*q_val[595]*q_val[596] + 1 + -0.5*q_val[597] + 0.5*q_val[594]*q_val[597] + 0.5*q_val[596]*q_val[597] + 1 + -0.5*q_val[598] + 0.5*q_val[595]*q_val[598] + 0.5*q_val[596]*q_val[598] + 1 + -0.5*q_val[599] + 0.5*q_val[597]*q_val[599] + 0.5*q_val[598]*q_val[599] + 0.5*q_val[0]*q_val[1]*q_val[2] + 0.5*q_val[0]*q_val[2]*q_val[3] + 0.5*q_val[1]*q_val[2]*q_val[4] + 0.5*q_val[3]*q_val[4]*q_val[5] + 0.5*q_val[6]*q_val[7]*q_val[8] + 0.5*q_val[6]*q_val[8]*q_val[9] + 0.5*q_val[7]*q_val[8]*q_val[10] + 0.5*q_val[9]*q_val[10]*q_val[11] + 0.5*q_val[12]*q_val[13]*q_val[14] + 0.5*q_val[12]*q_val[14]*q_val[15] + 0.5*q_val[13]*q_val[14]*q_val[16] + 0.5*q_val[15]*q_val[16]*q_val[17] + 0.5*q_val[18]*q_val[19]*q_val[20] + 0.5*q_val[18]*q_val[20]*q_val[21] + 0.5*q_val[19]*q_val[20]*q_val[22] + 0.5*q_val[21]*q_val[22]*q_val[23] + 0.5*q_val[24]*q_val[25]*q_val[26] + 0.5*q_val[24]*q_val[26]*q_val[27] + 0.5*q_val[25]*q_val[26]*q_val[28] + 0.5*q_val[27]*q_val[28]*q_val[29] + 0.5*q_val[30]*q_val[31]*q_val[32] + 0.5*q_val[30]*q_val[32]*q_val[33] + 0.5*q_val[31]*q_val[32]*q_val[34] + 0.5*q_val[33]*q_val[34]*q_val[35] + 0.5*q_val[36]*q_val[37]*q_val[38] + 0.5*q_val[36]*q_val[38]*q_val[39] + 0.5*q_val[37]*q_val[38]*q_val[40] + 0.5*q_val[39]*q_val[40]*q_val[41] + 0.5*q_val[42]*q_val[43]*q_val[44] + 0.5*q_val[42]*q_val[44]*q_val[45] + 0.5*q_val[43]*q_val[44]*q_val[46] + 0.5*q_val[45]*q_val[46]*q_val[47] + 0.5*q_val[48]*q_val[49]*q_val[50] + 0.5*q_val[48]*q_val[50]*q_val[51] + 0.5*q_val[49]*q_val[50]*q_val[52] + 0.5*q_val[51]*q_val[52]*q_val[53] + 0.5*q_val[54]*q_val[55]*q_val[56] + 0.5*q_val[54]*q_val[56]*q_val[57] + 0.5*q_val[55]*q_val[56]*q_val[58] + 0.5*q_val[57]*q_val[58]*q_val[59] + 0.5*q_val[60]*q_val[61]*q_val[62] + 0.5*q_val[60]*q_val[62]*q_val[63] + 0.5*q_val[61]*q_val[62]*q_val[64] + 0.5*q_val[63]*q_val[64]*q_val[65] + 0.5*q_val[66]*q_val[67]*q_val[68] + 0.5*q_val[66]*q_val[68]*q_val[69] + 0.5*q_val[67]*q_val[68]*q_val[70] + 0.5*q_val[69]*q_val[70]*q_val[71] + 0.5*q_val[72]*q_val[73]*q_val[74] + 0.5*q_val[72]*q_val[74]*q_val[75] + 0.5*q_val[73]*q_val[74]*q_val[76] + 0.5*q_val[75]*q_val[76]*q_val[77] + 0.5*q_val[78]*q_val[79]*q_val[80] + 0.5*q_val[78]*q_val[80]*q_val[81] + 0.5*q_val[79]*q_val[80]*q_val[82] + 0.5*q_val[81]*q_val[82]*q_val[83] + 0.5*q_val[84]*q_val[85]*q_val[86] + 0.5*q_val[84]*q_val[86]*q_val[87] + 0.5*q_val[85]*q_val[86]*q_val[88] + 0.5*q_val[87]*q_val[88]*q_val[89] + 0.5*q_val[90]*q_val[91]*q_val[92] + 0.5*q_val[90]*q_val[92]*q_val[93] + 0.5*q_val[91]*q_val[92]*q_val[94] + 0.5*q_val[93]*q_val[94]*q_val[95] + 0.5*q_val[96]*q_val[97]*q_val[98] + 0.5*q_val[96]*q_val[98]*q_val[99] + 0.5*q_val[97]*q_val[98]*q_val[100] + 0.5*q_val[99]*q_val[100]*q_val[101] + 0.5*q_val[102]*q_val[103]*q_val[104] + 0.5*q_val[102]*q_val[104]*q_val[105] + 0.5*q_val[103]*q_val[104]*q_val[106] + 0.5*q_val[105]*q_val[106]*q_val[107] + 0.5*q_val[108]*q_val[109]*q_val[110] + 0.5*q_val[108]*q_val[110]*q_val[111] + 0.5*q_val[109]*q_val[110]*q_val[112] + 0.5*q_val[111]*q_val[112]*q_val[113] + 0.5*q_val[114]*q_val[115]*q_val[116] + 0.5*q_val[114]*q_val[116]*q_val[117] + 0.5*q_val[115]*q_val[116]*q_val[118] + 0.5*q_val[117]*q_val[118]*q_val[119] + 0.5*q_val[120]*q_val[121]*q_val[122] + 0.5*q_val[120]*q_val[122]*q_val[123] + 0.5*q_val[121]*q_val[122]*q_val[124] + 0.5*q_val[123]*q_val[124]*q_val[125] + 0.5*q_val[126]*q_val[127]*q_val[128] + 0.5*q_val[126]*q_val[128]*q_val[129] + 0.5*q_val[127]*q_val[128]*q_val[130] + 0.5*q_val[129]*q_val[130]*q_val[131] + 0.5*q_val[132]*q_val[133]*q_val[134] + 0.5*q_val[132]*q_val[134]*q_val[135] + 0.5*q_val[133]*q_val[134]*q_val[136] + 0.5*q_val[135]*q_val[136]*q_val[137] + 0.5*q_val[138]*q_val[139]*q_val[140] + 0.5*q_val[138]*q_val[140]*q_val[141] + 0.5*q_val[139]*q_val[140]*q_val[142] + 0.5*q_val[141]*q_val[142]*q_val[143] + 0.5*q_val[144]*q_val[145]*q_val[146] + 0.5*q_val[144]*q_val[146]*q_val[147] + 0.5*q_val[145]*q_val[146]*q_val[148] + 0.5*q_val[147]*q_val[148]*q_val[149] + 0.5*q_val[150]*q_val[151]*q_val[152] + 0.5*q_val[150]*q_val[152]*q_val[153] + 0.5*q_val[151]*q_val[152]*q_val[154] + 0.5*q_val[153]*q_val[154]*q_val[155] + 0.5*q_val[156]*q_val[157]*q_val[158] + 0.5*q_val[156]*q_val[158]*q_val[159] + 0.5*q_val[157]*q_val[158]*q_val[160] + 0.5*q_val[159]*q_val[160]*q_val[161] + 0.5*q_val[162]*q_val[163]*q_val[164] + 0.5*q_val[162]*q_val[164]*q_val[165] + 0.5*q_val[163]*q_val[164]*q_val[166] + 0.5*q_val[165]*q_val[166]*q_val[167] + 0.5*q_val[168]*q_val[169]*q_val[170] + 0.5*q_val[168]*q_val[170]*q_val[171] + 0.5*q_val[169]*q_val[170]*q_val[172] + 0.5*q_val[171]*q_val[172]*q_val[173] + 0.5*q_val[174]*q_val[175]*q_val[176] + 0.5*q_val[174]*q_val[176]*q_val[177] + 0.5*q_val[175]*q_val[176]*q_val[178] + 0.5*q_val[177]*q_val[178]*q_val[179] + 0.5*q_val[180]*q_val[181]*q_val[182] + 0.5*q_val[180]*q_val[182]*q_val[183] + 0.5*q_val[181]*q_val[182]*q_val[184] + 0.5*q_val[183]*q_val[184]*q_val[185] + 0.5*q_val[186]*q_val[187]*q_val[188] + 0.5*q_val[186]*q_val[188]*q_val[189] + 0.5*q_val[187]*q_val[188]*q_val[190] + 0.5*q_val[189]*q_val[190]*q_val[191] + 0.5*q_val[192]*q_val[193]*q_val[194] + 0.5*q_val[192]*q_val[194]*q_val[195] + 0.5*q_val[193]*q_val[194]*q_val[196] + 0.5*q_val[195]*q_val[196]*q_val[197] + 0.5*q_val[198]*q_val[199]*q_val[200] + 0.5*q_val[198]*q_val[200]*q_val[201] + 0.5*q_val[199]*q_val[200]*q_val[202] + 0.5*q_val[201]*q_val[202]*q_val[203] + 0.5*q_val[204]*q_val[205]*q_val[206] + 0.5*q_val[204]*q_val[206]*q_val[207] + 0.5*q_val[205]*q_val[206]*q_val[208] + 0.5*q_val[207]*q_val[208]*q_val[209] + 0.5*q_val[210]*q_val[211]*q_val[212] + 0.5*q_val[210]*q_val[212]*q_val[213] + 0.5*q_val[211]*q_val[212]*q_val[214] + 0.5*q_val[213]*q_val[214]*q_val[215] + 0.5*q_val[216]*q_val[217]*q_val[218] + 0.5*q_val[216]*q_val[218]*q_val[219] + 0.5*q_val[217]*q_val[218]*q_val[220] + 0.5*q_val[219]*q_val[220]*q_val[221] + 0.5*q_val[222]*q_val[223]*q_val[224] + 0.5*q_val[222]*q_val[224]*q_val[225] + 0.5*q_val[223]*q_val[224]*q_val[226] + 0.5*q_val[225]*q_val[226]*q_val[227] + 0.5*q_val[228]*q_val[229]*q_val[230] + 0.5*q_val[228]*q_val[230]*q_val[231] + 0.5*q_val[229]*q_val[230]*q_val[232] + 0.5*q_val[231]*q_val[232]*q_val[233] + 0.5*q_val[234]*q_val[235]*q_val[236] + 0.5*q_val[234]*q_val[236]*q_val[237] + 0.5*q_val[235]*q_val[236]*q_val[238] + 0.5*q_val[237]*q_val[238]*q_val[239] + 0.5*q_val[240]*q_val[241]*q_val[242] + 0.5*q_val[240]*q_val[242]*q_val[243] + 0.5*q_val[241]*q_val[242]*q_val[244] + 0.5*q_val[243]*q_val[244]*q_val[245] + 0.5*q_val[246]*q_val[247]*q_val[248] + 0.5*q_val[246]*q_val[248]*q_val[249] + 0.5*q_val[247]*q_val[248]*q_val[250] + 0.5*q_val[249]*q_val[250]*q_val[251] + 0.5*q_val[252]*q_val[253]*q_val[254] + 0.5*q_val[252]*q_val[254]*q_val[255] + 0.5*q_val[253]*q_val[254]*q_val[256] + 0.5*q_val[255]*q_val[256]*q_val[257] + 0.5*q_val[258]*q_val[259]*q_val[260] + 0.5*q_val[258]*q_val[260]*q_val[261] + 0.5*q_val[259]*q_val[260]*q_val[262] + 0.5*q_val[261]*q_val[262]*q_val[263] + 0.5*q_val[264]*q_val[265]*q_val[266] + 0.5*q_val[264]*q_val[266]*q_val[267] + 0.5*q_val[265]*q_val[266]*q_val[268] + 0.5*q_val[267]*q_val[268]*q_val[269] + 0.5*q_val[270]*q_val[271]*q_val[272] + 0.5*q_val[270]*q_val[272]*q_val[273] + 0.5*q_val[271]*q_val[272]*q_val[274] + 0.5*q_val[273]*q_val[274]*q_val[275] + 0.5*q_val[276]*q_val[277]*q_val[278] + 0.5*q_val[276]*q_val[278]*q_val[279] + 0.5*q_val[277]*q_val[278]*q_val[280] + 0.5*q_val[279]*q_val[280]*q_val[281] + 0.5*q_val[282]*q_val[283]*q_val[284] + 0.5*q_val[282]*q_val[284]*q_val[285] + 0.5*q_val[283]*q_val[284]*q_val[286] + 0.5*q_val[285]*q_val[286]*q_val[287] + 0.5*q_val[288]*q_val[289]*q_val[290] + 0.5*q_val[288]*q_val[290]*q_val[291] + 0.5*q_val[289]*q_val[290]*q_val[292] + 0.5*q_val[291]*q_val[292]*q_val[293] + 0.5*q_val[294]*q_val[295]*q_val[296] + 0.5*q_val[294]*q_val[296]*q_val[297] + 0.5*q_val[295]*q_val[296]*q_val[298] + 0.5*q_val[297]*q_val[298]*q_val[299] + 0.5*q_val[300]*q_val[301]*q_val[302] + 0.5*q_val[300]*q_val[302]*q_val[303] + 0.5*q_val[301]*q_val[302]*q_val[304] + 0.5*q_val[303]*q_val[304]*q_val[305] + 0.5*q_val[306]*q_val[307]*q_val[308] + 0.5*q_val[306]*q_val[308]*q_val[309] + 0.5*q_val[307]*q_val[308]*q_val[310] + 0.5*q_val[309]*q_val[310]*q_val[311] + 0.5*q_val[312]*q_val[313]*q_val[314] + 0.5*q_val[312]*q_val[314]*q_val[315] + 0.5*q_val[313]*q_val[314]*q_val[316] + 0.5*q_val[315]*q_val[316]*q_val[317] + 0.5*q_val[318]*q_val[319]*q_val[320] + 0.5*q_val[318]*q_val[320]*q_val[321] + 0.5*q_val[319]*q_val[320]*q_val[322] + 0.5*q_val[321]*q_val[322]*q_val[323] + 0.5*q_val[324]*q_val[325]*q_val[326] + 0.5*q_val[324]*q_val[326]*q_val[327] + 0.5*q_val[325]*q_val[326]*q_val[328] + 0.5*q_val[327]*q_val[328]*q_val[329] + 0.5*q_val[330]*q_val[331]*q_val[332] + 0.5*q_val[330]*q_val[332]*q_val[333] + 0.5*q_val[331]*q_val[332]*q_val[334] + 0.5*q_val[333]*q_val[334]*q_val[335] + 0.5*q_val[336]*q_val[337]*q_val[338] + 0.5*q_val[336]*q_val[338]*q_val[339] + 0.5*q_val[337]*q_val[338]*q_val[340] + 0.5*q_val[339]*q_val[340]*q_val[341] + 0.5*q_val[342]*q_val[343]*q_val[344] + 0.5*q_val[342]*q_val[344]*q_val[345] + 0.5*q_val[343]*q_val[344]*q_val[346] + 0.5*q_val[345]*q_val[346]*q_val[347] + 0.5*q_val[348]*q_val[349]*q_val[350] + 0.5*q_val[348]*q_val[350]*q_val[351] + 0.5*q_val[349]*q_val[350]*q_val[352] + 0.5*q_val[351]*q_val[352]*q_val[353] + 0.5*q_val[354]*q_val[355]*q_val[356] + 0.5*q_val[354]*q_val[356]*q_val[357] + 0.5*q_val[355]*q_val[356]*q_val[358] + 0.5*q_val[357]*q_val[358]*q_val[359] + 0.5*q_val[360]*q_val[361]*q_val[362] + 0.5*q_val[360]*q_val[362]*q_val[363] + 0.5*q_val[361]*q_val[362]*q_val[364] + 0.5*q_val[363]*q_val[364]*q_val[365] + 0.5*q_val[366]*q_val[367]*q_val[368] + 0.5*q_val[366]*q_val[368]*q_val[369] + 0.5*q_val[367]*q_val[368]*q_val[370] + 0.5*q_val[369]*q_val[370]*q_val[371] + 0.5*q_val[372]*q_val[373]*q_val[374] + 0.5*q_val[372]*q_val[374]*q_val[375] + 0.5*q_val[373]*q_val[374]*q_val[376] + 0.5*q_val[375]*q_val[376]*q_val[377] + 0.5*q_val[378]*q_val[379]*q_val[380] + 0.5*q_val[378]*q_val[380]*q_val[381] + 0.5*q_val[379]*q_val[380]*q_val[382] + 0.5*q_val[381]*q_val[382]*q_val[383] + 0.5*q_val[384]*q_val[385]*q_val[386] + 0.5*q_val[384]*q_val[386]*q_val[387] + 0.5*q_val[385]*q_val[386]*q_val[388] + 0.5*q_val[387]*q_val[388]*q_val[389] + 0.5*q_val[390]*q_val[391]*q_val[392] + 0.5*q_val[390]*q_val[392]*q_val[393] + 0.5*q_val[391]*q_val[392]*q_val[394] + 0.5*q_val[393]*q_val[394]*q_val[395] + 0.5*q_val[396]*q_val[397]*q_val[398] + 0.5*q_val[396]*q_val[398]*q_val[399] + 0.5*q_val[397]*q_val[398]*q_val[400] + 0.5*q_val[399]*q_val[400]*q_val[401] + 0.5*q_val[402]*q_val[403]*q_val[404] + 0.5*q_val[402]*q_val[404]*q_val[405] + 0.5*q_val[403]*q_val[404]*q_val[406] + 0.5*q_val[405]*q_val[406]*q_val[407] + 0.5*q_val[408]*q_val[409]*q_val[410] + 0.5*q_val[408]*q_val[410]*q_val[411] + 0.5*q_val[409]*q_val[410]*q_val[412] + 0.5*q_val[411]*q_val[412]*q_val[413] + 0.5*q_val[414]*q_val[415]*q_val[416] + 0.5*q_val[414]*q_val[416]*q_val[417] + 0.5*q_val[415]*q_val[416]*q_val[418] + 0.5*q_val[417]*q_val[418]*q_val[419] + 0.5*q_val[420]*q_val[421]*q_val[422] + 0.5*q_val[420]*q_val[422]*q_val[423] + 0.5*q_val[421]*q_val[422]*q_val[424] + 0.5*q_val[423]*q_val[424]*q_val[425] + 0.5*q_val[426]*q_val[427]*q_val[428] + 0.5*q_val[426]*q_val[428]*q_val[429] + 0.5*q_val[427]*q_val[428]*q_val[430] + 0.5*q_val[429]*q_val[430]*q_val[431] + 0.5*q_val[432]*q_val[433]*q_val[434] + 0.5*q_val[432]*q_val[434]*q_val[435] + 0.5*q_val[433]*q_val[434]*q_val[436] + 0.5*q_val[435]*q_val[436]*q_val[437] + 0.5*q_val[438]*q_val[439]*q_val[440] + 0.5*q_val[438]*q_val[440]*q_val[441] + 0.5*q_val[439]*q_val[440]*q_val[442] + 0.5*q_val[441]*q_val[442]*q_val[443] + 0.5*q_val[444]*q_val[445]*q_val[446] + 0.5*q_val[444]*q_val[446]*q_val[447] + 0.5*q_val[445]*q_val[446]*q_val[448] + 0.5*q_val[447]*q_val[448]*q_val[449] + 0.5*q_val[450]*q_val[451]*q_val[452] + 0.5*q_val[450]*q_val[452]*q_val[453] + 0.5*q_val[451]*q_val[452]*q_val[454] + 0.5*q_val[453]*q_val[454]*q_val[455] + 0.5*q_val[456]*q_val[457]*q_val[458] + 0.5*q_val[456]*q_val[458]*q_val[459] + 0.5*q_val[457]*q_val[458]*q_val[460] + 0.5*q_val[459]*q_val[460]*q_val[461] + 0.5*q_val[462]*q_val[463]*q_val[464] + 0.5*q_val[462]*q_val[464]*q_val[465] + 0.5*q_val[463]*q_val[464]*q_val[466] + 0.5*q_val[465]*q_val[466]*q_val[467] + 0.5*q_val[468]*q_val[469]*q_val[470] + 0.5*q_val[468]*q_val[470]*q_val[471] + 0.5*q_val[469]*q_val[470]*q_val[472] + 0.5*q_val[471]*q_val[472]*q_val[473] + 0.5*q_val[474]*q_val[475]*q_val[476] + 0.5*q_val[474]*q_val[476]*q_val[477] + 0.5*q_val[475]*q_val[476]*q_val[478] + 0.5*q_val[477]*q_val[478]*q_val[479] + 0.5*q_val[480]*q_val[481]*q_val[482] + 0.5*q_val[480]*q_val[482]*q_val[483] + 0.5*q_val[481]*q_val[482]*q_val[484] + 0.5*q_val[483]*q_val[484]*q_val[485] + 0.5*q_val[486]*q_val[487]*q_val[488] + 0.5*q_val[486]*q_val[488]*q_val[489] + 0.5*q_val[487]*q_val[488]*q_val[490] + 0.5*q_val[489]*q_val[490]*q_val[491] + 0.5*q_val[492]*q_val[493]*q_val[494] + 0.5*q_val[492]*q_val[494]*q_val[495] + 0.5*q_val[493]*q_val[494]*q_val[496] + 0.5*q_val[495]*q_val[496]*q_val[497] + 0.5*q_val[498]*q_val[499]*q_val[500] + 0.5*q_val[498]*q_val[500]*q_val[501] + 0.5*q_val[499]*q_val[500]*q_val[502] + 0.5*q_val[501]*q_val[502]*q_val[503] + 0.5*q_val[504]*q_val[505]*q_val[506] + 0.5*q_val[504]*q_val[506]*q_val[507] + 0.5*q_val[505]*q_val[506]*q_val[508] + 0.5*q_val[507]*q_val[508]*q_val[509] + 0.5*q_val[510]*q_val[511]*q_val[512] + 0.5*q_val[510]*q_val[512]*q_val[513] + 0.5*q_val[511]*q_val[512]*q_val[514] + 0.5*q_val[513]*q_val[514]*q_val[515] + 0.5*q_val[516]*q_val[517]*q_val[518] + 0.5*q_val[516]*q_val[518]*q_val[519] + 0.5*q_val[517]*q_val[518]*q_val[520] + 0.5*q_val[519]*q_val[520]*q_val[521] + 0.5*q_val[522]*q_val[523]*q_val[524] + 0.5*q_val[522]*q_val[524]*q_val[525] + 0.5*q_val[523]*q_val[524]*q_val[526] + 0.5*q_val[525]*q_val[526]*q_val[527] + 0.5*q_val[528]*q_val[529]*q_val[530] + 0.5*q_val[528]*q_val[530]*q_val[531] + 0.5*q_val[529]*q_val[530]*q_val[532] + 0.5*q_val[531]*q_val[532]*q_val[533] + 0.5*q_val[534]*q_val[535]*q_val[536] + 0.5*q_val[534]*q_val[536]*q_val[537] + 0.5*q_val[535]*q_val[536]*q_val[538] + 0.5*q_val[537]*q_val[538]*q_val[539] + 0.5*q_val[540]*q_val[541]*q_val[542] + 0.5*q_val[540]*q_val[542]*q_val[543] + 0.5*q_val[541]*q_val[542]*q_val[544] + 0.5*q_val[543]*q_val[544]*q_val[545] + 0.5*q_val[546]*q_val[547]*q_val[548] + 0.5*q_val[546]*q_val[548]*q_val[549] + 0.5*q_val[547]*q_val[548]*q_val[550] + 0.5*q_val[549]*q_val[550]*q_val[551] + 0.5*q_val[552]*q_val[553]*q_val[554] + 0.5*q_val[552]*q_val[554]*q_val[555] + 0.5*q_val[553]*q_val[554]*q_val[556] + 0.5*q_val[555]*q_val[556]*q_val[557] + 0.5*q_val[558]*q_val[559]*q_val[560] + 0.5*q_val[558]*q_val[560]*q_val[561] + 0.5*q_val[559]*q_val[560]*q_val[562] + 0.5*q_val[561]*q_val[562]*q_val[563] + 0.5*q_val[564]*q_val[565]*q_val[566] + 0.5*q_val[564]*q_val[566]*q_val[567] + 0.5*q_val[565]*q_val[566]*q_val[568] + 0.5*q_val[567]*q_val[568]*q_val[569] + 0.5*q_val[570]*q_val[571]*q_val[572] + 0.5*q_val[570]*q_val[572]*q_val[573] + 0.5*q_val[571]*q_val[572]*q_val[574] + 0.5*q_val[573]*q_val[574]*q_val[575] + 0.5*q_val[576]*q_val[577]*q_val[578] + 0.5*q_val[576]*q_val[578]*q_val[579] + 0.5*q_val[577]*q_val[578]*q_val[580] + 0.5*q_val[579]*q_val[580]*q_val[581] + 0.5*q_val[582]*q_val[583]*q_val[584] + 0.5*q_val[582]*q_val[584]*q_val[585] + 0.5*q_val[583]*q_val[584]*q_val[586] + 0.5*q_val[585]*q_val[586]*q_val[587] + 0.5*q_val[588]*q_val[589]*q_val[590] + 0.5*q_val[588]*q_val[590]*q_val[591] + 0.5*q_val[589]*q_val[590]*q_val[592] + 0.5*q_val[591]*q_val[592]*q_val[593] + 0.5*q_val[594]*q_val[595]*q_val[596] + 0.5*q_val[594]*q_val[596]*q_val[597] + 0.5*q_val[595]*q_val[596]*q_val[598] + 0.5*q_val[597]*q_val[598]*q_val[599]
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
    q = gen.array(600)

    # 模型数据
    cubic_terms_list = [
    '0.5*q[0]*q[1]*q[2]',
    '0.5*q[0]*q[2]*q[3]',
    '0.5*q[1]*q[2]*q[4]',
    '0.5*q[3]*q[4]*q[5]',
    '0.5*q[6]*q[7]*q[8]',
    '0.5*q[6]*q[8]*q[9]',
    '0.5*q[7]*q[8]*q[10]',
    '0.5*q[9]*q[10]*q[11]',
    '0.5*q[12]*q[13]*q[14]',
    '0.5*q[12]*q[14]*q[15]',
    '0.5*q[13]*q[14]*q[16]',
    '0.5*q[15]*q[16]*q[17]',
    '0.5*q[18]*q[19]*q[20]',
    '0.5*q[18]*q[20]*q[21]',
    '0.5*q[19]*q[20]*q[22]',
    '0.5*q[21]*q[22]*q[23]',
    '0.5*q[24]*q[25]*q[26]',
    '0.5*q[24]*q[26]*q[27]',
    '0.5*q[25]*q[26]*q[28]',
    '0.5*q[27]*q[28]*q[29]',
    '0.5*q[30]*q[31]*q[32]',
    '0.5*q[30]*q[32]*q[33]',
    '0.5*q[31]*q[32]*q[34]',
    '0.5*q[33]*q[34]*q[35]',
    '0.5*q[36]*q[37]*q[38]',
    '0.5*q[36]*q[38]*q[39]',
    '0.5*q[37]*q[38]*q[40]',
    '0.5*q[39]*q[40]*q[41]',
    '0.5*q[42]*q[43]*q[44]',
    '0.5*q[42]*q[44]*q[45]',
    '0.5*q[43]*q[44]*q[46]',
    '0.5*q[45]*q[46]*q[47]',
    '0.5*q[48]*q[49]*q[50]',
    '0.5*q[48]*q[50]*q[51]',
    '0.5*q[49]*q[50]*q[52]',
    '0.5*q[51]*q[52]*q[53]',
    '0.5*q[54]*q[55]*q[56]',
    '0.5*q[54]*q[56]*q[57]',
    '0.5*q[55]*q[56]*q[58]',
    '0.5*q[57]*q[58]*q[59]',
    '0.5*q[60]*q[61]*q[62]',
    '0.5*q[60]*q[62]*q[63]',
    '0.5*q[61]*q[62]*q[64]',
    '0.5*q[63]*q[64]*q[65]',
    '0.5*q[66]*q[67]*q[68]',
    '0.5*q[66]*q[68]*q[69]',
    '0.5*q[67]*q[68]*q[70]',
    '0.5*q[69]*q[70]*q[71]',
    '0.5*q[72]*q[73]*q[74]',
    '0.5*q[72]*q[74]*q[75]',
    '0.5*q[73]*q[74]*q[76]',
    '0.5*q[75]*q[76]*q[77]',
    '0.5*q[78]*q[79]*q[80]',
    '0.5*q[78]*q[80]*q[81]',
    '0.5*q[79]*q[80]*q[82]',
    '0.5*q[81]*q[82]*q[83]',
    '0.5*q[84]*q[85]*q[86]',
    '0.5*q[84]*q[86]*q[87]',
    '0.5*q[85]*q[86]*q[88]',
    '0.5*q[87]*q[88]*q[89]',
    '0.5*q[90]*q[91]*q[92]',
    '0.5*q[90]*q[92]*q[93]',
    '0.5*q[91]*q[92]*q[94]',
    '0.5*q[93]*q[94]*q[95]',
    '0.5*q[96]*q[97]*q[98]',
    '0.5*q[96]*q[98]*q[99]',
    '0.5*q[97]*q[98]*q[100]',
    '0.5*q[99]*q[100]*q[101]',
    '0.5*q[102]*q[103]*q[104]',
    '0.5*q[102]*q[104]*q[105]',
    '0.5*q[103]*q[104]*q[106]',
    '0.5*q[105]*q[106]*q[107]',
    '0.5*q[108]*q[109]*q[110]',
    '0.5*q[108]*q[110]*q[111]',
    '0.5*q[109]*q[110]*q[112]',
    '0.5*q[111]*q[112]*q[113]',
    '0.5*q[114]*q[115]*q[116]',
    '0.5*q[114]*q[116]*q[117]',
    '0.5*q[115]*q[116]*q[118]',
    '0.5*q[117]*q[118]*q[119]',
    '0.5*q[120]*q[121]*q[122]',
    '0.5*q[120]*q[122]*q[123]',
    '0.5*q[121]*q[122]*q[124]',
    '0.5*q[123]*q[124]*q[125]',
    '0.5*q[126]*q[127]*q[128]',
    '0.5*q[126]*q[128]*q[129]',
    '0.5*q[127]*q[128]*q[130]',
    '0.5*q[129]*q[130]*q[131]',
    '0.5*q[132]*q[133]*q[134]',
    '0.5*q[132]*q[134]*q[135]',
    '0.5*q[133]*q[134]*q[136]',
    '0.5*q[135]*q[136]*q[137]',
    '0.5*q[138]*q[139]*q[140]',
    '0.5*q[138]*q[140]*q[141]',
    '0.5*q[139]*q[140]*q[142]',
    '0.5*q[141]*q[142]*q[143]',
    '0.5*q[144]*q[145]*q[146]',
    '0.5*q[144]*q[146]*q[147]',
    '0.5*q[145]*q[146]*q[148]',
    '0.5*q[147]*q[148]*q[149]',
    '0.5*q[150]*q[151]*q[152]',
    '0.5*q[150]*q[152]*q[153]',
    '0.5*q[151]*q[152]*q[154]',
    '0.5*q[153]*q[154]*q[155]',
    '0.5*q[156]*q[157]*q[158]',
    '0.5*q[156]*q[158]*q[159]',
    '0.5*q[157]*q[158]*q[160]',
    '0.5*q[159]*q[160]*q[161]',
    '0.5*q[162]*q[163]*q[164]',
    '0.5*q[162]*q[164]*q[165]',
    '0.5*q[163]*q[164]*q[166]',
    '0.5*q[165]*q[166]*q[167]',
    '0.5*q[168]*q[169]*q[170]',
    '0.5*q[168]*q[170]*q[171]',
    '0.5*q[169]*q[170]*q[172]',
    '0.5*q[171]*q[172]*q[173]',
    '0.5*q[174]*q[175]*q[176]',
    '0.5*q[174]*q[176]*q[177]',
    '0.5*q[175]*q[176]*q[178]',
    '0.5*q[177]*q[178]*q[179]',
    '0.5*q[180]*q[181]*q[182]',
    '0.5*q[180]*q[182]*q[183]',
    '0.5*q[181]*q[182]*q[184]',
    '0.5*q[183]*q[184]*q[185]',
    '0.5*q[186]*q[187]*q[188]',
    '0.5*q[186]*q[188]*q[189]',
    '0.5*q[187]*q[188]*q[190]',
    '0.5*q[189]*q[190]*q[191]',
    '0.5*q[192]*q[193]*q[194]',
    '0.5*q[192]*q[194]*q[195]',
    '0.5*q[193]*q[194]*q[196]',
    '0.5*q[195]*q[196]*q[197]',
    '0.5*q[198]*q[199]*q[200]',
    '0.5*q[198]*q[200]*q[201]',
    '0.5*q[199]*q[200]*q[202]',
    '0.5*q[201]*q[202]*q[203]',
    '0.5*q[204]*q[205]*q[206]',
    '0.5*q[204]*q[206]*q[207]',
    '0.5*q[205]*q[206]*q[208]',
    '0.5*q[207]*q[208]*q[209]',
    '0.5*q[210]*q[211]*q[212]',
    '0.5*q[210]*q[212]*q[213]',
    '0.5*q[211]*q[212]*q[214]',
    '0.5*q[213]*q[214]*q[215]',
    '0.5*q[216]*q[217]*q[218]',
    '0.5*q[216]*q[218]*q[219]',
    '0.5*q[217]*q[218]*q[220]',
    '0.5*q[219]*q[220]*q[221]',
    '0.5*q[222]*q[223]*q[224]',
    '0.5*q[222]*q[224]*q[225]',
    '0.5*q[223]*q[224]*q[226]',
    '0.5*q[225]*q[226]*q[227]',
    '0.5*q[228]*q[229]*q[230]',
    '0.5*q[228]*q[230]*q[231]',
    '0.5*q[229]*q[230]*q[232]',
    '0.5*q[231]*q[232]*q[233]',
    '0.5*q[234]*q[235]*q[236]',
    '0.5*q[234]*q[236]*q[237]',
    '0.5*q[235]*q[236]*q[238]',
    '0.5*q[237]*q[238]*q[239]',
    '0.5*q[240]*q[241]*q[242]',
    '0.5*q[240]*q[242]*q[243]',
    '0.5*q[241]*q[242]*q[244]',
    '0.5*q[243]*q[244]*q[245]',
    '0.5*q[246]*q[247]*q[248]',
    '0.5*q[246]*q[248]*q[249]',
    '0.5*q[247]*q[248]*q[250]',
    '0.5*q[249]*q[250]*q[251]',
    '0.5*q[252]*q[253]*q[254]',
    '0.5*q[252]*q[254]*q[255]',
    '0.5*q[253]*q[254]*q[256]',
    '0.5*q[255]*q[256]*q[257]',
    '0.5*q[258]*q[259]*q[260]',
    '0.5*q[258]*q[260]*q[261]',
    '0.5*q[259]*q[260]*q[262]',
    '0.5*q[261]*q[262]*q[263]',
    '0.5*q[264]*q[265]*q[266]',
    '0.5*q[264]*q[266]*q[267]',
    '0.5*q[265]*q[266]*q[268]',
    '0.5*q[267]*q[268]*q[269]',
    '0.5*q[270]*q[271]*q[272]',
    '0.5*q[270]*q[272]*q[273]',
    '0.5*q[271]*q[272]*q[274]',
    '0.5*q[273]*q[274]*q[275]',
    '0.5*q[276]*q[277]*q[278]',
    '0.5*q[276]*q[278]*q[279]',
    '0.5*q[277]*q[278]*q[280]',
    '0.5*q[279]*q[280]*q[281]',
    '0.5*q[282]*q[283]*q[284]',
    '0.5*q[282]*q[284]*q[285]',
    '0.5*q[283]*q[284]*q[286]',
    '0.5*q[285]*q[286]*q[287]',
    '0.5*q[288]*q[289]*q[290]',
    '0.5*q[288]*q[290]*q[291]',
    '0.5*q[289]*q[290]*q[292]',
    '0.5*q[291]*q[292]*q[293]',
    '0.5*q[294]*q[295]*q[296]',
    '0.5*q[294]*q[296]*q[297]',
    '0.5*q[295]*q[296]*q[298]',
    '0.5*q[297]*q[298]*q[299]',
    '0.5*q[300]*q[301]*q[302]',
    '0.5*q[300]*q[302]*q[303]',
    '0.5*q[301]*q[302]*q[304]',
    '0.5*q[303]*q[304]*q[305]',
    '0.5*q[306]*q[307]*q[308]',
    '0.5*q[306]*q[308]*q[309]',
    '0.5*q[307]*q[308]*q[310]',
    '0.5*q[309]*q[310]*q[311]',
    '0.5*q[312]*q[313]*q[314]',
    '0.5*q[312]*q[314]*q[315]',
    '0.5*q[313]*q[314]*q[316]',
    '0.5*q[315]*q[316]*q[317]',
    '0.5*q[318]*q[319]*q[320]',
    '0.5*q[318]*q[320]*q[321]',
    '0.5*q[319]*q[320]*q[322]',
    '0.5*q[321]*q[322]*q[323]',
    '0.5*q[324]*q[325]*q[326]',
    '0.5*q[324]*q[326]*q[327]',
    '0.5*q[325]*q[326]*q[328]',
    '0.5*q[327]*q[328]*q[329]',
    '0.5*q[330]*q[331]*q[332]',
    '0.5*q[330]*q[332]*q[333]',
    '0.5*q[331]*q[332]*q[334]',
    '0.5*q[333]*q[334]*q[335]',
    '0.5*q[336]*q[337]*q[338]',
    '0.5*q[336]*q[338]*q[339]',
    '0.5*q[337]*q[338]*q[340]',
    '0.5*q[339]*q[340]*q[341]',
    '0.5*q[342]*q[343]*q[344]',
    '0.5*q[342]*q[344]*q[345]',
    '0.5*q[343]*q[344]*q[346]',
    '0.5*q[345]*q[346]*q[347]',
    '0.5*q[348]*q[349]*q[350]',
    '0.5*q[348]*q[350]*q[351]',
    '0.5*q[349]*q[350]*q[352]',
    '0.5*q[351]*q[352]*q[353]',
    '0.5*q[354]*q[355]*q[356]',
    '0.5*q[354]*q[356]*q[357]',
    '0.5*q[355]*q[356]*q[358]',
    '0.5*q[357]*q[358]*q[359]',
    '0.5*q[360]*q[361]*q[362]',
    '0.5*q[360]*q[362]*q[363]',
    '0.5*q[361]*q[362]*q[364]',
    '0.5*q[363]*q[364]*q[365]',
    '0.5*q[366]*q[367]*q[368]',
    '0.5*q[366]*q[368]*q[369]',
    '0.5*q[367]*q[368]*q[370]',
    '0.5*q[369]*q[370]*q[371]',
    '0.5*q[372]*q[373]*q[374]',
    '0.5*q[372]*q[374]*q[375]',
    '0.5*q[373]*q[374]*q[376]',
    '0.5*q[375]*q[376]*q[377]',
    '0.5*q[378]*q[379]*q[380]',
    '0.5*q[378]*q[380]*q[381]',
    '0.5*q[379]*q[380]*q[382]',
    '0.5*q[381]*q[382]*q[383]',
    '0.5*q[384]*q[385]*q[386]',
    '0.5*q[384]*q[386]*q[387]',
    '0.5*q[385]*q[386]*q[388]',
    '0.5*q[387]*q[388]*q[389]',
    '0.5*q[390]*q[391]*q[392]',
    '0.5*q[390]*q[392]*q[393]',
    '0.5*q[391]*q[392]*q[394]',
    '0.5*q[393]*q[394]*q[395]',
    '0.5*q[396]*q[397]*q[398]',
    '0.5*q[396]*q[398]*q[399]',
    '0.5*q[397]*q[398]*q[400]',
    '0.5*q[399]*q[400]*q[401]',
    '0.5*q[402]*q[403]*q[404]',
    '0.5*q[402]*q[404]*q[405]',
    '0.5*q[403]*q[404]*q[406]',
    '0.5*q[405]*q[406]*q[407]',
    '0.5*q[408]*q[409]*q[410]',
    '0.5*q[408]*q[410]*q[411]',
    '0.5*q[409]*q[410]*q[412]',
    '0.5*q[411]*q[412]*q[413]',
    '0.5*q[414]*q[415]*q[416]',
    '0.5*q[414]*q[416]*q[417]',
    '0.5*q[415]*q[416]*q[418]',
    '0.5*q[417]*q[418]*q[419]',
    '0.5*q[420]*q[421]*q[422]',
    '0.5*q[420]*q[422]*q[423]',
    '0.5*q[421]*q[422]*q[424]',
    '0.5*q[423]*q[424]*q[425]',
    '0.5*q[426]*q[427]*q[428]',
    '0.5*q[426]*q[428]*q[429]',
    '0.5*q[427]*q[428]*q[430]',
    '0.5*q[429]*q[430]*q[431]',
    '0.5*q[432]*q[433]*q[434]',
    '0.5*q[432]*q[434]*q[435]',
    '0.5*q[433]*q[434]*q[436]',
    '0.5*q[435]*q[436]*q[437]',
    '0.5*q[438]*q[439]*q[440]',
    '0.5*q[438]*q[440]*q[441]',
    '0.5*q[439]*q[440]*q[442]',
    '0.5*q[441]*q[442]*q[443]',
    '0.5*q[444]*q[445]*q[446]',
    '0.5*q[444]*q[446]*q[447]',
    '0.5*q[445]*q[446]*q[448]',
    '0.5*q[447]*q[448]*q[449]',
    '0.5*q[450]*q[451]*q[452]',
    '0.5*q[450]*q[452]*q[453]',
    '0.5*q[451]*q[452]*q[454]',
    '0.5*q[453]*q[454]*q[455]',
    '0.5*q[456]*q[457]*q[458]',
    '0.5*q[456]*q[458]*q[459]',
    '0.5*q[457]*q[458]*q[460]',
    '0.5*q[459]*q[460]*q[461]',
    '0.5*q[462]*q[463]*q[464]',
    '0.5*q[462]*q[464]*q[465]',
    '0.5*q[463]*q[464]*q[466]',
    '0.5*q[465]*q[466]*q[467]',
    '0.5*q[468]*q[469]*q[470]',
    '0.5*q[468]*q[470]*q[471]',
    '0.5*q[469]*q[470]*q[472]',
    '0.5*q[471]*q[472]*q[473]',
    '0.5*q[474]*q[475]*q[476]',
    '0.5*q[474]*q[476]*q[477]',
    '0.5*q[475]*q[476]*q[478]',
    '0.5*q[477]*q[478]*q[479]',
    '0.5*q[480]*q[481]*q[482]',
    '0.5*q[480]*q[482]*q[483]',
    '0.5*q[481]*q[482]*q[484]',
    '0.5*q[483]*q[484]*q[485]',
    '0.5*q[486]*q[487]*q[488]',
    '0.5*q[486]*q[488]*q[489]',
    '0.5*q[487]*q[488]*q[490]',
    '0.5*q[489]*q[490]*q[491]',
    '0.5*q[492]*q[493]*q[494]',
    '0.5*q[492]*q[494]*q[495]',
    '0.5*q[493]*q[494]*q[496]',
    '0.5*q[495]*q[496]*q[497]',
    '0.5*q[498]*q[499]*q[500]',
    '0.5*q[498]*q[500]*q[501]',
    '0.5*q[499]*q[500]*q[502]',
    '0.5*q[501]*q[502]*q[503]',
    '0.5*q[504]*q[505]*q[506]',
    '0.5*q[504]*q[506]*q[507]',
    '0.5*q[505]*q[506]*q[508]',
    '0.5*q[507]*q[508]*q[509]',
    '0.5*q[510]*q[511]*q[512]',
    '0.5*q[510]*q[512]*q[513]',
    '0.5*q[511]*q[512]*q[514]',
    '0.5*q[513]*q[514]*q[515]',
    '0.5*q[516]*q[517]*q[518]',
    '0.5*q[516]*q[518]*q[519]',
    '0.5*q[517]*q[518]*q[520]',
    '0.5*q[519]*q[520]*q[521]',
    '0.5*q[522]*q[523]*q[524]',
    '0.5*q[522]*q[524]*q[525]',
    '0.5*q[523]*q[524]*q[526]',
    '0.5*q[525]*q[526]*q[527]',
    '0.5*q[528]*q[529]*q[530]',
    '0.5*q[528]*q[530]*q[531]',
    '0.5*q[529]*q[530]*q[532]',
    '0.5*q[531]*q[532]*q[533]',
    '0.5*q[534]*q[535]*q[536]',
    '0.5*q[534]*q[536]*q[537]',
    '0.5*q[535]*q[536]*q[538]',
    '0.5*q[537]*q[538]*q[539]',
    '0.5*q[540]*q[541]*q[542]',
    '0.5*q[540]*q[542]*q[543]',
    '0.5*q[541]*q[542]*q[544]',
    '0.5*q[543]*q[544]*q[545]',
    '0.5*q[546]*q[547]*q[548]',
    '0.5*q[546]*q[548]*q[549]',
    '0.5*q[547]*q[548]*q[550]',
    '0.5*q[549]*q[550]*q[551]',
    '0.5*q[552]*q[553]*q[554]',
    '0.5*q[552]*q[554]*q[555]',
    '0.5*q[553]*q[554]*q[556]',
    '0.5*q[555]*q[556]*q[557]',
    '0.5*q[558]*q[559]*q[560]',
    '0.5*q[558]*q[560]*q[561]',
    '0.5*q[559]*q[560]*q[562]',
    '0.5*q[561]*q[562]*q[563]',
    '0.5*q[564]*q[565]*q[566]',
    '0.5*q[564]*q[566]*q[567]',
    '0.5*q[565]*q[566]*q[568]',
    '0.5*q[567]*q[568]*q[569]',
    '0.5*q[570]*q[571]*q[572]',
    '0.5*q[570]*q[572]*q[573]',
    '0.5*q[571]*q[572]*q[574]',
    '0.5*q[573]*q[574]*q[575]',
    '0.5*q[576]*q[577]*q[578]',
    '0.5*q[576]*q[578]*q[579]',
    '0.5*q[577]*q[578]*q[580]',
    '0.5*q[579]*q[580]*q[581]',
    '0.5*q[582]*q[583]*q[584]',
    '0.5*q[582]*q[584]*q[585]',
    '0.5*q[583]*q[584]*q[586]',
    '0.5*q[585]*q[586]*q[587]',
    '0.5*q[588]*q[589]*q[590]',
    '0.5*q[588]*q[590]*q[591]',
    '0.5*q[589]*q[590]*q[592]',
    '0.5*q[591]*q[592]*q[593]',
    '0.5*q[594]*q[595]*q[596]',
    '0.5*q[594]*q[596]*q[597]',
    '0.5*q[595]*q[596]*q[598]',
    '0.5*q[597]*q[598]*q[599]'
    ]

    f_base = 1 + -0.5*q[2] + 0.5*q[0]*q[2] + 0.5*q[1]*q[2] + 1 + -0.5*q[3] + 0.5*q[0]*q[3] + 0.5*q[2]*q[3] + 1 + -0.5*q[4] + 0.5*q[1]*q[4] + 0.5*q[2]*q[4] + 1 + -0.5*q[5] + 0.5*q[3]*q[5] + 0.5*q[4]*q[5] + 1 + -0.5*q[8] + 0.5*q[6]*q[8] + 0.5*q[7]*q[8] + 1 + -0.5*q[9] + 0.5*q[6]*q[9] + 0.5*q[8]*q[9] + 1 + -0.5*q[10] + 0.5*q[7]*q[10] + 0.5*q[8]*q[10] + 1 + -0.5*q[11] + 0.5*q[9]*q[11] + 0.5*q[10]*q[11] + 1 + -0.5*q[14] + 0.5*q[12]*q[14] + 0.5*q[13]*q[14] + 1 + -0.5*q[15] + 0.5*q[12]*q[15] + 0.5*q[14]*q[15] + 1 + -0.5*q[16] + 0.5*q[13]*q[16] + 0.5*q[14]*q[16] + 1 + -0.5*q[17] + 0.5*q[15]*q[17] + 0.5*q[16]*q[17] + 1 + -0.5*q[20] + 0.5*q[18]*q[20] + 0.5*q[19]*q[20] + 1 + -0.5*q[21] + 0.5*q[18]*q[21] + 0.5*q[20]*q[21] + 1 + -0.5*q[22] + 0.5*q[19]*q[22] + 0.5*q[20]*q[22] + 1 + -0.5*q[23] + 0.5*q[21]*q[23] + 0.5*q[22]*q[23] + 1 + -0.5*q[26] + 0.5*q[24]*q[26] + 0.5*q[25]*q[26] + 1 + -0.5*q[27] + 0.5*q[24]*q[27] + 0.5*q[26]*q[27] + 1 + -0.5*q[28] + 0.5*q[25]*q[28] + 0.5*q[26]*q[28] + 1 + -0.5*q[29] + 0.5*q[27]*q[29] + 0.5*q[28]*q[29] + 1 + -0.5*q[32] + 0.5*q[30]*q[32] + 0.5*q[31]*q[32] + 1 + -0.5*q[33] + 0.5*q[30]*q[33] + 0.5*q[32]*q[33] + 1 + -0.5*q[34] + 0.5*q[31]*q[34] + 0.5*q[32]*q[34] + 1 + -0.5*q[35] + 0.5*q[33]*q[35] + 0.5*q[34]*q[35] + 1 + -0.5*q[38] + 0.5*q[36]*q[38] + 0.5*q[37]*q[38] + 1 + -0.5*q[39] + 0.5*q[36]*q[39] + 0.5*q[38]*q[39] + 1 + -0.5*q[40] + 0.5*q[37]*q[40] + 0.5*q[38]*q[40] + 1 + -0.5*q[41] + 0.5*q[39]*q[41] + 0.5*q[40]*q[41] + 1 + -0.5*q[44] + 0.5*q[42]*q[44] + 0.5*q[43]*q[44] + 1 + -0.5*q[45] + 0.5*q[42]*q[45] + 0.5*q[44]*q[45] + 1 + -0.5*q[46] + 0.5*q[43]*q[46] + 0.5*q[44]*q[46] + 1 + -0.5*q[47] + 0.5*q[45]*q[47] + 0.5*q[46]*q[47] + 1 + -0.5*q[50] + 0.5*q[48]*q[50] + 0.5*q[49]*q[50] + 1 + -0.5*q[51] + 0.5*q[48]*q[51] + 0.5*q[50]*q[51] + 1 + -0.5*q[52] + 0.5*q[49]*q[52] + 0.5*q[50]*q[52] + 1 + -0.5*q[53] + 0.5*q[51]*q[53] + 0.5*q[52]*q[53] + 1 + -0.5*q[56] + 0.5*q[54]*q[56] + 0.5*q[55]*q[56] + 1 + -0.5*q[57] + 0.5*q[54]*q[57] + 0.5*q[56]*q[57] + 1 + -0.5*q[58] + 0.5*q[55]*q[58] + 0.5*q[56]*q[58] + 1 + -0.5*q[59] + 0.5*q[57]*q[59] + 0.5*q[58]*q[59] + 1 + -0.5*q[62] + 0.5*q[60]*q[62] + 0.5*q[61]*q[62] + 1 + -0.5*q[63] + 0.5*q[60]*q[63] + 0.5*q[62]*q[63] + 1 + -0.5*q[64] + 0.5*q[61]*q[64] + 0.5*q[62]*q[64] + 1 + -0.5*q[65] + 0.5*q[63]*q[65] + 0.5*q[64]*q[65] + 1 + -0.5*q[68] + 0.5*q[66]*q[68] + 0.5*q[67]*q[68] + 1 + -0.5*q[69] + 0.5*q[66]*q[69] + 0.5*q[68]*q[69] + 1 + -0.5*q[70] + 0.5*q[67]*q[70] + 0.5*q[68]*q[70] + 1 + -0.5*q[71] + 0.5*q[69]*q[71] + 0.5*q[70]*q[71] + 1 + -0.5*q[74] + 0.5*q[72]*q[74] + 0.5*q[73]*q[74] + 1 + -0.5*q[75] + 0.5*q[72]*q[75] + 0.5*q[74]*q[75] + 1 + -0.5*q[76] + 0.5*q[73]*q[76] + 0.5*q[74]*q[76] + 1 + -0.5*q[77] + 0.5*q[75]*q[77] + 0.5*q[76]*q[77] + 1 + -0.5*q[80] + 0.5*q[78]*q[80] + 0.5*q[79]*q[80] + 1 + -0.5*q[81] + 0.5*q[78]*q[81] + 0.5*q[80]*q[81] + 1 + -0.5*q[82] + 0.5*q[79]*q[82] + 0.5*q[80]*q[82] + 1 + -0.5*q[83] + 0.5*q[81]*q[83] + 0.5*q[82]*q[83] + 1 + -0.5*q[86] + 0.5*q[84]*q[86] + 0.5*q[85]*q[86] + 1 + -0.5*q[87] + 0.5*q[84]*q[87] + 0.5*q[86]*q[87] + 1 + -0.5*q[88] + 0.5*q[85]*q[88] + 0.5*q[86]*q[88] + 1 + -0.5*q[89] + 0.5*q[87]*q[89] + 0.5*q[88]*q[89] + 1 + -0.5*q[92] + 0.5*q[90]*q[92] + 0.5*q[91]*q[92] + 1 + -0.5*q[93] + 0.5*q[90]*q[93] + 0.5*q[92]*q[93] + 1 + -0.5*q[94] + 0.5*q[91]*q[94] + 0.5*q[92]*q[94] + 1 + -0.5*q[95] + 0.5*q[93]*q[95] + 0.5*q[94]*q[95] + 1 + -0.5*q[98] + 0.5*q[96]*q[98] + 0.5*q[97]*q[98] + 1 + -0.5*q[99] + 0.5*q[96]*q[99] + 0.5*q[98]*q[99] + 1 + -0.5*q[100] + 0.5*q[97]*q[100] + 0.5*q[98]*q[100] + 1 + -0.5*q[101] + 0.5*q[99]*q[101] + 0.5*q[100]*q[101] + 1 + -0.5*q[104] + 0.5*q[102]*q[104] + 0.5*q[103]*q[104] + 1 + -0.5*q[105] + 0.5*q[102]*q[105] + 0.5*q[104]*q[105] + 1 + -0.5*q[106] + 0.5*q[103]*q[106] + 0.5*q[104]*q[106] + 1 + -0.5*q[107] + 0.5*q[105]*q[107] + 0.5*q[106]*q[107] + 1 + -0.5*q[110] + 0.5*q[108]*q[110] + 0.5*q[109]*q[110] + 1 + -0.5*q[111] + 0.5*q[108]*q[111] + 0.5*q[110]*q[111] + 1 + -0.5*q[112] + 0.5*q[109]*q[112] + 0.5*q[110]*q[112] + 1 + -0.5*q[113] + 0.5*q[111]*q[113] + 0.5*q[112]*q[113] + 1 + -0.5*q[116] + 0.5*q[114]*q[116] + 0.5*q[115]*q[116] + 1 + -0.5*q[117] + 0.5*q[114]*q[117] + 0.5*q[116]*q[117] + 1 + -0.5*q[118] + 0.5*q[115]*q[118] + 0.5*q[116]*q[118] + 1 + -0.5*q[119] + 0.5*q[117]*q[119] + 0.5*q[118]*q[119] + 1 + -0.5*q[122] + 0.5*q[120]*q[122] + 0.5*q[121]*q[122] + 1 + -0.5*q[123] + 0.5*q[120]*q[123] + 0.5*q[122]*q[123] + 1 + -0.5*q[124] + 0.5*q[121]*q[124] + 0.5*q[122]*q[124] + 1 + -0.5*q[125] + 0.5*q[123]*q[125] + 0.5*q[124]*q[125] + 1 + -0.5*q[128] + 0.5*q[126]*q[128] + 0.5*q[127]*q[128] + 1 + -0.5*q[129] + 0.5*q[126]*q[129] + 0.5*q[128]*q[129] + 1 + -0.5*q[130] + 0.5*q[127]*q[130] + 0.5*q[128]*q[130] + 1 + -0.5*q[131] + 0.5*q[129]*q[131] + 0.5*q[130]*q[131] + 1 + -0.5*q[134] + 0.5*q[132]*q[134] + 0.5*q[133]*q[134] + 1 + -0.5*q[135] + 0.5*q[132]*q[135] + 0.5*q[134]*q[135] + 1 + -0.5*q[136] + 0.5*q[133]*q[136] + 0.5*q[134]*q[136] + 1 + -0.5*q[137] + 0.5*q[135]*q[137] + 0.5*q[136]*q[137] + 1 + -0.5*q[140] + 0.5*q[138]*q[140] + 0.5*q[139]*q[140] + 1 + -0.5*q[141] + 0.5*q[138]*q[141] + 0.5*q[140]*q[141] + 1 + -0.5*q[142] + 0.5*q[139]*q[142] + 0.5*q[140]*q[142] + 1 + -0.5*q[143] + 0.5*q[141]*q[143] + 0.5*q[142]*q[143] + 1 + -0.5*q[146] + 0.5*q[144]*q[146] + 0.5*q[145]*q[146] + 1 + -0.5*q[147] + 0.5*q[144]*q[147] + 0.5*q[146]*q[147] + 1 + -0.5*q[148] + 0.5*q[145]*q[148] + 0.5*q[146]*q[148] + 1 + -0.5*q[149] + 0.5*q[147]*q[149] + 0.5*q[148]*q[149] + 1 + -0.5*q[152] + 0.5*q[150]*q[152] + 0.5*q[151]*q[152] + 1 + -0.5*q[153] + 0.5*q[150]*q[153] + 0.5*q[152]*q[153] + 1 + -0.5*q[154] + 0.5*q[151]*q[154] + 0.5*q[152]*q[154] + 1 + -0.5*q[155] + 0.5*q[153]*q[155] + 0.5*q[154]*q[155] + 1 + -0.5*q[158] + 0.5*q[156]*q[158] + 0.5*q[157]*q[158] + 1 + -0.5*q[159] + 0.5*q[156]*q[159] + 0.5*q[158]*q[159] + 1 + -0.5*q[160] + 0.5*q[157]*q[160] + 0.5*q[158]*q[160] + 1 + -0.5*q[161] + 0.5*q[159]*q[161] + 0.5*q[160]*q[161] + 1 + -0.5*q[164] + 0.5*q[162]*q[164] + 0.5*q[163]*q[164] + 1 + -0.5*q[165] + 0.5*q[162]*q[165] + 0.5*q[164]*q[165] + 1 + -0.5*q[166] + 0.5*q[163]*q[166] + 0.5*q[164]*q[166] + 1 + -0.5*q[167] + 0.5*q[165]*q[167] + 0.5*q[166]*q[167] + 1 + -0.5*q[170] + 0.5*q[168]*q[170] + 0.5*q[169]*q[170] + 1 + -0.5*q[171] + 0.5*q[168]*q[171] + 0.5*q[170]*q[171] + 1 + -0.5*q[172] + 0.5*q[169]*q[172] + 0.5*q[170]*q[172] + 1 + -0.5*q[173] + 0.5*q[171]*q[173] + 0.5*q[172]*q[173] + 1 + -0.5*q[176] + 0.5*q[174]*q[176] + 0.5*q[175]*q[176] + 1 + -0.5*q[177] + 0.5*q[174]*q[177] + 0.5*q[176]*q[177] + 1 + -0.5*q[178] + 0.5*q[175]*q[178] + 0.5*q[176]*q[178] + 1 + -0.5*q[179] + 0.5*q[177]*q[179] + 0.5*q[178]*q[179] + 1 + -0.5*q[182] + 0.5*q[180]*q[182] + 0.5*q[181]*q[182] + 1 + -0.5*q[183] + 0.5*q[180]*q[183] + 0.5*q[182]*q[183] + 1 + -0.5*q[184] + 0.5*q[181]*q[184] + 0.5*q[182]*q[184] + 1 + -0.5*q[185] + 0.5*q[183]*q[185] + 0.5*q[184]*q[185] + 1 + -0.5*q[188] + 0.5*q[186]*q[188] + 0.5*q[187]*q[188] + 1 + -0.5*q[189] + 0.5*q[186]*q[189] + 0.5*q[188]*q[189] + 1 + -0.5*q[190] + 0.5*q[187]*q[190] + 0.5*q[188]*q[190] + 1 + -0.5*q[191] + 0.5*q[189]*q[191] + 0.5*q[190]*q[191] + 1 + -0.5*q[194] + 0.5*q[192]*q[194] + 0.5*q[193]*q[194] + 1 + -0.5*q[195] + 0.5*q[192]*q[195] + 0.5*q[194]*q[195] + 1 + -0.5*q[196] + 0.5*q[193]*q[196] + 0.5*q[194]*q[196] + 1 + -0.5*q[197] + 0.5*q[195]*q[197] + 0.5*q[196]*q[197] + 1 + -0.5*q[200] + 0.5*q[198]*q[200] + 0.5*q[199]*q[200] + 1 + -0.5*q[201] + 0.5*q[198]*q[201] + 0.5*q[200]*q[201] + 1 + -0.5*q[202] + 0.5*q[199]*q[202] + 0.5*q[200]*q[202] + 1 + -0.5*q[203] + 0.5*q[201]*q[203] + 0.5*q[202]*q[203] + 1 + -0.5*q[206] + 0.5*q[204]*q[206] + 0.5*q[205]*q[206] + 1 + -0.5*q[207] + 0.5*q[204]*q[207] + 0.5*q[206]*q[207] + 1 + -0.5*q[208] + 0.5*q[205]*q[208] + 0.5*q[206]*q[208] + 1 + -0.5*q[209] + 0.5*q[207]*q[209] + 0.5*q[208]*q[209] + 1 + -0.5*q[212] + 0.5*q[210]*q[212] + 0.5*q[211]*q[212] + 1 + -0.5*q[213] + 0.5*q[210]*q[213] + 0.5*q[212]*q[213] + 1 + -0.5*q[214] + 0.5*q[211]*q[214] + 0.5*q[212]*q[214] + 1 + -0.5*q[215] + 0.5*q[213]*q[215] + 0.5*q[214]*q[215] + 1 + -0.5*q[218] + 0.5*q[216]*q[218] + 0.5*q[217]*q[218] + 1 + -0.5*q[219] + 0.5*q[216]*q[219] + 0.5*q[218]*q[219] + 1 + -0.5*q[220] + 0.5*q[217]*q[220] + 0.5*q[218]*q[220] + 1 + -0.5*q[221] + 0.5*q[219]*q[221] + 0.5*q[220]*q[221] + 1 + -0.5*q[224] + 0.5*q[222]*q[224] + 0.5*q[223]*q[224] + 1 + -0.5*q[225] + 0.5*q[222]*q[225] + 0.5*q[224]*q[225] + 1 + -0.5*q[226] + 0.5*q[223]*q[226] + 0.5*q[224]*q[226] + 1 + -0.5*q[227] + 0.5*q[225]*q[227] + 0.5*q[226]*q[227] + 1 + -0.5*q[230] + 0.5*q[228]*q[230] + 0.5*q[229]*q[230] + 1 + -0.5*q[231] + 0.5*q[228]*q[231] + 0.5*q[230]*q[231] + 1 + -0.5*q[232] + 0.5*q[229]*q[232] + 0.5*q[230]*q[232] + 1 + -0.5*q[233] + 0.5*q[231]*q[233] + 0.5*q[232]*q[233] + 1 + -0.5*q[236] + 0.5*q[234]*q[236] + 0.5*q[235]*q[236] + 1 + -0.5*q[237] + 0.5*q[234]*q[237] + 0.5*q[236]*q[237] + 1 + -0.5*q[238] + 0.5*q[235]*q[238] + 0.5*q[236]*q[238] + 1 + -0.5*q[239] + 0.5*q[237]*q[239] + 0.5*q[238]*q[239] + 1 + -0.5*q[242] + 0.5*q[240]*q[242] + 0.5*q[241]*q[242] + 1 + -0.5*q[243] + 0.5*q[240]*q[243] + 0.5*q[242]*q[243] + 1 + -0.5*q[244] + 0.5*q[241]*q[244] + 0.5*q[242]*q[244] + 1 + -0.5*q[245] + 0.5*q[243]*q[245] + 0.5*q[244]*q[245] + 1 + -0.5*q[248] + 0.5*q[246]*q[248] + 0.5*q[247]*q[248] + 1 + -0.5*q[249] + 0.5*q[246]*q[249] + 0.5*q[248]*q[249] + 1 + -0.5*q[250] + 0.5*q[247]*q[250] + 0.5*q[248]*q[250] + 1 + -0.5*q[251] + 0.5*q[249]*q[251] + 0.5*q[250]*q[251] + 1 + -0.5*q[254] + 0.5*q[252]*q[254] + 0.5*q[253]*q[254] + 1 + -0.5*q[255] + 0.5*q[252]*q[255] + 0.5*q[254]*q[255] + 1 + -0.5*q[256] + 0.5*q[253]*q[256] + 0.5*q[254]*q[256] + 1 + -0.5*q[257] + 0.5*q[255]*q[257] + 0.5*q[256]*q[257] + 1 + -0.5*q[260] + 0.5*q[258]*q[260] + 0.5*q[259]*q[260] + 1 + -0.5*q[261] + 0.5*q[258]*q[261] + 0.5*q[260]*q[261] + 1 + -0.5*q[262] + 0.5*q[259]*q[262] + 0.5*q[260]*q[262] + 1 + -0.5*q[263] + 0.5*q[261]*q[263] + 0.5*q[262]*q[263] + 1 + -0.5*q[266] + 0.5*q[264]*q[266] + 0.5*q[265]*q[266] + 1 + -0.5*q[267] + 0.5*q[264]*q[267] + 0.5*q[266]*q[267] + 1 + -0.5*q[268] + 0.5*q[265]*q[268] + 0.5*q[266]*q[268] + 1 + -0.5*q[269] + 0.5*q[267]*q[269] + 0.5*q[268]*q[269] + 1 + -0.5*q[272] + 0.5*q[270]*q[272] + 0.5*q[271]*q[272] + 1 + -0.5*q[273] + 0.5*q[270]*q[273] + 0.5*q[272]*q[273] + 1 + -0.5*q[274] + 0.5*q[271]*q[274] + 0.5*q[272]*q[274] + 1 + -0.5*q[275] + 0.5*q[273]*q[275] + 0.5*q[274]*q[275] + 1 + -0.5*q[278] + 0.5*q[276]*q[278] + 0.5*q[277]*q[278] + 1 + -0.5*q[279] + 0.5*q[276]*q[279] + 0.5*q[278]*q[279] + 1 + -0.5*q[280] + 0.5*q[277]*q[280] + 0.5*q[278]*q[280] + 1 + -0.5*q[281] + 0.5*q[279]*q[281] + 0.5*q[280]*q[281] + 1 + -0.5*q[284] + 0.5*q[282]*q[284] + 0.5*q[283]*q[284] + 1 + -0.5*q[285] + 0.5*q[282]*q[285] + 0.5*q[284]*q[285] + 1 + -0.5*q[286] + 0.5*q[283]*q[286] + 0.5*q[284]*q[286] + 1 + -0.5*q[287] + 0.5*q[285]*q[287] + 0.5*q[286]*q[287] + 1 + -0.5*q[290] + 0.5*q[288]*q[290] + 0.5*q[289]*q[290] + 1 + -0.5*q[291] + 0.5*q[288]*q[291] + 0.5*q[290]*q[291] + 1 + -0.5*q[292] + 0.5*q[289]*q[292] + 0.5*q[290]*q[292] + 1 + -0.5*q[293] + 0.5*q[291]*q[293] + 0.5*q[292]*q[293] + 1 + -0.5*q[296] + 0.5*q[294]*q[296] + 0.5*q[295]*q[296] + 1 + -0.5*q[297] + 0.5*q[294]*q[297] + 0.5*q[296]*q[297] + 1 + -0.5*q[298] + 0.5*q[295]*q[298] + 0.5*q[296]*q[298] + 1 + -0.5*q[299] + 0.5*q[297]*q[299] + 0.5*q[298]*q[299] + 1 + -0.5*q[302] + 0.5*q[300]*q[302] + 0.5*q[301]*q[302] + 1 + -0.5*q[303] + 0.5*q[300]*q[303] + 0.5*q[302]*q[303] + 1 + -0.5*q[304] + 0.5*q[301]*q[304] + 0.5*q[302]*q[304] + 1 + -0.5*q[305] + 0.5*q[303]*q[305] + 0.5*q[304]*q[305] + 1 + -0.5*q[308] + 0.5*q[306]*q[308] + 0.5*q[307]*q[308] + 1 + -0.5*q[309] + 0.5*q[306]*q[309] + 0.5*q[308]*q[309] + 1 + -0.5*q[310] + 0.5*q[307]*q[310] + 0.5*q[308]*q[310] + 1 + -0.5*q[311] + 0.5*q[309]*q[311] + 0.5*q[310]*q[311] + 1 + -0.5*q[314] + 0.5*q[312]*q[314] + 0.5*q[313]*q[314] + 1 + -0.5*q[315] + 0.5*q[312]*q[315] + 0.5*q[314]*q[315] + 1 + -0.5*q[316] + 0.5*q[313]*q[316] + 0.5*q[314]*q[316] + 1 + -0.5*q[317] + 0.5*q[315]*q[317] + 0.5*q[316]*q[317] + 1 + -0.5*q[320] + 0.5*q[318]*q[320] + 0.5*q[319]*q[320] + 1 + -0.5*q[321] + 0.5*q[318]*q[321] + 0.5*q[320]*q[321] + 1 + -0.5*q[322] + 0.5*q[319]*q[322] + 0.5*q[320]*q[322] + 1 + -0.5*q[323] + 0.5*q[321]*q[323] + 0.5*q[322]*q[323] + 1 + -0.5*q[326] + 0.5*q[324]*q[326] + 0.5*q[325]*q[326] + 1 + -0.5*q[327] + 0.5*q[324]*q[327] + 0.5*q[326]*q[327] + 1 + -0.5*q[328] + 0.5*q[325]*q[328] + 0.5*q[326]*q[328] + 1 + -0.5*q[329] + 0.5*q[327]*q[329] + 0.5*q[328]*q[329] + 1 + -0.5*q[332] + 0.5*q[330]*q[332] + 0.5*q[331]*q[332] + 1 + -0.5*q[333] + 0.5*q[330]*q[333] + 0.5*q[332]*q[333] + 1 + -0.5*q[334] + 0.5*q[331]*q[334] + 0.5*q[332]*q[334] + 1 + -0.5*q[335] + 0.5*q[333]*q[335] + 0.5*q[334]*q[335] + 1 + -0.5*q[338] + 0.5*q[336]*q[338] + 0.5*q[337]*q[338] + 1 + -0.5*q[339] + 0.5*q[336]*q[339] + 0.5*q[338]*q[339] + 1 + -0.5*q[340] + 0.5*q[337]*q[340] + 0.5*q[338]*q[340] + 1 + -0.5*q[341] + 0.5*q[339]*q[341] + 0.5*q[340]*q[341] + 1 + -0.5*q[344] + 0.5*q[342]*q[344] + 0.5*q[343]*q[344] + 1 + -0.5*q[345] + 0.5*q[342]*q[345] + 0.5*q[344]*q[345] + 1 + -0.5*q[346] + 0.5*q[343]*q[346] + 0.5*q[344]*q[346] + 1 + -0.5*q[347] + 0.5*q[345]*q[347] + 0.5*q[346]*q[347] + 1 + -0.5*q[350] + 0.5*q[348]*q[350] + 0.5*q[349]*q[350] + 1 + -0.5*q[351] + 0.5*q[348]*q[351] + 0.5*q[350]*q[351] + 1 + -0.5*q[352] + 0.5*q[349]*q[352] + 0.5*q[350]*q[352] + 1 + -0.5*q[353] + 0.5*q[351]*q[353] + 0.5*q[352]*q[353] + 1 + -0.5*q[356] + 0.5*q[354]*q[356] + 0.5*q[355]*q[356] + 1 + -0.5*q[357] + 0.5*q[354]*q[357] + 0.5*q[356]*q[357] + 1 + -0.5*q[358] + 0.5*q[355]*q[358] + 0.5*q[356]*q[358] + 1 + -0.5*q[359] + 0.5*q[357]*q[359] + 0.5*q[358]*q[359] + 1 + -0.5*q[362] + 0.5*q[360]*q[362] + 0.5*q[361]*q[362] + 1 + -0.5*q[363] + 0.5*q[360]*q[363] + 0.5*q[362]*q[363] + 1 + -0.5*q[364] + 0.5*q[361]*q[364] + 0.5*q[362]*q[364] + 1 + -0.5*q[365] + 0.5*q[363]*q[365] + 0.5*q[364]*q[365] + 1 + -0.5*q[368] + 0.5*q[366]*q[368] + 0.5*q[367]*q[368] + 1 + -0.5*q[369] + 0.5*q[366]*q[369] + 0.5*q[368]*q[369] + 1 + -0.5*q[370] + 0.5*q[367]*q[370] + 0.5*q[368]*q[370] + 1 + -0.5*q[371] + 0.5*q[369]*q[371] + 0.5*q[370]*q[371] + 1 + -0.5*q[374] + 0.5*q[372]*q[374] + 0.5*q[373]*q[374] + 1 + -0.5*q[375] + 0.5*q[372]*q[375] + 0.5*q[374]*q[375] + 1 + -0.5*q[376] + 0.5*q[373]*q[376] + 0.5*q[374]*q[376] + 1 + -0.5*q[377] + 0.5*q[375]*q[377] + 0.5*q[376]*q[377] + 1 + -0.5*q[380] + 0.5*q[378]*q[380] + 0.5*q[379]*q[380] + 1 + -0.5*q[381] + 0.5*q[378]*q[381] + 0.5*q[380]*q[381] + 1 + -0.5*q[382] + 0.5*q[379]*q[382] + 0.5*q[380]*q[382] + 1 + -0.5*q[383] + 0.5*q[381]*q[383] + 0.5*q[382]*q[383] + 1 + -0.5*q[386] + 0.5*q[384]*q[386] + 0.5*q[385]*q[386] + 1 + -0.5*q[387] + 0.5*q[384]*q[387] + 0.5*q[386]*q[387] + 1 + -0.5*q[388] + 0.5*q[385]*q[388] + 0.5*q[386]*q[388] + 1 + -0.5*q[389] + 0.5*q[387]*q[389] + 0.5*q[388]*q[389] + 1 + -0.5*q[392] + 0.5*q[390]*q[392] + 0.5*q[391]*q[392] + 1 + -0.5*q[393] + 0.5*q[390]*q[393] + 0.5*q[392]*q[393] + 1 + -0.5*q[394] + 0.5*q[391]*q[394] + 0.5*q[392]*q[394] + 1 + -0.5*q[395] + 0.5*q[393]*q[395] + 0.5*q[394]*q[395] + 1 + -0.5*q[398] + 0.5*q[396]*q[398] + 0.5*q[397]*q[398] + 1 + -0.5*q[399] + 0.5*q[396]*q[399] + 0.5*q[398]*q[399] + 1 + -0.5*q[400] + 0.5*q[397]*q[400] + 0.5*q[398]*q[400] + 1 + -0.5*q[401] + 0.5*q[399]*q[401] + 0.5*q[400]*q[401] + 1 + -0.5*q[404] + 0.5*q[402]*q[404] + 0.5*q[403]*q[404] + 1 + -0.5*q[405] + 0.5*q[402]*q[405] + 0.5*q[404]*q[405] + 1 + -0.5*q[406] + 0.5*q[403]*q[406] + 0.5*q[404]*q[406] + 1 + -0.5*q[407] + 0.5*q[405]*q[407] + 0.5*q[406]*q[407] + 1 + -0.5*q[410] + 0.5*q[408]*q[410] + 0.5*q[409]*q[410] + 1 + -0.5*q[411] + 0.5*q[408]*q[411] + 0.5*q[410]*q[411] + 1 + -0.5*q[412] + 0.5*q[409]*q[412] + 0.5*q[410]*q[412] + 1 + -0.5*q[413] + 0.5*q[411]*q[413] + 0.5*q[412]*q[413] + 1 + -0.5*q[416] + 0.5*q[414]*q[416] + 0.5*q[415]*q[416] + 1 + -0.5*q[417] + 0.5*q[414]*q[417] + 0.5*q[416]*q[417] + 1 + -0.5*q[418] + 0.5*q[415]*q[418] + 0.5*q[416]*q[418] + 1 + -0.5*q[419] + 0.5*q[417]*q[419] + 0.5*q[418]*q[419] + 1 + -0.5*q[422] + 0.5*q[420]*q[422] + 0.5*q[421]*q[422] + 1 + -0.5*q[423] + 0.5*q[420]*q[423] + 0.5*q[422]*q[423] + 1 + -0.5*q[424] + 0.5*q[421]*q[424] + 0.5*q[422]*q[424] + 1 + -0.5*q[425] + 0.5*q[423]*q[425] + 0.5*q[424]*q[425] + 1 + -0.5*q[428] + 0.5*q[426]*q[428] + 0.5*q[427]*q[428] + 1 + -0.5*q[429] + 0.5*q[426]*q[429] + 0.5*q[428]*q[429] + 1 + -0.5*q[430] + 0.5*q[427]*q[430] + 0.5*q[428]*q[430] + 1 + -0.5*q[431] + 0.5*q[429]*q[431] + 0.5*q[430]*q[431] + 1 + -0.5*q[434] + 0.5*q[432]*q[434] + 0.5*q[433]*q[434] + 1 + -0.5*q[435] + 0.5*q[432]*q[435] + 0.5*q[434]*q[435] + 1 + -0.5*q[436] + 0.5*q[433]*q[436] + 0.5*q[434]*q[436] + 1 + -0.5*q[437] + 0.5*q[435]*q[437] + 0.5*q[436]*q[437] + 1 + -0.5*q[440] + 0.5*q[438]*q[440] + 0.5*q[439]*q[440] + 1 + -0.5*q[441] + 0.5*q[438]*q[441] + 0.5*q[440]*q[441] + 1 + -0.5*q[442] + 0.5*q[439]*q[442] + 0.5*q[440]*q[442] + 1 + -0.5*q[443] + 0.5*q[441]*q[443] + 0.5*q[442]*q[443] + 1 + -0.5*q[446] + 0.5*q[444]*q[446] + 0.5*q[445]*q[446] + 1 + -0.5*q[447] + 0.5*q[444]*q[447] + 0.5*q[446]*q[447] + 1 + -0.5*q[448] + 0.5*q[445]*q[448] + 0.5*q[446]*q[448] + 1 + -0.5*q[449] + 0.5*q[447]*q[449] + 0.5*q[448]*q[449] + 1 + -0.5*q[452] + 0.5*q[450]*q[452] + 0.5*q[451]*q[452] + 1 + -0.5*q[453] + 0.5*q[450]*q[453] + 0.5*q[452]*q[453] + 1 + -0.5*q[454] + 0.5*q[451]*q[454] + 0.5*q[452]*q[454] + 1 + -0.5*q[455] + 0.5*q[453]*q[455] + 0.5*q[454]*q[455] + 1 + -0.5*q[458] + 0.5*q[456]*q[458] + 0.5*q[457]*q[458] + 1 + -0.5*q[459] + 0.5*q[456]*q[459] + 0.5*q[458]*q[459] + 1 + -0.5*q[460] + 0.5*q[457]*q[460] + 0.5*q[458]*q[460] + 1 + -0.5*q[461] + 0.5*q[459]*q[461] + 0.5*q[460]*q[461] + 1 + -0.5*q[464] + 0.5*q[462]*q[464] + 0.5*q[463]*q[464] + 1 + -0.5*q[465] + 0.5*q[462]*q[465] + 0.5*q[464]*q[465] + 1 + -0.5*q[466] + 0.5*q[463]*q[466] + 0.5*q[464]*q[466] + 1 + -0.5*q[467] + 0.5*q[465]*q[467] + 0.5*q[466]*q[467] + 1 + -0.5*q[470] + 0.5*q[468]*q[470] + 0.5*q[469]*q[470] + 1 + -0.5*q[471] + 0.5*q[468]*q[471] + 0.5*q[470]*q[471] + 1 + -0.5*q[472] + 0.5*q[469]*q[472] + 0.5*q[470]*q[472] + 1 + -0.5*q[473] + 0.5*q[471]*q[473] + 0.5*q[472]*q[473] + 1 + -0.5*q[476] + 0.5*q[474]*q[476] + 0.5*q[475]*q[476] + 1 + -0.5*q[477] + 0.5*q[474]*q[477] + 0.5*q[476]*q[477] + 1 + -0.5*q[478] + 0.5*q[475]*q[478] + 0.5*q[476]*q[478] + 1 + -0.5*q[479] + 0.5*q[477]*q[479] + 0.5*q[478]*q[479] + 1 + -0.5*q[482] + 0.5*q[480]*q[482] + 0.5*q[481]*q[482] + 1 + -0.5*q[483] + 0.5*q[480]*q[483] + 0.5*q[482]*q[483] + 1 + -0.5*q[484] + 0.5*q[481]*q[484] + 0.5*q[482]*q[484] + 1 + -0.5*q[485] + 0.5*q[483]*q[485] + 0.5*q[484]*q[485] + 1 + -0.5*q[488] + 0.5*q[486]*q[488] + 0.5*q[487]*q[488] + 1 + -0.5*q[489] + 0.5*q[486]*q[489] + 0.5*q[488]*q[489] + 1 + -0.5*q[490] + 0.5*q[487]*q[490] + 0.5*q[488]*q[490] + 1 + -0.5*q[491] + 0.5*q[489]*q[491] + 0.5*q[490]*q[491] + 1 + -0.5*q[494] + 0.5*q[492]*q[494] + 0.5*q[493]*q[494] + 1 + -0.5*q[495] + 0.5*q[492]*q[495] + 0.5*q[494]*q[495] + 1 + -0.5*q[496] + 0.5*q[493]*q[496] + 0.5*q[494]*q[496] + 1 + -0.5*q[497] + 0.5*q[495]*q[497] + 0.5*q[496]*q[497] + 1 + -0.5*q[500] + 0.5*q[498]*q[500] + 0.5*q[499]*q[500] + 1 + -0.5*q[501] + 0.5*q[498]*q[501] + 0.5*q[500]*q[501] + 1 + -0.5*q[502] + 0.5*q[499]*q[502] + 0.5*q[500]*q[502] + 1 + -0.5*q[503] + 0.5*q[501]*q[503] + 0.5*q[502]*q[503] + 1 + -0.5*q[506] + 0.5*q[504]*q[506] + 0.5*q[505]*q[506] + 1 + -0.5*q[507] + 0.5*q[504]*q[507] + 0.5*q[506]*q[507] + 1 + -0.5*q[508] + 0.5*q[505]*q[508] + 0.5*q[506]*q[508] + 1 + -0.5*q[509] + 0.5*q[507]*q[509] + 0.5*q[508]*q[509] + 1 + -0.5*q[512] + 0.5*q[510]*q[512] + 0.5*q[511]*q[512] + 1 + -0.5*q[513] + 0.5*q[510]*q[513] + 0.5*q[512]*q[513] + 1 + -0.5*q[514] + 0.5*q[511]*q[514] + 0.5*q[512]*q[514] + 1 + -0.5*q[515] + 0.5*q[513]*q[515] + 0.5*q[514]*q[515] + 1 + -0.5*q[518] + 0.5*q[516]*q[518] + 0.5*q[517]*q[518] + 1 + -0.5*q[519] + 0.5*q[516]*q[519] + 0.5*q[518]*q[519] + 1 + -0.5*q[520] + 0.5*q[517]*q[520] + 0.5*q[518]*q[520] + 1 + -0.5*q[521] + 0.5*q[519]*q[521] + 0.5*q[520]*q[521] + 1 + -0.5*q[524] + 0.5*q[522]*q[524] + 0.5*q[523]*q[524] + 1 + -0.5*q[525] + 0.5*q[522]*q[525] + 0.5*q[524]*q[525] + 1 + -0.5*q[526] + 0.5*q[523]*q[526] + 0.5*q[524]*q[526] + 1 + -0.5*q[527] + 0.5*q[525]*q[527] + 0.5*q[526]*q[527] + 1 + -0.5*q[530] + 0.5*q[528]*q[530] + 0.5*q[529]*q[530] + 1 + -0.5*q[531] + 0.5*q[528]*q[531] + 0.5*q[530]*q[531] + 1 + -0.5*q[532] + 0.5*q[529]*q[532] + 0.5*q[530]*q[532] + 1 + -0.5*q[533] + 0.5*q[531]*q[533] + 0.5*q[532]*q[533] + 1 + -0.5*q[536] + 0.5*q[534]*q[536] + 0.5*q[535]*q[536] + 1 + -0.5*q[537] + 0.5*q[534]*q[537] + 0.5*q[536]*q[537] + 1 + -0.5*q[538] + 0.5*q[535]*q[538] + 0.5*q[536]*q[538] + 1 + -0.5*q[539] + 0.5*q[537]*q[539] + 0.5*q[538]*q[539] + 1 + -0.5*q[542] + 0.5*q[540]*q[542] + 0.5*q[541]*q[542] + 1 + -0.5*q[543] + 0.5*q[540]*q[543] + 0.5*q[542]*q[543] + 1 + -0.5*q[544] + 0.5*q[541]*q[544] + 0.5*q[542]*q[544] + 1 + -0.5*q[545] + 0.5*q[543]*q[545] + 0.5*q[544]*q[545] + 1 + -0.5*q[548] + 0.5*q[546]*q[548] + 0.5*q[547]*q[548] + 1 + -0.5*q[549] + 0.5*q[546]*q[549] + 0.5*q[548]*q[549] + 1 + -0.5*q[550] + 0.5*q[547]*q[550] + 0.5*q[548]*q[550] + 1 + -0.5*q[551] + 0.5*q[549]*q[551] + 0.5*q[550]*q[551] + 1 + -0.5*q[554] + 0.5*q[552]*q[554] + 0.5*q[553]*q[554] + 1 + -0.5*q[555] + 0.5*q[552]*q[555] + 0.5*q[554]*q[555] + 1 + -0.5*q[556] + 0.5*q[553]*q[556] + 0.5*q[554]*q[556] + 1 + -0.5*q[557] + 0.5*q[555]*q[557] + 0.5*q[556]*q[557] + 1 + -0.5*q[560] + 0.5*q[558]*q[560] + 0.5*q[559]*q[560] + 1 + -0.5*q[561] + 0.5*q[558]*q[561] + 0.5*q[560]*q[561] + 1 + -0.5*q[562] + 0.5*q[559]*q[562] + 0.5*q[560]*q[562] + 1 + -0.5*q[563] + 0.5*q[561]*q[563] + 0.5*q[562]*q[563] + 1 + -0.5*q[566] + 0.5*q[564]*q[566] + 0.5*q[565]*q[566] + 1 + -0.5*q[567] + 0.5*q[564]*q[567] + 0.5*q[566]*q[567] + 1 + -0.5*q[568] + 0.5*q[565]*q[568] + 0.5*q[566]*q[568] + 1 + -0.5*q[569] + 0.5*q[567]*q[569] + 0.5*q[568]*q[569] + 1 + -0.5*q[572] + 0.5*q[570]*q[572] + 0.5*q[571]*q[572] + 1 + -0.5*q[573] + 0.5*q[570]*q[573] + 0.5*q[572]*q[573] + 1 + -0.5*q[574] + 0.5*q[571]*q[574] + 0.5*q[572]*q[574] + 1 + -0.5*q[575] + 0.5*q[573]*q[575] + 0.5*q[574]*q[575] + 1 + -0.5*q[578] + 0.5*q[576]*q[578] + 0.5*q[577]*q[578] + 1 + -0.5*q[579] + 0.5*q[576]*q[579] + 0.5*q[578]*q[579] + 1 + -0.5*q[580] + 0.5*q[577]*q[580] + 0.5*q[578]*q[580] + 1 + -0.5*q[581] + 0.5*q[579]*q[581] + 0.5*q[580]*q[581] + 1 + -0.5*q[584] + 0.5*q[582]*q[584] + 0.5*q[583]*q[584] + 1 + -0.5*q[585] + 0.5*q[582]*q[585] + 0.5*q[584]*q[585] + 1 + -0.5*q[586] + 0.5*q[583]*q[586] + 0.5*q[584]*q[586] + 1 + -0.5*q[587] + 0.5*q[585]*q[587] + 0.5*q[586]*q[587] + 1 + -0.5*q[590] + 0.5*q[588]*q[590] + 0.5*q[589]*q[590] + 1 + -0.5*q[591] + 0.5*q[588]*q[591] + 0.5*q[590]*q[591] + 1 + -0.5*q[592] + 0.5*q[589]*q[592] + 0.5*q[590]*q[592] + 1 + -0.5*q[593] + 0.5*q[591]*q[593] + 0.5*q[592]*q[593] + 1 + -0.5*q[596] + 0.5*q[594]*q[596] + 0.5*q[595]*q[596] + 1 + -0.5*q[597] + 0.5*q[594]*q[597] + 0.5*q[596]*q[597] + 1 + -0.5*q[598] + 0.5*q[595]*q[598] + 0.5*q[596]*q[598] + 1 + -0.5*q[599] + 0.5*q[597]*q[599] + 0.5*q[598]*q[599]

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