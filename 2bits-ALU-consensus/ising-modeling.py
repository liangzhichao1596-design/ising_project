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


# 1. 定义2位ALU所需的所有符号变量（核心修正：补充缺失的ALU变量）
OP, A0, A1, B0, B1, Y0, Y1 = symbols('OP A0 A1 B0 B1 Y0 Y1')

# 2. 2位ALU的CNF约束（仅与/或逻辑，替换原SRAM约束）
alu_2bit_cnf = And(
    # 低位（i=0）与激活约束
    Or(Not(OP), Not(Y0), A0),
    Or(Not(OP), Not(Y0), B0),
    Or(Not(OP), Y0, Not(A0), Not(B0)),
    # 低位（i=0）或激活约束
    Or(OP, Not(Y0), A0, B0),
    Or(OP, Y0, Not(A0)),
    Or(OP, Y0, Not(B0)),
    # 高位（i=1）与激活约束
    Or(Not(OP), Not(Y1), A1),
    Or(Not(OP), Not(Y1), B1),
    Or(Not(OP), Y1, Not(A1), Not(B1)),
    # 高位（i=1）或激活约束
    Or(OP, Not(Y1), A1, B1),
    Or(OP, Y1, Not(A1)),
    Or(OP, Y1, Not(B1))
)

# 3. 转换为伊辛模型
steps, h_func, min_e, mapping = translate_to_ising_matrix(alu_2bit_cnf)

# --- 保存到文件并打印 ---
log_filename = "2bit_ALU_Ising.log"
with open(log_filename, "w", encoding="utf-8") as f:
    def write_and_print(msg):
        print(msg)
        f.write(msg + "\n")

    write_and_print("=== 2位ALU伊辛建模报告 (2-bit ALU Ising Modeling Report) ===")
    write_and_print("\n1. 变量映射说明 (Variable Mapping):")
    for q_name, original in mapping.items():
        write_and_print(f"   {q_name} 代表: {original}")

    write_and_print("\n2. 逻辑门拆解步骤 (Gate Sequence):")
    for idx, s in enumerate(steps, 1):
        write_and_print(f"   {idx}. {s}")

    write_and_print("\n3. 最终 Ising 能量函数 (H):")
    write_and_print(f"   H = {h_func}")

    write_and_print("\n4. 系统理论最低能量 (Min Energy):")
    write_and_print(f"   {min_e}")

print(f"\n[完成] 结果已成功保存到当前路径下的: {log_filename}")