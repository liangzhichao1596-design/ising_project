import re
import pandas as pd


class IsingSystem:
    def __init__(self):
        self.q_count = 0
        self.var_map = {}  # q[i] -> 描述 (完整表)

        # 存储列表
        self.cubic_terms_list = []  # 存储带系数的三次项 (用于列表输出给Solver)
        self.cubic_terms_full = []  # 存储带符号/系数的三次项 (用于构建总函数字符串)
        self.quad_terms_list = []  # 存储二次及线性项字符串

        self.min_energy = 0  # 理论最小能量偏移

        # 专门存储关键端口，用于干净的打印
        self.key_inputs = {}
        self.key_outputs = {}

    def get_q(self, desc):
        """分配量子比特"""
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    # ==========================================
    # 1. 映射引擎：严格按照 Ising 公式建模 (基态为0)
    # ==========================================
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        if gate_type == "NOT":
            a = inputs[0]
            x = out_var
            return f"(2 * {a} * {x} + 2)", 0

        if len(inputs) == 2:
            a, b = inputs
            x = out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x} + 3)", 0
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x} + 3)", 0
            elif gate_type == "XOR":
                return f"({a}*{b}*{x} + 1)", 0
            elif gate_type == "XNOR":
                return f"(-{a}*{b}*{x} + 1)", 0
            elif gate_type == "NAND":
                return f"(1 - 0.5*{x} + 0.5*{a}*{x} + 0.5*{b}*{x} + 0.5*{a}*{b}*{x})", 0
            elif gate_type == "NOR":
                return f"(1 + 0.5*{x} + 0.5*{a}*{x} + 0.5*{b}*{x} - 0.5*{a}*{b}*{x})", 0

        elif len(inputs) == 3:
            a, b, c = inputs
            x = out_var
            if gate_type == "AND":
                return (f"(5 - {a} + 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} + {a}*{b}*{c} "
                        f"- {a}*{b}*{x} - {a}*{c}*{x} - 2*{b}*{c}*{x})"), 0
            elif gate_type == "OR":
                return (f"(5 + {a} - 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} - {a}*{b}*{c} "
                        f"+ {a}*{b}*{x} + {a}*{c}*{x} + 2*{b}*{c}*{x})"), 0
        return "0", 0

    def add_gate(self, gate_type, inputs, desc):
        out_q = self.get_q(desc)
        expr_str, offset = self.get_higher_order_ising_contribution(gate_type, out_q, inputs)
        self.min_energy += offset

        clean_expr = expr_str.replace("(", "").replace(")", "")
        terms = re.split(r'(?=[+-])', clean_expr.replace(" ", ""))

        for term in terms:
            term = term.strip()
            if not term:
                continue

            clean_term_str = term
            if term.startswith('+'):
                clean_term_str = term[1:]

            vars_in_term = re.findall(r"q\[\d+\]", term)
            if len(vars_in_term) == 3:
                self.cubic_terms_full.append(clean_term_str)
                self.cubic_terms_list.append(clean_term_str)
            else:
                self.quad_terms_list.append(clean_term_str)

        return out_q

    # ==========================================
    # 2. 复合逻辑门
    # ==========================================
    def XOR(self, a, b, internal_name):
        return self.add_gate("XOR", [a, b], internal_name)

    def XOR_composite_AON(self, a, b, internal_name):
        not_a = self.add_gate("NOT", [a], f"{internal_name}_notA")
        not_b = self.add_gate("NOT", [b], f"{internal_name}_notB")
        and1 = self.add_gate("AND", [a, not_b], f"{internal_name}_and1")
        and2 = self.add_gate("AND", [not_a, b], f"{internal_name}_and2")
        out = self.add_gate("OR", [and1, and2], f"{internal_name}_out")
        return out

    def XOR_composite_NAND(self, a, b, internal_name):
        nand_ab = self.add_gate("NAND", [a, b], f"{internal_name}_nand1_ab")
        nand_a = self.add_gate("NAND", [a, nand_ab], f"{internal_name}_nand2_a")
        nand_b = self.add_gate("NAND", [b, nand_ab], f"{internal_name}_nand3_b")
        out = self.add_gate("NAND", [nand_a, nand_b], f"{internal_name}_out")
        return out

    def register_input(self, q, name):
        self.key_inputs[q] = name
        self.var_map[q] = f"[INPUT] {name}"

    def register_output(self, q, name):
        self.key_outputs[q] = name
        self.var_map[q] = f"[OUTPUT] {name}"


# ==========================================
# 3. 电路构建
# ==========================================
def build_system(a_percent, comp_mode="AON"):
    gen = IsingSystem()
    TOTAL_GATES = 100
    composite_count = int(TOTAL_GATES * a_percent / 100)

    for i in range(TOTAL_GATES):
        qa = gen.get_q(f"Raw_A{i}")
        qb = gen.get_q(f"Raw_B{i}")
        gen.register_input(qa, f"A[{i}]")
        gen.register_input(qb, f"B[{i}]")

        if i < composite_count:
            if comp_mode == "NAND":
                out = gen.XOR_composite_NAND(qa, qb, f"Comp_XOR_{i}")
            else:
                out = gen.XOR_composite_AON(qa, qb, f"Comp_XOR_{i}")
        else:
            out = gen.XOR(qa, qb, f"Native_XOR_{i}")

        gen.register_output(out, f"OUT[{i}]")

    return gen


# ==========================================
# 4. 生成规范的格式化报告
# ==========================================
def export_log(model, a_percent, mode_name, filename):
    """严格按照用户提供的样本格式生成 .log 文件"""

    # 构建函数字符串
    f_quad_str = " + ".join(model.quad_terms_list)
    f_total_str = f_quad_str
    if model.cubic_terms_full:
        f_total_str += " + " + " + ".join(model.cubic_terms_full)

    log_lines = []

    # Header
    log_lines.append("=" * 80)
    # 增加模式标识以免混淆，但整体结构保持一致
    log_lines.append(f" ISING MODEL GENERATION REPORT (100 XOR Gates, a={a_percent}%, {mode_name} Mode)")
    log_lines.append("=" * 80)
    log_lines.append(f"Total Qubits: {model.q_count}")
    log_lines.append(f"Theoretical Min Energy (Offset): {model.min_energy}")
    log_lines.append("-" * 80)

    # 1. CUBIC TERMS
    log_lines.append("\n[1. CUBIC TERMS LIST (With Coefficients)]")
    log_lines.append("cubic_terms_list = [")
    for i, t in enumerate(model.cubic_terms_list):
        comma = "," if i < len(model.cubic_terms_list) - 1 else ""
        log_lines.append(f"    '{t}'{comma}")
    log_lines.append("]")

    # 2. F_QUADRATIC
    log_lines.append("\n" + "-" * 80)
    log_lines.append("[2. F_QUADRATIC (Linear + Quadratic terms only)]")
    log_lines.append(f_quad_str)

    # 3. F_TOTAL
    log_lines.append("\n" + "-" * 80)
    log_lines.append("[3. F_TOTAL (Full Hamiltonian including Cubic)]")
    log_lines.append(f_total_str)

    # 4. MAPPING
    log_lines.append("\n" + "-" * 80)
    log_lines.append("[4. FULL VARIABLE MAPPING]")
    log_lines.append(f"{'Index':<10} | Description")
    log_lines.append("-" * 50)

    # 确保按数值大小（如 q[2], q[10]）排序而不是按字符串字典序排
    sorted_map = sorted(model.var_map.items(), key=lambda x: int(re.search(r'\d+', x[0]).group()))
    for k, v in sorted_map:
        log_lines.append(f"{k:<10} : {v}")

    # Footer
    log_lines.append("\n" + "=" * 80)
    log_lines.append(" END OF REPORT")
    log_lines.append("=" * 80)

    # 写入文件
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))


# ==========================================
# 5. 批量生成与执行入口
# ==========================================
def generate_reports_and_excel():
    summary_data = []

    for a in range(0, 101, 10):
        # 分别运行两种模式以进行对比
        model_aon = build_system(a, comp_mode="AON")
        model_nand = build_system(a, comp_mode="NAND")

        # 生成两种模式对应的严格格式 Log 文件
        export_log(model_aon, a, "AON", f"Ising_Report_a{a}_AON.log")
        export_log(model_nand, a, "NAND", f"Ising_Report_a{a}_NAND.log")

        print(f"a={a:^3}% | [与或非] 总 Qubits: {model_aon.q_count:<4} | [NAND] 总 Qubits: {model_nand.q_count}")

        # 收集数据到 Excel 表格
        summary_data.append({
            "a (%)": a,
            "Native XOR Count": 100 - a,
            "Composite XOR Count": a,
            "Total Qubits (与或非方案)": model_aon.q_count,
            "Total Qubits (NAND方案)": model_nand.q_count,
            "三次项数量 (与或非方案)": len(model_aon.cubic_terms_list),
            "三次项数量 (NAND方案)": len(model_nand.cubic_terms_list),
        })

    # 导出 Excel
    excel_filename = "Qubit_Comparison_Ising_Report.xlsx"
    df = pd.DataFrame(summary_data)
    df.to_excel(excel_filename, index=False)
    print(f"\n全部生成完毕！Excel 对比表已保存至: {excel_filename}")


if __name__ == "__main__":
    generate_reports_and_excel()