import re
import os
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
    # 1. 映射引擎：已加入 XOR / XNOR 标准三次项 Ising 表达式
    # ==========================================
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        # 非门映射
        if gate_type == "NOT":
            a = inputs[0]
            x = out_var
            return f"(2 * {a} * {x} + 2)", 0

        # 2输入门映射：新增 XOR / XNOR
        if len(inputs) == 2:
            a, b = inputs
            x = out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x} + 3)", 0
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x} + 3)", 0
            elif gate_type == "XOR":  # 2输入异或门
                return f"({a}*{b}*{x} + 1)", 0
            elif gate_type == "XNOR":  # 2输入同或门
                return f"(-{a}*{b}*{x} + 1)", 0

        elif len(inputs) == 3:
            a, b, c = inputs
            x = out_var

            if gate_type == "AND":
                # 3输入 AND 门 (整系数版, Max Degree=3, 无辅助变量)
                return (f"(5 - {a} + 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} + {a}*{b}*{c} "
                        f"- {a}*{b}*{x} - {a}*{c}*{x} - 2*{b}*{c}*{x})"), 0

            elif gate_type == "OR":
                # 3输入 OR 门 (整系数版, Max Degree=3, 无辅助变量)
                return (f"(5 + {a} - 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} - {a}*{b}*{c} "
                        f"+ {a}*{b}*{x} + {a}*{c}*{x} + 2*{b}*{c}*{x})"), 0
        return "0", 0

    def add_gate(self, gate_type, inputs, desc):
        out_q = self.get_q(desc)

        expr_str, offset = self.get_higher_order_ising_contribution(gate_type, out_q, inputs)
        self.min_energy += offset

        # --- 字符串解析器 ---
        # 1. 去除括号
        clean_expr = expr_str.replace("(", "").replace(")", "")

        # 2. 按加减号分割项 (保留符号)
        terms = re.split(r'(?=[+-])', clean_expr.replace(" ", ""))

        for term in terms:
            term = term.strip()
            if not term:
                continue

            clean_term_str = term
            if term.startswith('+'):
                clean_term_str = term[1:]

            # 判断是否为三次项 (含有3个q)
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
        """直接使用标准2输入XOR Ising模型"""
        return self.add_gate("XOR", [a, b], internal_name)

    def XOR_composite(self, a, b, internal_name):
        """使用 与或非 三门组合建模异或门: A XOR B = (A AND NOT B) OR (NOT A AND B)"""
        not_a = self.add_gate("NOT", [a], f"{internal_name}_notA")
        not_b = self.add_gate("NOT", [b], f"{internal_name}_notB")
        and1 = self.add_gate("AND", [a, not_b], f"{internal_name}_and1")
        and2 = self.add_gate("AND", [not_a, b], f"{internal_name}_and2")
        out = self.add_gate("OR", [and1, and2], f"{internal_name}_out")
        return out

    # --- 端口注册辅助函数 ---
    def register_input(self, q, name):
        self.key_inputs[q] = name
        self.var_map[q] = f"[INPUT] {name}"

    def register_output(self, q, name):
        self.key_outputs[q] = name
        self.var_map[q] = f"[OUTPUT] {name}"


# ==========================================
# 3. 构建 100个异或门 电路
# ==========================================
def build_system(a_percent):
    gen = IsingSystem()
    TOTAL_GATES = 100

    # 计算需要使用组合门建模的数量
    composite_count = int(TOTAL_GATES * a_percent / 100)

    for i in range(TOTAL_GATES):
        # 注册输入
        qa = gen.get_q(f"Raw_A{i}")
        qb = gen.get_q(f"Raw_B{i}")
        gen.register_input(qa, f"A[{i}]")
        gen.register_input(qb, f"B[{i}]")

        # 按照比例分配建模方式
        if i < composite_count:
            # 前 a% 使用 与或非 组合门建模
            out = gen.XOR_composite(qa, qb, f"Comp_XOR_{i}")
        else:
            # 剩余的直接使用原生 XOR 建模
            out = gen.XOR(qa, qb, f"Native_XOR_{i}")

        # 注册输出
        gen.register_output(out, f"OUT[{i}]")

    return gen


# ==========================================
# 4. 批量生成报告与 Excel
# ==========================================
def generate_reports_and_excel():
    summary_data = []

    # a 从 0 到 100，步长为 10
    for a in range(0, 101, 10):
        model = build_system(a)

        # 构建函数字符串
        f_quad_str = " + ".join(model.quad_terms_list)
        f_total_str = f"{f_quad_str} + {' + '.join(model.cubic_terms_full)}"

        # 准备日志内容
        log_lines = []
        log_lines.append("=" * 80)
        log_lines.append(f" ISING MODEL GENERATION REPORT (100 XOR Gates, a={a}%)")
        log_lines.append("=" * 80)
        log_lines.append(f"Total Qubits: {model.q_count}")
        log_lines.append(f"Theoretical Min Energy (Offset): {model.min_energy}")
        log_lines.append("-" * 80)

        log_lines.append("\n[1. CUBIC TERMS LIST (With Coefficients)]")
        log_lines.append("cubic_terms_list = [")
        for i, t in enumerate(model.cubic_terms_list):
            comma = "," if i < len(model.cubic_terms_list) - 1 else ""
            log_lines.append(f"    '{t}'{comma}")
        log_lines.append("]")

        log_lines.append("\n" + "-" * 80)
        log_lines.append("[2. F_QUADRATIC (Linear + Quadratic terms only)]")
        log_lines.append(f_quad_str)

        log_lines.append("\n" + "-" * 80)
        log_lines.append("[3. F_TOTAL (Full Hamiltonian including Cubic)]")
        log_lines.append(f_total_str)

        log_lines.append("\n" + "-" * 80)
        log_lines.append("[4. FULL VARIABLE MAPPING]")
        log_lines.append(f"{'Index':<10} | {'Description'}")
        log_lines.append("-" * 50)
        # 按索引排序输出
        sorted_map = sorted(model.var_map.items(), key=lambda x: int(x[0].split('[')[1].split(']')[0]))
        for k, v in sorted_map:
            log_lines.append(f"{k:<10} : {v}")

        log_lines.append("\n" + "=" * 80)
        log_lines.append(" END OF REPORT")
        log_lines.append("=" * 80)

        # 写入单独的 log 文件
        filename = f"Full_Ising_Report_a{a}.log"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

        print(f"成功生成模型! a={a:^3}% | 总量子比特数: {model.q_count:^4} | 日志文件: {filename}")

        # 收集数据用于生成 Excel
        summary_data.append({
            "a (%)": a,
            "Native XOR Count": 100 - a,
            "Composite XOR Count": a,
            "Total Qubits": model.q_count,
            "Cubic Terms Count": len(model.cubic_terms_list),
            "Min Energy Offset": model.min_energy
        })

    # 生成 Excel 文件
    excel_filename = "Qubit_Counts_Report.xlsx"
    df = pd.DataFrame(summary_data)
    df.to_excel(excel_filename, index=False)
    print(f"\n所有迭代完成！摘要数据已写入: {excel_filename}")


if __name__ == "__main__":
    generate_reports_and_excel()