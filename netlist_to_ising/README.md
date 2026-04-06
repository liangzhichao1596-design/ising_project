# `generate_netlist_ising.py` 使用说明

这个脚本的作用是：

把 Vivado 导出的、包含 Xilinx primitive 例化的结构化 Verilog 网表，组合成一个总的 Ising 报告。

## 脚本路径

`E:\zcling\ising_project\netlist_to_ising\generate_netlist_ising.py`

## 基本用法

```powershell
python E:\zcling\ising_project\netlist_to_ising\generate_netlist_ising.py [网表路径] [--output 输出log路径]
```

## 参数说明

`网表路径`

- 可选参数。
- 表示要转换的 Verilog 网表文件路径。
- 如果不写，默认使用：

```text
E:\zcling\ising_project\netlist_to_ising\mux2_1.v
```

`--output`

- 可选参数。
- 表示生成的 log 文件输出路径。
- 如果不写，默认会在输入网表所在目录生成：

```text
<网表文件名>_ising.log
```

例如 `mux2_1.v` 会生成 `mux2_1_ising.log`。

## 使用示例

1. 使用默认的 `mux2_1.v` 生成报告

```powershell
python E:\zcling\ising_project\netlist_to_ising\generate_netlist_ising.py
```

2. 指定一个网表文件

```powershell
python E:\zcling\ising_project\netlist_to_ising\generate_netlist_ising.py E:\zcling\ising_project\netlist_to_ising\mux2_1.v
```

3. 指定输出文件名

```powershell
python E:\zcling\ising_project\netlist_to_ising\generate_netlist_ising.py E:\zcling\ising_project\netlist_to_ising\mux2_1.v --output E:\zcling\ising_project\netlist_to_ising\mux2_1_custom.log
```

## 输出内容

当前生成的 log 包含以下内容：

1. 总最低能量 `Total Minimum Energy`
2. 总 qubit 数 `Total Qubits`
3. 三次项列表 `CUBIC TERMS LIST`
4. 去掉三次项后的 Ising 函数 `F_QUADRATIC`
5. 完整的总 Ising 函数 `F_TOTAL`
6. 完整的 qubit 与网表端口/连线的映射关系
7. 网表中的 primitive 实例摘要

## 如果要修改 LUT 的 `INIT`

这个脚本会直接读取网表中的 LUT 参数，比如：

```verilog
LUT3 #(
  .INIT(8'hAC))
```

如果你想修改 LUT 的逻辑功能，最直接的做法就是：

1. 先改网表里的 `.INIT(...)`
2. 再重新运行这个脚本生成新的 Ising 报告

目前支持的 `INIT` 写法包括：

- `8'hAC`
- `0xAC`
- `8'b10101100`
- 十进制整数

## 当前脚本的假设

1. 输入文件是 Vivado 风格的结构化 Verilog 网表。
2. 网表中使用到的 primitive，必须已经在 `primitive/common/ising_primitive_lib.py` 里支持。
3. primitive 之间的连接方式，是通过“共享同一个 net 就共享同一个全局 qubit”来组合的。
4. 每个 primitive 自己内部的 ancilla qubit 会保留下来，作为新的全局 qubit。

## `mux2_1.v` 的默认输出

对于下面这个输入：

`E:\zcling\ising_project\netlist_to_ising\mux2_1.v`

默认会生成：

`E:\zcling\ising_project\netlist_to_ising\mux2_1_ising.log`

## 说明和限制

1. 这个脚本目前不会修改原始网表文件。
2. 这个脚本目前还没有提供命令行方式去直接覆盖某个 LUT 的 `INIT`，而是直接使用网表里已经写好的参数。
3. 对于更大的网表，最低能量的计算目前是通过枚举所有全局 qubit 完成的，所以 qubit 很多时运行时间会明显变长。
