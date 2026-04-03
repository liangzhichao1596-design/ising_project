import re
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

# ===================== 方案A：原生 XOR/XNOR 三次项模型 =====================
class IsingSystem_Native:
    def __init__(self):
        self.q_count = 0
        self.var_map = {}

        self.cubic_terms_list = []
        self.cubic_terms_full = []
        self.quad_terms_list = []
        self.min_energy = 0

    def get_q(self, desc):
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        if gate_type == "NOT":
            a = inputs[0]
            x = out_var
            return f"(2*{a}*{x})", -2

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
            clean_term_str = term[1:] if term.startswith('+') else term
            vars_in_term = re.findall(r"q\[\d+\]", term)
            if len(vars_in_term) == 3:
                self.cubic_terms_full.append(clean_term_str)
                self.cubic_terms_list.append(clean_term_str)
            else:
                self.quad_terms_list.append(clean_term_str)
        return out_q

    def XOR(self, a, b, name):
        return self.add_gate("XOR", [a, b], name)

    def OR_Tree(self, bits, name):
        current = bits
        layer = 0
        while len(current) > 1:
            next_layer = []
            i = 0
            while i < len(current):
                rem = len(current) - i
                if rem >= 3:
                    res = self.add_gate("OR", [current[i], current[i+1], current[i+2]], f"Tree_{name}_L{layer}")
                    next_layer.append(res)
                    i += 3
                elif rem == 2:
                    res = self.add_gate("OR", [current[i], current[i+1]], f"Tree_{name}_L{layer}")
                    next_layer.append(res)
                    i += 2
                else:
                    next_layer.append(current[i])
                    i += 1
            current = next_layer
            layer += 1
        return current[0]

# ===================== 方案B：组合门 XOR（原始拼接方式）=====================
class IsingSystem_Composite:
    def __init__(self):
        self.q_count = 0
        self.var_map = {}

        self.cubic_terms_list = []
        self.cubic_terms_full = []
        self.quad_terms_list = []
        self.min_energy = 0

    def get_q(self, desc):
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    # ✅ 修复：参数名统一为 out_var
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        if gate_type == "NOT":
            a = inputs[0]
            x = out_var
            return f"(2*{a}*{x})", -2
        if len(inputs) == 2:
            a, b = inputs
            x = out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3
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
            clean_term_str = term[1:] if term.startswith('+') else term
            vars_in_term = re.findall(r"q\[\d+\]", term)
            if len(vars_in_term) == 3:
                self.cubic_terms_full.append(clean_term_str)
                self.cubic_terms_list.append(clean_term_str)
            else:
                self.quad_terms_list.append(clean_term_str)
        return out_q

    def XOR(self, a, b, internal_name):
        or_res = self.add_gate("OR", [a, b], f"Aux_OR({internal_name})")
        and_res = self.add_gate("AND", [a, b], f"Aux_AND({internal_name})")
        nand_res = self.add_gate("NOT", [and_res], f"Aux_NAND({internal_name})")
        return self.add_gate("AND", [or_res, nand_res], f"XOR_OUT({internal_name})")

    def OR_Tree(self, bits, name):
        current = bits
        layer = 0
        while len(current) > 1:
            next_layer = []
            i = 0
            while i < len(current):
                rem = len(current) - i
                if rem >= 3:
                    res = self.add_gate("OR", [current[i], current[i+1], current[i+2]], f"Tree_{name}_L{layer}")
                    next_layer.append(res)
                    i += 3
                elif rem == 2:
                    res = self.add_gate("OR", [current[i], current[i+1]], f"Tree_{name}_L{layer}")
                    next_layer.append(res)
                    i += 2
                else:
                    next_layer.append(current[i])
                    i += 1
            current = next_layer
            layer += 1
        return current[0]

# ===================== 4bit 加法器构建函数 =====================
def build_adder(ising_class, bit_width=4):
    gen = ising_class()
    A, B = [], []
    for i in range(bit_width):
        A.append(gen.get_q(f"A{i}"))
        B.append(gen.get_q(f"B{i}"))
    Cin = gen.get_q("Cin")

    # RCA
    S_RCA = []
    c_curr = Cin
    for i in range(bit_width):
        t1 = gen.XOR(A[i], B[i], f"RCA_t1_{i}")
        s = gen.XOR(t1, c_curr, f"RCA_sum_{i}")
        S_RCA.append(s)
        ab = gen.add_gate("AND", [A[i], B[i]], f"AB_{i}")
        ac = gen.add_gate("AND", [A[i], c_curr], f"AC_{i}")
        bc = gen.add_gate("AND", [B[i], c_curr], f"BC_{i}")
        c_curr = gen.add_gate("OR", [ab, ac, bc], f"C_{i}")
    C_RCA = c_curr

    # CLA
    G = [gen.add_gate("AND", [A[i], B[i]], f"G{i}") for i in range(bit_width)]
    P = [gen.XOR(A[i], B[i], f"P{i}") for i in range(bit_width)]
    C_CLA_Chain = [Cin]
    for i in range(bit_width):
        pc = gen.add_gate("AND", [P[i], C_CLA_Chain[-1]], f"PC_{i}")
        c_next = gen.add_gate("OR", [G[i], pc], f"C_CLA_{i}")
        C_CLA_Chain.append(c_next)
    S_CLA = [gen.XOR(P[i], C_CLA_Chain[i], f"S_CLA_{i}") for i in range(bit_width)]
    C_CLA = C_CLA_Chain[-1]

    # Miter
    diffs = [gen.XOR(S_RCA[i], S_CLA[i], f"Diff_{i}") for i in range(bit_width)]
    diffs.append(gen.XOR(C_RCA, C_CLA, "Diff_Cout"))
    gen.OR_Tree(diffs, "FinalDiff")
    return gen.q_count

# ===================== 统计与绘图 =====================
if __name__ == "__main__":
    bits_list = [1,2,3,4,5,6,7,8]
    native_qubits = []
    composite_qubits = []

    print("\n[+] 正在计算 qubit 用量...")
    for b in bits_list:
        q1 = build_adder(IsingSystem_Native, b)
        q2 = build_adder(IsingSystem_Composite, b)
        native_qubits.append(q1)
        composite_qubits.append(q2)

    # 表格输出
    data = pd.DataFrame({
        "bits": bits_list,
        "with_XOR/XNOR(qubit)": native_qubits,
        "without_XOR(qubit)": composite_qubits,
        "extra_qubit": [c-n for c,n in zip(composite_qubits, native_qubits)]
    })
    print("\n" + "="*80)
    print(" 4bits_adder Ising model qubit contrast ")
    print("="*80)
    print(tabulate(data, headers='keys', tablefmt='grid', showindex=False))

    # 画图
    plt.figure(figsize=(10,5))
    plt.bar([x-0.2 for x in bits_list], native_qubits, width=0.4, label="with_XOR/XNOR", color="#2E86AB")
    plt.bar([x+0.2 for x in bits_list], composite_qubits, width=0.4, label="without_XOR/XNOR", color="#A23B72")
    plt.plot(bits_list, native_qubits, 'o-', color='#005a9c')
    plt.plot(bits_list, composite_qubits, 'o-', color='#9c005c')

    plt.xlabel("bit")
    plt.ylabel("qubit_number (qubit)")
    plt.title("Ising model：with XOR/XNOR vs without XOR/XNOR contrast")
    plt.xticks(bits_list)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()