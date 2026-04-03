import sympy
from sympy import symbols, Not, And, Or


# 复用你之前的工具函数 (get_ising_contribution)
def get_ising_contribution(gate_type, out_var, in1, in2=None):
    a, b, x = in1, in2, out_var
    if gate_type == "AND":
        return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
    elif gate_type == "OR":
        return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3
    elif gate_type == "NOT":
        return f"(2 * {a} * {x})", -2


# 稍微修改原函数，使其支持重置 qubits 索引
def translate_to_ising_matrix_modular(expr, start_q_idx=0):
    steps = []
    total_energy_terms = []
    min_energy = 0

    # 提取变量
    raw_vars = sorted(list(expr.free_symbols), key=lambda x: str(x))
    # 建立映射: 这里的关键是，我们可以控制 q 的起始，通常每个 Agent 都从 q[0] 开始
    var_to_q = {str(v): f"q[{i}]" for i, v in enumerate(raw_vars)}
    q_to_var = {f"q[{i}]": str(v) for i, v in enumerate(raw_vars)}
    next_q_idx = len(raw_vars)

    def process(e):
        nonlocal min_energy, next_q_idx
        if isinstance(e, sympy.Symbol):
            return var_to_q[str(e)]

        # 逻辑门处理
        if isinstance(e, Not):
            child_q = process(e.args[0])
            out_q = f"q[{next_q_idx}]"
            q_to_var[out_q] = f"Ancilla (NOT {child_q})"
            next_q_idx += 1
            term, energy = get_ising_contribution("NOT", out_q, child_q)
            total_energy_terms.append(term)
            min_energy += energy
            steps.append(f"{out_q} = NOT {child_q}")
            return out_q

        if isinstance(e, (And, Or)):
            gate_name = "AND" if isinstance(e, And) else "OR"
            args = list(e.args)
            left_q = process(args[0])
            for i in range(1, len(args)):
                right_q = process(args[i])
                out_q = f"q[{next_q_idx}]"
                q_to_var[out_q] = f"Ancilla ({left_q} {gate_name} {right_q})"
                next_q_idx += 1
                term, energy = get_ising_contribution(gate_name, out_q, left_q, right_q)
                total_energy_terms.append(term)
                min_energy += energy
                steps.append(f"{out_q} = {left_q} {gate_name} {right_q}")
                left_q = out_q
            return left_q

    process(expr)
    final_h = " + ".join(total_energy_terms)
    return final_h, q_to_var, next_q_idx  # 返回 next_q_idx 代表占用比特总数


# --- 1. 定义变量 ---
OP, A0, A1, B0, B1, Y0, Y1 = symbols('OP A0 A1 B0 B1 Y0 Y1')

# --- 2. 拆分约束 ---
# Agent 1 只看 Bit 0
cnf_bit0 = And(
    Or(Not(OP), Not(Y0), A0), Or(Not(OP), Not(Y0), B0), Or(Not(OP), Y0, Not(A0), Not(B0)),  # AND
    Or(OP, Not(Y0), A0, B0), Or(OP, Y0, Not(A0)), Or(OP, Y0, Not(B0))  # OR
)

# Agent 2 只看 Bit 1
cnf_bit1 = And(
    Or(Not(OP), Not(Y1), A1), Or(Not(OP), Not(Y1), B1), Or(Not(OP), Y1, Not(A1), Not(B1)),
    Or(OP, Not(Y1), A1, B1), Or(OP, Y1, Not(A1)), Or(OP, Y1, Not(B1))
)

# --- 3. 分别生成模型 ---
print("=== ADMM 拆分优化报告 ===")

# 生成 Agent 1 模型
h0, map0, count0 = translate_to_ising_matrix_modular(cnf_bit0)
print(f"\n[Agent 1 - Bit 0]")
print(f"占用物理比特数: {count0}")
print(f"变量映射: {map0}")
print(f"局部哈密顿量: {h0[:100]}...")  # 只打印前100字符

# 生成 Agent 2 模型
h1, map1, count1 = translate_to_ising_matrix_modular(cnf_bit1)
print(f"\n[Agent 2 - Bit 1]")
print(f"占用物理比特数: {count1}")
print(f"变量映射: {map1}")
print(f"局部哈密顿量: {h1[:100]}...")

print(f"\n[对比] 原方案预计占用比特数: >{count0 + count1}")
print(f"[结论] 使用 ADMM 分时复用，只需要 {max(count0, count1)} 个量子比特的芯片即可运行！")