import sympy
from sympy import symbols, Not, And, Or
import os


def get_ising_contribution(gate_type, out_var, in1, in2=None):
    """
    根据门类型返回对应的 Ising 能量项
    """
    a, b, x = in1, in2, out_var
    if gate_type == "AND":
        # H = ab - 2ax - 2bx - a - b + 2x, Min = -3
        return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
    elif gate_type == "OR":
        # H = ab - 2ax - 2bx + a + b - 2x, Min = -3
        return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3
    elif gate_type == "NOT":
        # H = 2ax, Min = -2
        return f"(2 * {a} * {x})", -2


def translate_to_ising_matrix(expr):
    """
    递归拆解表达式，生成基于 q[i] 的 Ising 函数并记录日志
    """
    steps = []
    total_energy_terms = []
    min_energy = 0

    # 提取并排序所有原始变量
    raw_vars = sorted(list(expr.free_symbols), key=lambda x: str(x))
    # 建立变量映射表 q[0], q[1]...
    var_to_q = {str(v): f"q[{i}]" for i, v in enumerate(raw_vars)}
    q_to_var = {f"q[{i}]": str(v) for i, v in enumerate(raw_vars)}
    next_q_idx = len(raw_vars)

    def process(e):
        nonlocal min_energy, next_q_idx

        # 处理基本变量 (转为 q[i])
        if isinstance(e, sympy.Symbol):
            return var_to_q[str(e)]

        # 处理 NOT
        if isinstance(e, Not):
            child_q = process(e.args[0])
            out_q = f"q[{next_q_idx}]"
            q_to_var[out_q] = f"Ancilla (NOT {child_q})"
            next_q_idx += 1
            term, energy = get_ising_contribution("NOT", out_q, child_q)
            total_energy_terms.append(term)
            min_energy += energy
            steps.append(f"Gate: {out_q} = NOT {child_q}")
            return out_q

        # 处理 AND / OR
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
                steps.append(f"Gate: {out_q} = {left_q} {gate_name} {right_q}")
                left_q = out_q
            return left_q

    # 执行拆解逻辑
    process(expr)
    final_h = " + ".join(total_energy_terms)

    return steps, final_h, min_energy, q_to_var


# 1. 定义所有符号变量
CLK_t, CLK_t_1, R_CLK = symbols('CLK_t CLK_t_1 R_CLK')
WE, RE, WE_valid, RE_valid = symbols('WE RE WE_valid RE_valid')
D_in, Q_t, Q_t_1, D_out = symbols('D_in Q_t Q_t_1 D_out')

# 2. 同步SRAM的CNF约束（按约束类型拆分）
sram_cnf_constraints = And(
    # ---------------- 时钟边沿检测约束 ----------------
    # R_CLK ↔ (CLK_t ∧ ¬CLK_t_1)
    Or(Not(R_CLK), CLK_t),
    Or(Not(R_CLK), Not(CLK_t_1)),
    Or(R_CLK, Not(CLK_t), CLK_t_1),

    # ---------------- 有效写边沿触发约束 ----------------
    # WE_valid ↔ (WE ∧ R_CLK)
    Or(Not(WE_valid), WE),
    Or(Not(WE_valid), R_CLK),
    Or(WE_valid, Not(WE), Not(R_CLK)),

    # ---------------- 有效读边沿触发约束 ----------------
    # RE_valid ↔ (RE ∧ R_CLK)
    Or(Not(RE_valid), RE),
    Or(Not(RE_valid), R_CLK),
    Or(RE_valid, Not(RE), Not(R_CLK)),

    # ---------------- 读写时序互斥约束 ----------------
    Or(Not(WE_valid), Not(RE_valid)),

    # ---------------- 写功能约束 ----------------
    # WE_valid → (Q_t = D_in)
    Or(Not(WE_valid), Not(Q_t), D_in),
    Or(Not(WE_valid), Q_t, Not(D_in)),

    # ---------------- 读功能约束 ----------------
    # RE_valid → (D_out = Q_t)
    Or(Not(RE_valid), Not(D_out), Q_t),
    Or(Not(RE_valid), D_out, Not(Q_t)),

    # ---------------- 存储值保持约束 ----------------
    # ¬WE_valid ∧ ¬RE_valid → (Q_t = Q_t_1)
    Or(WE_valid, RE_valid, Not(Q_t), Q_t_1),
    Or(WE_valid, RE_valid, Q_t, Not(Q_t_1))
)

steps, h_func, min_e, mapping = translate_to_ising_matrix(sram_cnf_constraints)

# --- 保存到文件并打印 ---
log_filename = "SRAM_CLK.log"
with open(log_filename, "w", encoding="utf-8") as f:
    def write_and_print(msg):
        print(msg)
        f.write(msg + "\n")


    write_and_print("=== 伊辛建模报告 (Ising Modeling Report) ===")
    write_and_print("\n1. 变量映射说明 (Variable Mapping):")
    for q_name, original in mapping.items():
        write_and_print(f"   {q_name} 代表: {original}")

    write_and_print("\n2. 逻辑门拆解步骤 (Gate Sequence):")
    for s in steps:
        write_and_print(f"   {s}")

    write_and_print("\n3. 最终 Ising 能量函数 (H):")
    write_and_print(f"   H = {h_func}")

    write_and_print("\n4. 系统理论最低能量 (Min Energy):")
    write_and_print(f"   {min_e}")

print(f"\n[完成] 结果已成功保存到当前路径下的: {log_filename}")