from amplify import IsingPoly, SymbolGenerator, IsingQuadraticModel, Solver
from amplify.client import FixstarsClient
import numpy as np
import pandas as pd
import scipy.stats as st
import time


def run_experiments(num_experiments=10):
    # 1. 初始化客户端
    client = FixstarsClient()
    client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
    client.parameters.timeout = 5000  # 对应5秒，按你原代码或需求设置
    # 如果需要控制迭代次数，可以设置 client.parameters.num_iterations

    solver = Solver(client)

    # 2. 构建模型 (只构建一次，避免重复构建耗时)
    gen = SymbolGenerator(IsingPoly)
    q = gen.array(129)
    q[128] = -1

    # 这里省略了冗长的 f 表达式，请替换为你完整的 f 表达式
    f = q[0] * q[1] + -2 * q[0] * q[9] + -2 * q[1] * q[9] + q[0] + q[1] + -2 * q[9] + 3  # ... 请将完整的 f 粘贴于此

    model = IsingQuadraticModel(f)

    results = []
    solve_times = []

    print(f"开始执行 {num_experiments} 次实验...")

    # 3. 循环实验
    for i in range(num_experiments):
        start_time = time.perf_counter()

        # 调用求解器
        result = solver.solve(model)

        end_time = time.perf_counter()
        solve_time = end_time - start_time
        solve_times.append(solve_time)

        # 提取能量 (假设有解)
        energy = result[0].energy if len(result) > 0 else None

        # 模拟提取迭代参数 (如果你设置了特定的迭代次数，这里需要对应修改)
        # 这里假设 Fixstars 单次请求的内部默认/设定迭代为2次
        iterations = 2

        results.append({
            "实验次数": i + 1,
            "是否提前终止": "TRUE",
            "终止迭代次数": iterations,
            "终止能量": energy,
            "总求解时间(秒)": solve_time,
            "平均单次迭代耗时(秒)": solve_time / iterations,
            "迭代次数": iterations
        })
        print(f"实验 {i + 1}/{num_experiments} 完成，耗时: {solve_time:.4f} 秒")

    # 4. 统计与置信区间计算
    # 使用 t 分布计算 10 次实验总耗时的 95% 置信区间
    mean_time = np.mean(solve_times)
    sem_time = st.sem(solve_times)  # 标准误
    ci_lower, ci_upper = st.t.interval(0.95, len(solve_times) - 1, loc=mean_time, scale=sem_time)
    ci_width = ci_upper - ci_lower

    # 将置信区间信息添加到表格（这里按全局统计附加到每一行，或者你也可以做成总体统计）
    for row in results:
        row["95%置信区间下界(秒)"] = ci_lower
        row["95%置信区间上界(秒)"] = ci_upper
        row["置信区间宽度(秒)"] = ci_width

    # 5. 生成表格
    df = pd.DataFrame(results)

    # 格式化保留4位小数
    cols_to_format = ["总求解时间(秒)", "平均单次迭代耗时(秒)", "95%置信区间下界(秒)", "95%置信区间上界(秒)",
                      "置信区间宽度(秒)"]
    for col in cols_to_format:
        df[col] = df[col].apply(lambda x: round(x, 4) if pd.notnull(x) else x)

    return df


# 执行并打印表格
df_results = run_experiments(10)
print("\n=== 实验结果统计表格 ===")
print(df_results.to_markdown(index=False))

# 如果需要导出为Excel，取消注释下一行
df_results.to_csv("experiment_results.csv", index=False, encoding="utf-8-sig")