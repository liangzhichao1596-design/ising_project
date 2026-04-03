import re
import os
import random
import matplotlib.pyplot as plt


class IsingSystem:
    def __init__(self, ratio_3in=1.0):
        self.q_count = 0
        self.var_map = {}

        # 参数：目标三输入门比例 (0.0=全二次拆解, 1.0=全保留三输入)
        self.ratio_3in = ratio_3in

        # 统计实际生成的门数量
        self.actual_3in_count = 0
        self.actual_2in_count = 0

    def get_q(self, desc):
        """分配量子比特"""
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    # ==========================================
    # 1. 映射引擎 (只管数学公式，不涉及拆解逻辑)
    # ==========================================
    def get_higher_order_ising_contribution(self, gate_type, out_var, inputs):
        if gate_type == "NOT":
            return f"(2 * {inputs[0]} * {out_var})", -2

        if len(inputs) == 2:
            a, b, x = inputs[0], inputs[1], out_var
            if gate_type == "AND":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} - {a} - {b} + 2*{x})", -3
            elif gate_type == "OR":
                return f"({a}*{b} - 2*{a}*{x} - 2*{b}*{x} + {a} + {b} - 2*{x})", -3

        elif len(inputs) == 3:
            a, b, c, x = inputs[0], inputs[1], inputs[2], out_var
            if gate_type == "AND":
                return (f"(5 - {a} + 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} + {a}*{b}*{c} "
                        f"- {a}*{b}*{x} - {a}*{c}*{x} - 2*{b}*{c}*{x})"), 0
            elif gate_type == "OR":
                return (f"(5 + {a} - 4*{x} - 2*{a}*{x} - {b}*{c} "
                        f"- {b}*{x} - {c}*{x} - {a}*{b}*{c} "
                        f"+ {a}*{b}*{x} + {a}*{c}*{x} + 2*{b}*{c}*{x})"), 0
        return "0", 0

    # ==========================================
    # 2. 智能门添加与拆解逻辑
    # ==========================================
    def add_gate(self, gate_type, inputs, desc):
        """
        核心拦截器：如果遇到 3 输入需求，根据 ratio_3in 决定是否降维
        """
        if len(inputs) == 3:
            # 根据设定的比例，随机决定是否保留为 3 输入
            if random.random() <= self.ratio_3in:
                # 幸运命中：保留为 3 输入门
                self.actual_3in_count += 1
            else:
                # 未命中：强制降维拆解为两个 2 输入门
                # 例如 OR(a, b, c) -> tmp = OR(a, b); res = OR(tmp, c)
                tmp_desc = f"Aux_Decomp_{desc}"
                tmp_q = self.add_gate(gate_type, [inputs[0], inputs[1]], tmp_desc)
                return self.add_gate(gate_type, [tmp_q, inputs[2]], desc)

        # 统计正常的 2 输入或 NOT 门
        if len(inputs) == 2:
            self.actual_2in_count += 1

        # 真正分配量子比特并生成公式 (此处省略了字符串解析过程，因为实验只关心 qubit 数量)
        out_q = self.get_q(desc)
        return out_q

    # ==========================================
    # 3. 复合逻辑门
    # ==========================================
    def XOR(self, a, b, internal_name):
        or_res = self.add_gate("OR", [a, b], f"Aux_XOR_OR({internal_name})")
        and_res = self.add_gate("AND", [a, b], f"Aux_XOR_AND({internal_name})")
        nand_res = self.add_gate("NOT", [and_res], f"Aux_XOR_NAND({internal_name})")
        return self.add_gate("AND", [or_res, nand_res], f"Aux_XOR_Res({internal_name})")

    def OR_Tree(self, bits, name):
        """尽可能提供 3 输入的需求，由 add_gate 决定是否拆解"""
        current = bits
        layer = 0
        while len(current) > 1:
            next_layer = []
            i = 0
            while i < len(current):
                rem = len(current) - i
                if rem >= 3:
                    # 尝试申请一个 3 输入门
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


# ==========================================
# 4. 电路构建 (参数化的大规模电路)
# ==========================================
def build_large_circuit(bit_width, ratio_3in):
    """构建 N 位的 RCA vs CLA 比较电路"""
    gen = IsingSystem(ratio_3in=ratio_3in)

    # 注册输入
    A = [gen.get_q(f"A[{i}]") for i in range(bit_width)]
    B = [gen.get_q(f"B[{i}]") for i in range(bit_width)]
    Cin = gen.get_q("Cin")

    # --- RCA (行波进位) ---
    S_RCA = []
    c_curr = Cin
    for i in range(bit_width):
        t1 = gen.XOR(A[i], B[i], f"RCA_b{i}_step1")
        s = gen.XOR(t1, c_curr, f"RCA_b{i}_step2")
        S_RCA.append(s)

        # 尝试使用 3 输入 OR 汇聚进位
        ab = gen.add_gate("AND", [A[i], B[i]], f"RCA_Cry_AB_{i}")
        ac = gen.add_gate("AND", [A[i], c_curr], f"RCA_Cry_AC_{i}")
        bc = gen.add_gate("AND", [B[i], c_curr], f"RCA_Cry_BC_{i}")
        c_curr = gen.add_gate("OR", [ab, ac, bc], f"C_RCA_Int_{i}")
    C_RCA = c_curr

    # --- CLA (超前进位) ---
    G = [gen.add_gate("AND", [A[i], B[i]], f"CLA_G_{i}") for i in range(bit_width)]
    P = [gen.XOR(A[i], B[i], f"CLA_P_{i}") for i in range(bit_width)]

    C_CLA_Chain = [Cin]
    for i in range(bit_width):
        pc = gen.add_gate("AND", [P[i], C_CLA_Chain[-1]], f"CLA_PC_{i}")
        c_next = gen.add_gate("OR", [G[i], pc], f"C_CLA_{i + 1}")
        C_CLA_Chain.append(c_next)

    S_CLA = []
    for i in range(bit_width):
        s = gen.XOR(P[i], C_CLA_Chain[i], f"CLA_Sum_{i}")
        S_CLA.append(s)
    C_CLA = C_CLA_Chain[-1]

    # --- Miter 比较逻辑 ---
    diffs = []
    for i in range(bit_width):
        diffs.append(gen.XOR(S_RCA[i], S_CLA[i], f"Diff_Sum_{i}"))
    diffs.append(gen.XOR(C_RCA, C_CLA, "Diff_Cout"))

    # 最终结果汇聚树
    final_diff = gen.OR_Tree(diffs, "FinalDiff")

    return gen


# ==========================================
# 5. 自动化实验与可视化
# ==========================================
def run_experiment():
    # 采用 64 位规模（大型电路等效性验证）
    BW = 512
    print(f"=== 开始执行大规模等效性验证建模实验 (位宽: {BW} Bits) ===")

    # 我们测试三输入门比例从 0% (全二次) 到 100% (全高阶)
    test_ratios = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    results_qubits = []
    results_3in_count = []
    results_2in_count = []

    print(f"{'Target 3-in Ratio':<20} | {'实际生成3输入门':<18} | {'实际生成2输入门':<18} | {'所需总 Qubits数量':<20}")
    print("-" * 80)

    for ratio in test_ratios:
        # 为了平滑随机性带来的轻微波动，每个比例跑 5 次取平均 (蒙特卡洛思想)
        q_sum = 0
        gate3_sum = 0
        gate2_sum = 0
        trials = 5

        for _ in range(trials):
            # 随机种子在内部会自动变化
            model = build_large_circuit(bit_width=BW, ratio_3in=ratio)
            q_sum += model.q_count
            gate3_sum += model.actual_3in_count
            gate2_sum += model.actual_2in_count

        avg_q = q_sum / trials
        avg_g3 = gate3_sum / trials
        avg_g2 = gate2_sum / trials

        results_qubits.append(avg_q)
        results_3in_count.append(avg_g3)
        results_2in_count.append(avg_g2)

        print(f"{ratio * 100:>15.0f}%    | {avg_g3:>15.1f}    | {avg_g2:>15.1f}    | {avg_q:>18.1f}")

    # ===== 绘制折线图 =====
    plt.figure(figsize=(10, 6))

    # 绘制比例与量子比特总数的关系
    plt.plot([r * 100 for r in test_ratios], results_qubits, marker='o', linewidth=2.5, color='#e74c3c',
             label='Total Qubits Required')

    plt.title(
        f'Impact of High-Order (3-Input) Gates on Qubit Resources\n(Circuit: {BW}-bit RCA vs CLA Equivalence Checker)',
        fontsize=14, fontweight='bold')
    plt.xlabel('Percentage of 3-Input Gates Used (%)', fontsize=12)
    plt.ylabel('Total Number of Qubits', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)

    # 添加数值标签（首尾标注）
    plt.text(0, results_qubits[0] + 5, f"{int(results_qubits[0])} Qubits\n(Pure QUBO)", ha='left', va='bottom',
             color='#c0392b', fontweight='bold')
    plt.text(100, results_qubits[-1] - 5, f"{int(results_qubits[-1])} Qubits\n(Max HOBO)", ha='right', va='top',
             color='#c0392b', fontweight='bold')

    plt.legend()
    plt.tight_layout()

    filename = "Gate_Ratio_vs_Qubits.png"
    plt.savefig(filename, dpi=300)
    print(f"\n[成功] 实验完毕！折线图已保存至当前目录: {filename}")


if __name__ == "__main__":
    run_experiment()