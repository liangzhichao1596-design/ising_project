from neal import SimulatedAnnealingSampler
import sympy as sp
import time  # 用于计时

# ==============================================
# 动态 q 定义
# ==============================================
class DynamicSymbol:
    def __getitem__(self, index):
        return sp.Symbol(f"q{index}")
q = DynamicSymbol()

# ==============================================
# 你的完整公式（替换成你自己的）
# ==============================================
f = 2*q[0]*q[2] + 2 + 2*q[1]*q[3] + 2 + q[0]*q[3] + -2*q[0]*q[4] + -2*q[3]*q[4] + -q[0] + -q[3] + 2*q[4] + 3 + q[2]*q[1] + -2*q[2]*q[5] + -2*q[1]*q[5] + -q[2] + -q[1] + 2*q[5] + 3 + q[4]*q[5] + -2*q[4]*q[6] + -2*q[5]*q[6] + q[4] + q[5] + -2*q[6] + 3 + 2*q[7]*q[9] + 2 + 2*q[8]*q[10] + 2 + q[7]*q[10] + -2*q[7]*q[11] + -2*q[10]*q[11] + -q[7] + -q[10] + 2*q[11] + 3 + q[9]*q[8] + -2*q[9]*q[12] + -2*q[8]*q[12] + -q[9] + -q[8] + 2*q[12] + 3 + q[11]*q[12] + -2*q[11]*q[13] + -2*q[12]*q[13] + q[11] + q[12] + -2*q[13] + 3 + 2*q[14]*q[16] + 2 + 2*q[15]*q[17] + 2 + q[14]*q[17] + -2*q[14]*q[18] + -2*q[17]*q[18] + -q[14] + -q[17] + 2*q[18] + 3 + q[16]*q[15] + -2*q[16]*q[19] + -2*q[15]*q[19] + -q[16] + -q[15] + 2*q[19] + 3 + q[18]*q[19] + -2*q[18]*q[20] + -2*q[19]*q[20] + q[18] + q[19] + -2*q[20] + 3 + 2*q[21]*q[23] + 2 + 2*q[22]*q[24] + 2 + q[21]*q[24] + -2*q[21]*q[25] + -2*q[24]*q[25] + -q[21] + -q[24] + 2*q[25] + 3 + q[23]*q[22] + -2*q[23]*q[26] + -2*q[22]*q[26] + -q[23] + -q[22] + 2*q[26] + 3 + q[25]*q[26] + -2*q[25]*q[27] + -2*q[26]*q[27] + q[25] + q[26] + -2*q[27] + 3 + 2*q[28]*q[30] + 2 + 2*q[29]*q[31] + 2 + q[28]*q[31] + -2*q[28]*q[32] + -2*q[31]*q[32] + -q[28] + -q[31] + 2*q[32] + 3 + q[30]*q[29] + -2*q[30]*q[33] + -2*q[29]*q[33] + -q[30] + -q[29] + 2*q[33] + 3 + q[32]*q[33] + -2*q[32]*q[34] + -2*q[33]*q[34] + q[32] + q[33] + -2*q[34] + 3 + 2*q[35]*q[37] + 2 + 2*q[36]*q[38] + 2 + q[35]*q[38] + -2*q[35]*q[39] + -2*q[38]*q[39] + -q[35] + -q[38] + 2*q[39] + 3 + q[37]*q[36] + -2*q[37]*q[40] + -2*q[36]*q[40] + -q[37] + -q[36] + 2*q[40] + 3 + q[39]*q[40] + -2*q[39]*q[41] + -2*q[40]*q[41] + q[39] + q[40] + -2*q[41] + 3 + 2*q[42]*q[44] + 2 + 2*q[43]*q[45] + 2 + q[42]*q[45] + -2*q[42]*q[46] + -2*q[45]*q[46] + -q[42] + -q[45] + 2*q[46] + 3 + q[44]*q[43] + -2*q[44]*q[47] + -2*q[43]*q[47] + -q[44] + -q[43] + 2*q[47] + 3 + q[46]*q[47] + -2*q[46]*q[48] + -2*q[47]*q[48] + q[46] + q[47] + -2*q[48] + 3 + 2*q[49]*q[51] + 2 + 2*q[50]*q[52] + 2 + q[49]*q[52] + -2*q[49]*q[53] + -2*q[52]*q[53] + -q[49] + -q[52] + 2*q[53] + 3 + q[51]*q[50] + -2*q[51]*q[54] + -2*q[50]*q[54] + -q[51] + -q[50] + 2*q[54] + 3 + q[53]*q[54] + -2*q[53]*q[55] + -2*q[54]*q[55] + q[53] + q[54] + -2*q[55] + 3 + 2*q[56]*q[58] + 2 + 2*q[57]*q[59] + 2 + q[56]*q[59] + -2*q[56]*q[60] + -2*q[59]*q[60] + -q[56] + -q[59] + 2*q[60] + 3 + q[58]*q[57] + -2*q[58]*q[61] + -2*q[57]*q[61] + -q[58] + -q[57] + 2*q[61] + 3 + q[60]*q[61] + -2*q[60]*q[62] + -2*q[61]*q[62] + q[60] + q[61] + -2*q[62] + 3 + 2*q[63]*q[65] + 2 + 2*q[64]*q[66] + 2 + q[63]*q[66] + -2*q[63]*q[67] + -2*q[66]*q[67] + -q[63] + -q[66] + 2*q[67] + 3 + q[65]*q[64] + -2*q[65]*q[68] + -2*q[64]*q[68] + -q[65] + -q[64] + 2*q[68] + 3 + q[67]*q[68] + -2*q[67]*q[69] + -2*q[68]*q[69] + q[67] + q[68] + -2*q[69] + 3

# ==============================================
# 公式转 Ising
# ==============================================
def formula_to_ising(f):
    exp = sp.expand(f)
    constant = 0.0
    for term in exp.as_ordered_terms():
        if term.is_constant():
            constant += float(term)
            exp -= term
            break

    h = {}
    J = {}
    for term in exp.as_ordered_terms():
        coeff = 1.0
        qs = []
        for fac in term.as_ordered_factors():
            if fac.is_number:
                coeff *= float(fac)
            else:
                idx = int(str(fac)[1:])
                qs.append(idx)
        if len(qs) == 1:
            i = qs[0]
            h[i] = h.get(i, 0.0) + coeff
        elif len(qs) == 2:
            i, j = sorted(qs)
            J[(i, j)] = J.get((i, j), 0.0) + coeff
    return h, J, constant, exp

# ==============================================
# 手动计算能量（无 lambdify，无溢出）
# ==============================================
def compute_energy(exp, sample_dict):
    if exp.is_constant():
        return float(exp)
    elif isinstance(exp, sp.Symbol):
        idx = int(str(exp)[1:])
        return sample_dict[idx]
    elif isinstance(exp, sp.Mul):
        prod = 1.0
        for fac in exp.as_ordered_factors():
            prod *= compute_energy(fac, sample_dict)
        return prod
    elif isinstance(exp, sp.Add):
        total = 0.0
        for term in exp.as_ordered_terms():
            total += compute_energy(term, sample_dict)
        return total
    else:
        return 0.0

# ==============================================
# 准备求解
# ==============================================
h, J, const, exp = formula_to_ising(f)
sampler = SimulatedAnnealingSampler()

# ==============================================
# ⏱️【核心：计时开始】只统计退火时间
# ==============================================
start_time = time.perf_counter()

response = sampler.sample_ising(
    h, J,
    num_reads=3000,
    num_sweeps=6000,
    beta_range=(0.1, 200.0),
    num_threads=8
)

# ==============================================
# ⏱️【计时结束】
# ==============================================
solve_time = time.perf_counter() - start_time

# ==============================================
# 结果
# ==============================================
best = response.first
ising_energy = best.energy
real_energy = ising_energy + const
verify_energy = compute_energy(exp, best.sample) + const

# ==============================================
# 输出
# ==============================================
print("\n==== 【带计时】Ising 求解结果 ====")
print(f"求解耗时 = {solve_time:.4f} 秒")    # <-- 你要的时间
print(f"公式真实能量 = {real_energy:.4f}")
print(f"手动验证能量 = {verify_energy:.4f}")
print(f"✅ 能量匹配: {abs(real_energy - verify_energy) < 1e-6}")