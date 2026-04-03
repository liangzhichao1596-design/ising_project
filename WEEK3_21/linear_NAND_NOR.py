import re
import os
import random
import matplotlib.pyplot as plt


class IsingSystem:
    def __init__(self, ratio_direct=1.0):
        self.q_count = 0
        self.var_map = {}  # q[i] -> 描述 (完整表)

        # 存储列表
        self.cubic_terms_list = []
        self.cubic_terms_full = []
        self.quad_terms_list = []

        self.min_energy = 0
        self.key_inputs = {}
        self.key_outputs = {}

        # 核心参数：原生 XOR/XNOR 门所占的比例
        self.ratio_direct = ratio_direct

        # 统计实际使用的门数量
        self.count_direct = 0
        self.count_composite = 0

    def get_q(self, desc):
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    # ==========================================
    # 1. 映射引擎 (原封不动保留你的公式)
    # ==========================================
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        if gate_type == "NOT":
            a = inputs[0]
            x = out_var
            return f"(2 * {a} * {x})", -2

        if len(inputs) == 2:
            a, b = inputs
            x = out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3
            elif gate_type == "XOR":
                return f"(-{a}*{b} - {a}*{x} - {b}*{x} + 1)", 0
            elif gate_type == "XNOR":
                return f"({a}*{b} + {a}*{x} + {b}*{x} - 1)", 0
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
            elif gate_type == "NAND":
                return (f"(1.25 - 0.25*{a} - {x} + 0.5*{a}*{x} - 0.25*{b}*{c} "
                        f"+ 0.25*{b}*{x} + 0.25*{c}*{x} + 0.25*{a}*{b}*{c} "
                        f"+ 0.25*{a}*{b}*{x} + 0.25*{a}*{c}*{x} + 0.5*{b}*{c}*{x})"), 0
            elif gate_type == "NOR":
                return (f"(1.25 + 0.25*{c} + {x} - 0.25*{a}*{b} + 0.25*{a}*{x} "
                        f"+ 0.25*{b}*{x} + 0.5*{c}*{x} - 0.25*{a}*{b}*{c} "
                        f"- 0.5*{a}*{b}*{x} - 0.25*{a}*{c}*{x} - 0.25*{b}*{c}*{x})"), 0
        return "0", 0

    def add_gate(self, gate_type, inputs, desc):
        out_q = self.get_q(desc)
        expr_str, offset = self.get_higher_order_ising_contribution(gate_type, out_q, inputs)
        self.min_energy += offset

        clean_expr = expr_str.replace("(", "").replace(")", "")
        terms = re.split(r'(?=[+-])', clean_expr.replace(" ", ""))

        for term in terms:
            term = term.strip()
            if not term: continue
            clean_term_str = term if not term.startswith('+') else term[1:]
            vars_in_term = re.findall(r"q\[\d+\]", term)

            if len(vars_in_term) == 3:
                self.cubic_terms_full.append(clean_term_str)
                self.cubic_terms_list.append(clean_term_str)
            else:
                self.quad_terms_list.append(clean_term_str)

        return out_q

    # ==========================================
    # 2. 核心拦截：动态混合门控逻辑
    # ==========================================
    def XOR(self, a, b, internal_name):
        """随机决定使用原生 XOR 还是 与或非组合 XOR"""
        if random.random() <= self.ratio_direct:
            # 命中比例：使用原生 XOR 门（直接映射，只需 1 个 qubit）
            self.count_direct += 1
            return self.add_gate("XOR", [a, b], internal_name)
        else:
            # 未命中：降维使用组合门 XOR = (A OR B) AND (NOT(A AND B))
            self.count_composite += 1
            or_res = self.add_gate("OR", [a, b], f"Aux_CompXOR_OR_{internal_name}")
            and_res = self.add_gate("AND", [a, b], f"Aux_CompXOR_AND_{internal_name}")
            nand_res = self.add_gate("NOT", [and_res], f"Aux_CompXOR_NOT_{internal_name}")
            return self.add_gate("AND", [or_res, nand_res], internal_name)

    def XNOR(self, a, b, internal_name):
        """随机决定使用原生 XNOR 还是 与或非组合 XNOR"""
        if random.random() <= self.ratio_direct:
            self.count_direct += 1
            return self.add_gate("XNOR", [a, b], internal_name)
        else:
            # 组合 XNOR = NOT (XOR)
            self.count_composite += 1
            or_res = self.add_gate("OR", [a, b], f"Aux_CompXNOR_OR_{internal_name}")
            and_res = self.add_gate("AND", [a, b], f"Aux_CompXNOR_AND_{internal_name}")
            nand_res = self.add_gate("NOT", [and_res], f"Aux_CompXNOR_NOT_{internal_name}")
            xor_res = self.add_gate("AND", [or_res, nand_res], f"Aux_CompXNOR_XOR_{internal_name}")
            return self.add_gate("NOT", [xor_res], internal_name)

    def NAND(self, a, b, internal_name):
        return self.add_gate("NAND", [a, b], internal_name)

    def NOR(self, a, b, internal_name):
        return self.add_gate("NOR", [a, b], internal_name)

    def OR_Tree(self, bits, name):
        current = bits
        layer = 0
        while len(current) > 1:
            next_layer = []
            i = 0
            while i < len(current):
                rem = len(current) - i
                if rem >= 3:
                    res = self.add_gate("OR", [current[i], current[i + 1], current[i + 2]], f"Tree_{name}_L{layer}_OR3")
                    next_layer.append(res)
                    i += 3
                elif rem == 2:
                    res = self.add_gate("OR", [current[i], current[i + 1]], f"Tree_{name}_L{layer}_OR2")
                    next_layer.append(res)
                    i += 2
                else:
                    next_layer.append(current[i])
                    i += 1
            current = next_layer
            layer += 1
        return current[0]

    def register_input(self, q, name):
        self.key_inputs[q] = name
        self.var_map[q] = f"[INPUT] {name}"

    def register_output(self, q, name):
        self.key_outputs[q] = name
        self.var_map[q] = f"[OUTPUT] {name}"


# ==========================================
# 3. 电路构建
# ==========================================
def build_system(ratio_direct):
    """根据指定的原生门比例构建系统"""
    gen = IsingSystem(ratio_direct=ratio_direct)
    BIT_WIDTH = 4

    A = [gen.get_q(f"Raw_A{i}") for i in range(BIT_WIDTH)]
    B = [gen.get_q(f"Raw_B{i}") for i in range(BIT_WIDTH)]
    Cin = gen.get_q("Raw_Cin")
    gen.register_input(Cin, "Cin")
    for i in range(BIT_WIDTH):
        gen.register_input(A[i], f"A[{i}]")
        gen.register_input(B[i], f"B[{i}]")

    # --- RCA ---
    S_RCA = []
    c_curr = Cin
    for i in range(BIT_WIDTH):
        t1 = gen.XOR(A[i], B[i], f"RCA_b{i}_step1")
        s = gen.XOR(t1, c_curr, f"RCA_b{i}_step2")
        gen.register_output(s, f"S_RCA[{i}]")
        S_RCA.append(s)

        ab = gen.add_gate("AND", [A[i], B[i]], f"RCA_Cry_AB_{i}")
        ac = gen.add_gate("AND", [A[i], c_curr], f"RCA_Cry_AC_{i}")
        bc = gen.add_gate("AND", [B[i], c_curr], f"RCA_Cry_BC_{i}")
        c_curr = gen.add_gate("OR", [ab, ac, bc], f"C_RCA_Int_{i}")

    C_RCA = c_curr
    gen.register_output(C_RCA, "Cout_RCA")

    # --- CLA ---
    G = [gen.add_gate("AND", [A[i], B[i]], f"CLA_G_{i}") for i in range(BIT_WIDTH)]
    P = [gen.XOR(A[i], B[i], f"CLA_P_{i}") for i in range(BIT_WIDTH)]

    C_CLA_Chain = [Cin]
    for i in range(BIT_WIDTH):
        pc = gen.add_gate("AND", [P[i], C_CLA_Chain[-1]], f"CLA_PC_{i}")
        c_next = gen.add_gate("OR", [G[i], pc], f"C_CLA_{i + 1}")
        C_CLA_Chain.append(c_next)

    S_CLA = []
    for i in range(BIT_WIDTH):
        s = gen.XOR(P[i], C_CLA_Chain[i], f"CLA_Sum_{i}")
        gen.register_output(s, f"S_CLA[{i}]")
        S_CLA.append(s)
    C_CLA = C_CLA_Chain[-1]
    gen.register_output(C_CLA, "Cout_CLA")

    # --- Miter ---
    diffs = []
    for i in range(BIT_WIDTH):
        diffs.append(gen.XOR(S_RCA[i], S_CLA[i], f"Diff_Sum_{i}"))
    diffs.append(gen.XOR(C_RCA, C_CLA, "Diff_Cout"))

    final_diff = gen.OR_Tree(diffs, "FinalDiff")
    gen.quad_terms_list.append(f"1")
    gen.quad_terms_list.append(f"-{final_diff}")

    return gen


# ==========================================
# 4. 自动化梯度实验与可视化
# ==========================================
def run_experiment():
    print("=== 开始执行 XOR/XNOR 原生门替代梯度实验 ===")
    # 从 0% 到 100%，共 11 个梯度（也就是你要求的10个区间）
    ratios = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    avg_qubits = []

    print(f"{'原生 XOR 比例(%)':<18} | {'平均 Qubit 总数':<15}")
    print("-" * 38)

    for r in ratios:
        q_sum = 0
        trials = 10  # 每个梯度跑10次以平滑随机性
        for _ in range(trials):
            model = build_system(ratio_direct=r)
            q_sum += model.q_count

        avg_q = q_sum / trials
        avg_qubits.append(avg_q)
        print(f"{r * 100:>15.0f}%   | {avg_q:>15.1f}")

    # ===== 绘制折线图 =====
    plt.figure(figsize=(10, 6))

    # 画折线
    plt.plot([r * 100 for r in ratios], avg_qubits, marker='o', linestyle='-', linewidth=2.5, color='#8e44ad')

    plt.title('Impact of Native XOR/XNOR Gates on Total Qubits', fontsize=15, fontweight='bold')
    plt.xlabel('Proportion of Direct Native XOR/XNOR Gates (%)', fontsize=13)
    plt.ylabel('Total Qubits Required', fontsize=13)
    plt.grid(True, linestyle='--', alpha=0.7)

    # 标注起点和终点
    plt.text(0, avg_qubits[0] - 2, f"0% Native\n{int(avg_qubits[0])} Qubits\n(Composite Only)", ha='left', va='top',
             color='#c0392b', fontweight='bold')
    plt.text(100, avg_qubits[-1] + 2, f"100% Native\n{int(avg_qubits[-1])} Qubits", ha='right', va='bottom',
             color='#27ae60', fontweight='bold')

    plt.tight_layout()
    filename = "XOR_Native_Ratio_Experiment.png"
    plt.savefig(filename, dpi=300)
    print(f"\n实验完成！量子比特消耗曲线图已保存至当前目录: {filename}")


if __name__ == "__main__":
    run_experiment()