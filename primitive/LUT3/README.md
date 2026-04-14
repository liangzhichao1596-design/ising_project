# LUT3 Ising Generator

这个目录提供一个独立脚本，用来按给定 `INIT` 值生成 Xilinx `LUT3` primitive 对应的 Ising function 报告。

相关手册依据：

- `E:\zcling\ising_project\ug953-vivado-7series-libraries-en-us-2024.1.pdf`
- UG953 Chapter 5, `LUT3 Primitive: 3-Bit Look-Up Table with General Output`

UG953 里的关键信息可以直接对应到这个脚本：

- `LUT3` 有 3 个输入端口：`I0`、`I1`、`I2`
- 1 个输出端口：`O`
- 必须使用 8-bit 的 `INIT` 属性来定义逻辑功能
- 真值表顺序是：

```text
I2 I1 I0 -> O
0  0  0  -> INIT[0]
0  0  1  -> INIT[1]
0  1  0  -> INIT[2]
0  1  1  -> INIT[3]
1  0  0  -> INIT[4]
1  0  1  -> INIT[5]
1  1  0  -> INIT[6]
1  1  1  -> INIT[7]
```

也就是说，`INIT` 的 bit 下标按 `{I2, I1, I0}` 形成的二进制索引来选中。

## 脚本

- [LUT3.py](/E:/zcling/ising_project/primitive/LUT3/LUT3.py:1)

## 用法

在项目根目录或当前目录执行都可以：

```powershell
python E:\zcling\ising_project\primitive\LUT3\LUT3.py --init 8'hAC
```

也支持这些写法：

```powershell
python E:\zcling\ising_project\primitive\LUT3\LUT3.py --init 0xAC
python E:\zcling\ising_project\primitive\LUT3\LUT3.py --init 8'b10101100
python E:\zcling\ising_project\primitive\LUT3\LUT3.py --init 172
```

如果不写参数，默认使用：

```text
8'h00
```

## 输出

脚本会在当前目录生成或覆盖：

- [LUT3.log](/E:/zcling/ising_project/primitive/LUT3/LUT3.log:1)

报告中包含：

- Ising function
- qubit 数量
- qubit 和 primitive 端口的映射
- LUT3 真值表
- 全部 qubit 组合下的 Ising truth table
- 最小能量和验证摘要

## 例子

`INIT = 8'hAC` 常见于 2:1 mux 形式的 LUT3 实现。运行：

```powershell
python E:\zcling\ising_project\primitive\LUT3\LUT3.py --init 8'hAC
```

脚本会把这个 `INIT` 交给公共 primitive 建模库，并生成对应的 `LUT3` Ising Hamiltonian。

## 实现说明

这个脚本本身只负责：

1. 解析命令行 `INIT`
2. 校验 `INIT` 格式
3. 调用公共库 `ising_primitive_lib.py` 中已有的 `LUT3` 建模逻辑

真正的 `LUT3 -> Ising` 建模入口在：

- [ising_primitive_lib.py](/E:/zcling/ising_project/primitive/common/ising_primitive_lib.py:778)
- `build_lut_primitive(...)` 在 [ising_primitive_lib.py](/E:/zcling/ising_project/primitive/common/ising_primitive_lib.py:512)
