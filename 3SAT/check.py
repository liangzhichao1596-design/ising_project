import itertools


def verify_asymmetric_ising_gates():
    # ==========================================
    # 1. 定义映射公式 (直接复制你的公式)
    # ==========================================
    def calc_energy_and(a, b, c, x):
        # 3-Input AND (Asymmetric, No Aux, Max Degree 3)
        # Inputs: a, b, c | Output: x
        return (1.25
                - 0.25 * a
                + 1.00 * x
                - 0.50 * a * x
                - 0.25 * b * c
                - 0.25 * b * x
                - 0.25 * c * x
                + 0.25 * a * b * c
                - 0.25 * a * b * x
                - 0.25 * a * c * x
                - 0.50 * b * c * x)

    def calc_energy_or(a, b, c, x):
        # 3-Input OR (Asymmetric, No Aux, Max Degree 3)
        # Inputs: a, b, c | Output: x
        return (1.25
                + 0.25 * a
                - 1.00 * x
                - 0.50 * a * x
                - 0.25 * b * c
                - 0.25 * b * x
                - 0.25 * c * x
                - 0.25 * a * b * c
                + 0.25 * a * b * x
                + 0.25 * a * c * x
                + 0.50 * b * c * x)

    # ==========================================
    # 2. 验证逻辑
    # ==========================================
    gates = [
        ("AND", calc_energy_and, lambda a, b, c: a == 1 and b == 1 and c == 1),
        ("OR", calc_energy_or, lambda a, b, c: a == 1 or b == 1 or c == 1)
    ]

    for gate_name, energy_func, logic_func in gates:
        print(f"\n{'=' * 60}")
        print(f" Checking {gate_name} Gate (Asymmetric 3-Body Hamiltonian)")
        print(f"{'=' * 60}")
        print(f"{'a':^3} {'b':^3} {'c':^3} | {'x':^3} | {'Valid?':^8} | {'Energy':^8} | {'Check'}")
        print("-" * 60)

        pass_count = 0

        # 遍历所有 Ising 状态: -1, 1
        states = [-1, 1]
        combinations = list(itertools.product(states, repeat=4))  # (a, b, c, x)

        for a, b, c, x in combinations:
            # 1. 计算逻辑有效性 (Logic Truth)
            # 将 -1 转为 False, 1 转为 True
            is_valid_logic = (x == 1) if logic_func(a, b, c) else (x == -1)

            # 2. 计算哈密顿量能量
            energy = energy_func(a, b, c, x)

            # 3. 判定结果
            # 浮点数比较允许微小误差
            is_zero_energy = abs(energy) < 1e-5

            status = ""
            if is_valid_logic:
                if is_zero_energy:
                    status = "✅ OK (Ground State)"
                else:
                    status = "❌ FAIL (Should be 0)"
            else:
                if energy > 0.9:  # 期望 Gap 至少为 1 或 2
                    status = "✅ OK (Penalty)"
                elif is_zero_energy:
                    status = "⚠️ FATAL (False Positive)"
                else:
                    status = "⚠️ WEAK GAP"

            valid_str = "TRUE" if is_valid_logic else "FALSE"
            print(f"{a:^3} {b:^3} {c:^3} | {x:^3} | {valid_str:^8} | {energy:^8.2f} | {status}")

            if "FAIL" in status or "FATAL" in status:
                pass
            else:
                pass_count += 1

        print("-" * 60)
        if pass_count == 16:
            print(f"🏆 {gate_name} Result: PERFECT MAPPING.")
        else:
            print(f"💀 {gate_name} Result: MAPPING FAILED.")


# 执行脚本
if __name__ == "__main__":
    verify_asymmetric_ising_gates()