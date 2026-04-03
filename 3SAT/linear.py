import numpy as np
from scipy.optimize import linprog
import itertools


def solve_ising_coefficients(gate_name, inputs, output_func, max_degree=3):
    """
    使用线性规划寻找 Ising 多项式系数
    :param gate_name: 门的名字 (用于打印)
    :param inputs: 输入变量名列表 ['a', 'b', 'c']
    :param output_func: 逻辑函数 (lambda a,b,c: result)
    :param max_degree: 允许的最大多项式阶数 (3 或 4)
    """
    print(f"\nSearching coefficients for [{gate_name}] (Max Degree={max_degree})...")

    # 1. 定义变量和所有可能的项
    vars_list = inputs + ['x']  # ['a', 'b', 'c', 'x']
    n_vars = len(vars_list)

    # 生成所有可能的组合项 (1, a, b, ..., ab, ..., abc, abx, ...)
    terms = []
    terms_str = []

    # 从 0阶 (常数) 到 max_degree 阶
    for r in range(max_degree + 1):
        for combo in itertools.combinations(range(n_vars), r):
            terms.append(combo)  # 存储索引元组
            # 生成便于阅读的字符串，如 "a*b*x"
            if r == 0:
                t_str = "const"
            else:
                t_str = "*".join([vars_list[i] for i in combo])
            terms_str.append(t_str)

    num_coeffs = len(terms)

    # 2. 构建约束矩阵
    # 我们有 2^3 = 8 种输入情况
    # 对于每种输入，有两种 x 状态 (-1, 1)，总共 16 个状态
    # 逻辑正确的状态 -> Energy = 0
    # 逻辑错误的状态 -> Energy >= 2.0 (Gap)

    A_eq = []  # 等式约束矩阵 (Valid states)
    b_eq = []  # 等式约束值

    A_ub = []  # 不等式约束矩阵 (Invalid states)
    b_ub = []  # 不等式约束值

    input_combinations = list(itertools.product([-1, 1], repeat=len(inputs)))

    for inp_vals in input_combinations:
        # 计算预期的正确输出 (0/1 逻辑转 -1/1)
        # 注意：Ising中通常 1是True, -1是False。或者反过来。
        # 这里假设: 1=True, -1=False.

        # 将 -1/1 转为 0/1 给 lambda 函数用
        bool_inputs = [1 if v == 1 else 0 for v in inp_vals]
        expected_bool = output_func(*bool_inputs)
        expected_ising = 1 if expected_bool else -1

        # 遍历 x 的两种可能 (-1, 1)
        for x_val in [-1, 1]:
            # 当前状态的值向量 [a, b, c, x]
            current_state_vals = list(inp_vals) + [x_val]

            # 计算这一行状态对应的多项式项的值
            # row 必须对应 coefficients 的顺序
            row = []
            for combo in terms:
                val = 1
                for idx in combo:
                    val *= current_state_vals[idx]
                row.append(val)

            if x_val == expected_ising:
                # 这是一个合法状态，能量必须为 0
                # sum(c_i * term_i) = 0
                A_eq.append(row)
                b_eq.append(0.0)
            else:
                # 这是一个非法状态，能量必须 >= 2 (Gap)
                # sum(c_i * term_i) >= 2  =>  sum(-c_i * term_i) <= -2
                row_neg = [-1 * r for r in row]
                A_ub.append(row_neg)
                b_ub.append(-2.0)

    # 3. 求解线性规划
    # 目标：最小化系数的绝对值之和 (L1 正则化)，让公式尽量简单
    # 为了用 linprog 处理绝对值，我们需要把每个系数 c 分解为 u - v (u,v >= 0)
    # 变量数翻倍: [u0, ..., uN, v0, ..., vN]
    # c_i = u_i - v_i

    c_obj = [1] * (2 * num_coeffs)  # 目标函数系数 (全1，即最小化 sum(u+v))

    # 扩展约束矩阵以适应 u, v
    def expand_matrix(Mat):
        if not Mat: return None
        Mat_np = np.array(Mat)
        return np.hstack([Mat_np, -Mat_np])

    A_eq_full = expand_matrix(A_eq)
    A_ub_full = expand_matrix(A_ub)

    res = linprog(c_obj, A_ub=A_ub_full, b_ub=b_ub, A_eq=A_eq_full, b_eq=b_eq, method='highs')

    if res.success:
        print("✅ Found a valid Hamiltonian!")
        coeffs_uv = res.x
        coeffs = coeffs_uv[:num_coeffs] - coeffs_uv[num_coeffs:]

        # 格式化输出 Python 表达式
        expr_parts = []

        # 过滤掉接近 0 的项
        final_formula = []

        print("\n--- Model Coefficients ---")
        for idx, val in enumerate(coeffs):
            if abs(val) > 1e-5:
                # 尝试取整，为了好看
                if abs(val - round(val)) < 1e-5:
                    val = int(round(val))

                term_name = terms_str[idx]
                print(f"{term_name:>10}: {val}")

                if term_name == "const":
                    if val != 0: expr_parts.append(f"{val}")
                else:
                    # 格式化为 a*b*c
                    # 如果系数是 1, 省略系数; -1, 写 -
                    if val == 1:
                        expr_parts.append(f"{term_name}")
                    elif val == -1:
                        expr_parts.append(f"-{term_name}")
                    else:
                        expr_parts.append(f"{val}*{term_name}")

        final_str = " + ".join(expr_parts).replace("+ -", "- ")
        print(f"\n[Python Expression]:\nreturn \"{final_str}\", 0")
        return final_str
    else:
        print("❌ No solution found with current constraints.")
        print("   Consider allowing higher degree terms or auxiliary variables.")
        return None


# ==========================================
# 运行生成器
# ==========================================

print("=== 尝试生成 3-Input AND (无辅助变量) ===")
# 逻辑: a and b and c
solve_ising_coefficients("AND3", ['a', 'b', 'c'], lambda a, b, c: a and b and c, max_degree=3)

print("\n\n=== 尝试生成 3-Input OR (无辅助变量) ===")
# 逻辑: a or b or c
solve_ising_coefficients("OR3", ['a', 'b', 'c'], lambda a, b, c: a or b or c, max_degree=3)