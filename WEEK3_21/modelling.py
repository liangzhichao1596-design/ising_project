import re
import random


class IsingSystem:
    def __init__(self):
        self.q_count = 0
        self.var_map = {}
        self.quad_terms_list = []
        self.cubic_terms_full = []
        self.min_energy = 0

    def get_q(self, desc):
        name = f"q[{self.q_count}]"
        self.var_map[name] = desc
        self.q_count += 1
        return name

    def add_gate_raw(self, gate_type, inputs, out_var):
        """基础门 Ising 映射"""
        if gate_type == "NOT":
            a = inputs[0]
            self.quad_terms_list.append(f"(2 * {a} * {out_var} + 2)")
            self.min_energy -= 0
        elif gate_type == "AND":
            a, b = inputs
            self.quad_terms_list.append(f"({a}*{b} - 2*{a}*{out_var} - 2*{b}*{out_var} - {a} - {b} + 2*{out_var} + 2)")
            self.min_energy -= 0
        elif gate_type == "OR":
            a, b = inputs
            self.quad_terms_list.append(f"({a}*{b} - 2*{a}*{out_var} - 2*{b}*{out_var} + {a} + {b} - 2*{out_var} + 3)")
            self.min_energy -= 0
        elif gate_type == "NAND":
            a, b = inputs
            self.cubic_terms_full.append(
                f"(1 - 0.5*{out_var} + 0.5*{a}*{out_var} + 0.5*{b}*{out_var} + 0.5*{a}*{b}*{out_var})")
        elif gate_type == "XOR_DIRECT":
            a, b = inputs
            self.quad_terms_list.append(f"(-{a}*{b} - {a}*{out_var} - {b}*{out_var} + 1)")
        elif gate_type == "XNOR_DIRECT":
            a, b = inputs
            self.quad_terms_list.append(f"({a}*{b} + {a}*{out_var} + {b}*{out_var} - 1)")

    def XOR_decomposed(self, a, b, name):
        """使用 与/或/非 组合实现 XOR: (A or B) and (not (A and b))"""
        or_res = self.get_q(f"{name}_internal_or")
        self.add_gate_raw("OR", [a, b], or_res)

        and_res = self.get_q(f"{name}_internal_and")
        self.add_gate_raw("AND", [a, b], and_res)

        nand_res = self.get_q(f"{name}_internal_not")
        self.add_gate_raw("NOT", [and_res], nand_res)

        final_out = self.get_q(f"{name}_final")
        self.add_gate_raw("AND", [or_res, nand_res], final_out)
        return final_out

    def XNOR_decomposed(self, a, b, name):
        """使用 与/或/非 组合实现 XNOR: not (A xor B)"""
        xor_out = self.XOR_decomposed(a, b, f"{name}_sub_xor")
        final_out = self.get_q(f"{name}_final")
        self.add_gate_raw("NOT", [xor_out], final_out)
        return final_out


def run_experiment():
    results = []
    ratios = [i / 10 for i in range(11)]  # 0, 0.1, ..., 1.0 (11个梯度涵盖0-100%)

    # 测试电路规模：假设我们要建立一个包含 20 个随机异或逻辑的电路
    NUM_GATES = 20

    print(f"{'Ratio (Decomp)':<15} | {'Total Qubits':<15} | {'Min Energy Offset'}")
    print("-" * 50)

    for ratio in ratios:
        gen = IsingSystem()

        # 初始输入
        q_a = gen.get_q("Input_A")
        q_b = gen.get_q("Input_B")

        current_in_a = q_a
        current_in_b = q_b

        for i in range(NUM_GATES):
            gate_is_xor = (i % 2 == 0)
            use_decomposed = random.random() < ratio

            if gate_is_xor:
                if use_decomposed:
                    current_in_a = gen.XOR_decomposed(current_in_a, current_in_b, f"G{i}_XOR")
                else:
                    out = gen.get_q(f"G{i}_XOR_dir")
                    gen.add_gate_raw("XOR_DIRECT", [current_in_a, current_in_b], out)
                    current_in_a = out
            else:
                if use_decomposed:
                    current_in_a = gen.XNOR_decomposed(current_in_a, current_in_b, f"G{i}_XNOR")
                else:
                    out = gen.get_q(f"G{i}_XNOR_dir")
                    gen.add_gate_raw("XNOR_DIRECT", [current_in_a, current_in_b], out)
                    current_in_a = out

        results.append((ratio * 100, gen.q_count, gen.min_energy))
        print(f"{ratio * 100:>13.0f}% | {gen.q_count:>13} | {gen.min_energy:>15}")

    # 生成报告
    with open("XOR_Ising_Scaling_Report.txt", "w", encoding="utf-8") as f:
        f.write("XOR/XNOR Ising Modeling Scale Experiment Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"{'Decomposed Ratio (%)':<25} | {'Total Qubits Used':<20}\n")
        f.write("-" * 60 + "\n")
        for r, q, e in results:
            f.write(f"{r:<25.0f} | {q:<20}\n")
        f.write("=" * 60 + "\n")
        f.write("Note: Decomposed mode uses AND/OR/NOT gates which significantly increases Qubit count.\n")

    print("\n实验完成！详细数据已写入: XOR_Ising_Scaling_Report.txt")


if __name__ == "__main__":
    run_experiment()