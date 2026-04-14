# `mux2_1` Ising 样例

这个目录给出一个最小可复现样例，演示怎样把 Vivado 结构化网表里的 `mux2_1` 转成 Ising Hamiltonian，并把它当成一个很小的 formal 反例搜索问题来检查。

## 文件

- `mux2_1.v`
  Vivado 导出的结构化网表，核心逻辑是一个 `LUT3(.INIT(8'hAC))` 形式的 2:1 mux。
- `mux2_1_formal_example.py`
  生成 Ising 报告，并对 8 组输入做完整枚举检查。
- `mux2_1_ising_example.log`
  网表转 Ising 后的总报告。
- `mux2_1_formal_summary.txt`
  输入枚举和“错误输出抬高能量”的检查结果。

## 这个样例在验证什么

这个工程里的 `mux2_1` 原始 RTL 语义是：

```text
out = sel ? in1 : in2
```

样例脚本做了两件事：

1. 把 `IBUF/OBUF/LUT3` 组成的结构网表拼成一个整体 Ising 多项式。
2. 对每组 `in1/in2/sel`：
   - 固定输入 qubit；
   - 求最低能量状态；
   - 读取最低能量状态下的 `out`；
   - 再强行把 `out` 固定成错误值，确认最低能量会上升。

如果“错误输出”对应的最低能量严格大于“自由输出”的最低能量，就可以把它理解成一个很小的 UNSAT/无反例证据。

## 运行

在项目根目录执行：

```powershell
python E:\zcling\ising_project\netlist_to_ising\mux2_1\mux2_1_formal_example.py
```

默认会生成两个文件：

```text
E:\zcling\ising_project\netlist_to_ising\mux2_1\mux2_1_ising_example.log
E:\zcling\ising_project\netlist_to_ising\mux2_1\mux2_1_formal_summary.txt
```

也可以自己指定路径：

```powershell
python E:\zcling\ising_project\netlist_to_ising\mux2_1\mux2_1_formal_example.py `
  --netlist E:\zcling\ising_project\netlist_to_ising\mux2_1\mux2_1.v `
  --report E:\zcling\ising_project\netlist_to_ising\mux2_1\my_mux_ising.log `
  --summary E:\zcling\ising_project\netlist_to_ising\mux2_1\my_mux_summary.txt
```

## 怎么把它类比到 formal

这个样例对应的 formal 思路是：

- 网表本体约束：由 primitive 的 Ising 关系组成。
- 输入约束：把主输入固定到某个测试点。
- 性质检查：把“错误输出”为真当成一个 `bad` 条件。
- 结果解释：
  如果加上 `bad` 以后最小能量上升，说明这个 `bad` 在该输入点不可满足；
  如果能量不升，说明存在反例。

在更大的设计里，可以把同样的思路推广成：

- 组合等价检查：`bad = (dut_out XOR golden_out)`。
- 有界时序检查：先做 time-unroll，再把某一拍的 `bad` 拉高。

## 当前边界

这个样例故意只用 `mux2_1`，因为它只涉及组合 primitive，便于把流程跑通。对于 `FDRE`、RAM、三态 IO、PLL 这类对象，还需要额外的时序或多值抽象，不能直接套这个最小样例。
