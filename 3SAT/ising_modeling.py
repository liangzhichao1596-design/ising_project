import re
import os


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
    # 1. 映射引擎
    # ==========================================
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        # 非门映射
        if gate_type == "NOT":
            a = inputs[0];
            x = out_var
            return f"(2 * {a} * {x})", -2

        # 2输入门映射
        if len(inputs) == 2:
            a, b = inputs;
            x = out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3

        elif len(inputs) == 3:
            a, b, c = inputs;
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
        # 使用 Lookahead regex 分割
        terms = re.split(r'(?=[+-])', clean_expr.replace(" ", ""))

        for term in terms:
            term = term.strip()
            if not term: continue

            # 处理开头的 + 号 (对于 Python 字符串拼接非必须，但处理起来更干净)
            clean_term_str = term
            if term.startswith('+'):
                clean_term_str = term[1:]

            # 判断是否为三次项 (含有3个q)
            vars_in_term = re.findall(r"q\[\d+\]", term)

            if len(vars_in_term) == 3:
                self.cubic_terms_full.append(clean_term_str)

                # 【修改点】: 直接保存 clean_term_str 以保留系数 (例如 "4*q[0]*q[1]*q[2]")
                # 之前是 re-join 导致系数丢失
                self.cubic_terms_list.append(clean_term_str)
            else:
                self.quad_terms_list.append(clean_term_str)

        return out_q

    # ==========================================
    # 2. 复合逻辑门
    # ==========================================
    def XOR(self, a, b, internal_name):
        """XOR(A,B) = (A v B) ^ NAND(A, B)"""
        # OR
        or_res = self.add_gate("OR", [a, b], f"Aux_XOR_OR({internal_name})")
        # NAND = NOT(AND)
        and_res = self.add_gate("AND", [a, b], f"Aux_XOR_AND({internal_name})")
        nand_res = self.add_gate("NOT", [and_res], f"Aux_XOR_NAND({internal_name})")
        # Final AND
        return self.add_gate("AND", [or_res, nand_res], f"Aux_XOR_Res({internal_name})")

    def OR_Tree(self, bits, name):
        """3输入 OR 树，最大化三次项"""
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

    # --- 端口注册辅助函数 ---
    def register_input(self, q, name):
        self.key_inputs[q] = name
        self.var_map[q] = f"[INPUT] {name}"

    def register_output(self, q, name):
        self.key_outputs[q] = name
        self.var_map[q] = f"[OUTPUT] {name}"


# ==========================================
# 3. 4位加法器电路构建 (RCA vs CLA)
# ==========================================
def build_system():
    gen = IsingSystem()
    BIT_WIDTH = 4

    # --- A. 注册输入 ---
    A = []
    B = []
    for i in range(BIT_WIDTH):
        qa = gen.get_q(f"Raw_A{i}")
        qb = gen.get_q(f"Raw_B{i}")
        gen.register_input(qa, f"A[{i}]")
        gen.register_input(qb, f"B[{i}]")
        A.append(qa)
        B.append(qb)

    q_cin = gen.get_q("Raw_Cin")
    gen.register_input(q_cin, "Cin")
    Cin = q_cin

    # --- B. RCA (行波进位) ---
    S_RCA = []
    c_curr = Cin
    for i in range(BIT_WIDTH):
        t1 = gen.XOR(A[i], B[i], f"RCA_b{i}_step1")
        s = gen.XOR(t1, c_curr, f"RCA_b{i}_step2")
        gen.register_output(s, f"S_RCA[{i}]")
        S_RCA.append(s)

        # Carry Logic (利用 3输入 OR)
        ab = gen.add_gate("AND", [A[i], B[i]], f"RCA_Cry_AB_{i}")
        ac = gen.add_gate("AND", [A[i], c_curr], f"RCA_Cry_AC_{i}")
        bc = gen.add_gate("AND", [B[i], c_curr], f"RCA_Cry_BC_{i}")
        c_curr = gen.add_gate("OR", [ab, ac, bc], f"C_RCA_Int_{i}")

    C_RCA = c_curr
    gen.register_output(C_RCA, "Cout_RCA")

    # --- C. CLA (超前进位) ---
    G = [gen.add_gate("AND", [A[i], B[i]], f"CLA_G_{i}") for i in range(BIT_WIDTH)]
    P = [gen.XOR(A[i], B[i], f"CLA_P_{i}") for i in range(BIT_WIDTH)]

    C_CLA_Chain = [Cin]
    for i in range(BIT_WIDTH):
        # C[i+1] = G[i] | (P[i] & C[i])
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

    # --- D. Miter 比较逻辑 ---
    diffs = []
    for i in range(BIT_WIDTH):
        diffs.append(gen.XOR(S_RCA[i], S_CLA[i], f"Diff_Sum_{i}"))
    diffs.append(gen.XOR(C_RCA, C_CLA, "Diff_Cout"))

    # --- E. 汇聚差异 & UNSAT ---
    final_diff = gen.OR_Tree(diffs, "FinalDiff")

    # 添加强制约束: 1 - final_diff
    #gen.quad_terms_list.append(f"1")
    #gen.quad_terms_list.append(f"-{final_diff}")

    return gen


# ==========================================
# 4. 生成与文件写入
# ==========================================

model = build_system()

# 构建函数字符串
f_quad_str = " + ".join(model.quad_terms_list)
f_total_str = f"{f_quad_str} + {' + '.join(model.cubic_terms_full)}"

# 准备日志内容
log_lines = []

log_lines.append("=" * 80)
log_lines.append(" ISING MODEL GENERATION REPORT (4-bit RCA vs CLA)")
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

# 写入文件
filename = "Full_Ising_Report.log"
with open(filename, "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))

print(f"成功生成模型！")
print(f"总量子比特数: {model.q_count}")
print(f"理论最小能量: {model.min_energy}")
print(f"三次项数量: {len(model.cubic_terms_list)}")
print(f"\n所有详细数据（包括完整映射、三次项列表、二次函数、总函数）已写入文件: {filename}")
print("请打开该日志文件查看完整结果。")