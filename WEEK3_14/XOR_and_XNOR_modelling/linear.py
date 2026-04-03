import numpy as np
from scipy.optimize import linprog
import itertools


def solve_ising_coefficients(gate_name, inputs, output_func, max_degree=3):
    """
    使用线性规划寻找 Ising 多项式系数 + 自动验证能量真值表
    :param gate_name: 门的名字
    :param inputs: 输入变量名列表
    :param output_func: 逻辑函数 (0/1输入)
    :param max_degree: 最大多项式阶数
    """
    print(f"\n{'='*60}")
    print(f"🔍 求解 [{gate_name}] Ising 哈密顿量 (最大阶数={max_degree})")
    print(f"{'='*60}")

    # 1. 定义变量：输入变量 + 输出变量x
    vars_list = inputs + ['x']
    n_vars = len(vars_list)

    # 生成所有多项式项（0阶~max_degree阶）
    terms = []
    terms_str = []
    for r in range(max_degree + 1):
        for combo in itertools.combinations(range(n_vars), r):
            terms.append(combo)
            t_str = "const" if r == 0 else "*".join([vars_list[i] for i in combo])
            terms_str.append(t_str)

    num_coeffs = len(terms)

    # 2. 构建线性规划约束
    A_eq = []  # 合法状态：能量=0
    b_eq = []
    A_ub = []  # 非法状态：能量≥2
    b_ub = []

    # 生成所有输入组合 (-1,1)
    input_combinations = list(itertools.product([-1, 1], repeat=len(inputs)))

    for inp_vals in input_combinations:
        # 转换为0/1计算逻辑输出
        bool_inputs = [1 if v == 1 else 0 for v in inp_vals]
        expected_bool = output_func(*bool_inputs)
        expected_ising = 1 if expected_bool else -1  # Ising编码：1=真，-1=假

        # 遍历x的两种状态
        for x_val in [-1, 1]:
            current_state = list(inp_vals) + [x_val]
            # 计算当前状态的多项式行向量
            row = []
            for combo in terms:
                val = 1
                for idx in combo:
                    val *= current_state[idx]
                row.append(val)

            if x_val == expected_ising:
                # 合法状态：能量=0
                A_eq.append(row)
                b_eq.append(0.0)
            else:
                # 非法状态：能量≥2 → 转换为linprog标准形式
                A_ub.append([-r for r in row])
                b_ub.append(-2.0)

    # 3. L1正则化最小化系数和（简化公式）
    c_obj = [1] * (2 * num_coeffs)

    def expand_matrix(mat):
        return np.hstack([np.array(mat), -np.array(mat)]) if mat else None

    A_eq_full = expand_matrix(A_eq)
    A_ub_full = expand_matrix(A_ub)

    # 求解线性规划
    res = linprog(c_obj, A_ub=A_ub_full, b_ub=b_ub, A_eq=A_eq_full, b_eq=b_eq, method='highs')

    if not res.success:
        print("❌ 未找到满足条件的解")
        return None

    # 提取系数
    coeffs_uv = res.x
    coeffs = coeffs_uv[:num_coeffs] - coeffs_uv[num_coeffs:]

    # 4. 格式化输出哈密顿量
    expr_parts = []
    coeff_dict = {}
    for idx, val in enumerate(coeffs):
        if abs(val) > 1e-5:
            val = round(val) if abs(val - round(val)) < 1e-5 else val
            term = terms_str[idx]
            coeff_dict[term] = val
            if term == "const":
                expr_parts.append(f"{val}")
            else:
                expr_parts.append(f"{val}*{term}" if val not in (1, -1) else
                                 (term if val == 1 else f"-{term}"))

    final_expr = " + ".join(expr_parts).replace("+ -", "- ")
    print(f"\n✅ 最终 Ising 哈密顿量：\nH = {final_expr}")
    print(f"\n📊 能量真值表验证 (逻辑正确=0，错误≥2)")

    # 5. 自动验证所有输入，输出真值表
    header = " | ".join(inputs) + " | x(正确) | 能量(正确) | x(错误) | 能量(错误)"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for inp_vals in input_combinations:
        # 计算正确输出
        bool_inp = [1 if v == 1 else 0 for v in inp_vals]
        exp_bool = output_func(*bool_inp)
        exp_x = 1 if exp_bool else -1

        # 计算正确状态能量
        state_correct = list(inp_vals) + [exp_x]
        energy_correct = 0
        for combo, val in zip(terms, coeffs):
            term_val = 1
            for idx in combo:
                term_val *= state_correct[idx]
            energy_correct += val * term_val

        # 计算错误状态能量
        state_wrong = list(inp_vals) + [-exp_x]
        energy_wrong = 0
        for combo, val in zip(terms, coeffs):
            term_val = 1
            for idx in combo:
                term_val *= state_wrong[idx]
            energy_wrong += val * term_val

        # 格式化打印
        inp_str = " | ".join([f"{v:2d}" for v in inp_vals])
        print(f"{inp_str} |    {exp_x:2d}    |    {energy_correct:.0f}     |   {-exp_x:2d}    |    {energy_wrong:.0f}")

    return final_expr


# ==========================================
# 执行求解：2输入 / 3输入 异或门、同或门
# ==========================================
if __name__ == '__main__':
    # 2输入 异或门 (XOR)：a^b
    solve_ising_coefficients("2输入 XOR", ['a', 'b'], lambda a, b: a ^ b, max_degree=3)

    # 2输入 同或门 (XNOR)：a==b
    solve_ising_coefficients("2输入 XNOR", ['a', 'b'], lambda a, b: a == b, max_degree=3)

    # 3输入 异或门 (XOR)：a^b^c
    solve_ising_coefficients("3输入 XOR", ['a', 'b', 'c'], lambda a, b, c: a ^ b ^ c, max_degree=3)

    # 3输入 同或门 (XNOR)：a==b==c
    solve_ising_coefficients("3输入 XNOR", ['a', 'b', 'c'], lambda a, b, c: a == b == c, max_degree=3)