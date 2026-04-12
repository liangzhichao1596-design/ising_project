# Large Decoder RTL

本目录包含一个纯组合逻辑实现的大规模译码器：

- [large_decoder.v](E:/zcling/ising_project/WEEK4_10/decoder/rtl/large_decoder.v)

## 功能说明

`large_decoder` 是一个 `10-to-1024` 的 one-hot 译码器。

它采用两级预译码结构：

- 高 `5` 位地址 `addr[9:5]` 译码成 `32-bit` 的 `bank_sel`
- 低 `5` 位地址 `addr[4:0]` 译码成 `32-bit` 的 `word_sel`
- 再将两级结果做与运算，生成最终的 `1024-bit` one-hot 输出 `decode_out`

当 `en=1` 时：

- `decode_out` 中只有一个 bit 为 `1`
- 该 bit 的位置由 `addr[9:5]` 和 `addr[4:0]` 共同决定

当 `en=0` 时：

- `bank_sel = 32'b0`
- `word_sel = 32'b0`
- `decode_out = 1024'b0`

## 端口说明

### 输入端口

- `en`
  - 位宽：`1`
  - 作用：总使能信号
  - 说明：为 `1` 时开启译码，为 `0` 时所有译码输出清零

- `addr`
  - 位宽：`10`
  - 作用：输入地址
  - 说明：
    - `addr[9:5]` 用于选择 bank
    - `addr[4:0]` 用于选择 word

### 输出端口

- `bank_sel`
  - 位宽：`32`
  - 作用：高 5 位地址的 one-hot 预译码结果

- `word_sel`
  - 位宽：`32`
  - 作用：低 5 位地址的 one-hot 预译码结果

- `decode_out`
  - 位宽：`1024`
  - 作用：最终 one-hot 译码输出
  - 说明：索引计算方式为：
    - `decode_out[bank_index * 32 + word_index]`

- `hit`
  - 位宽：`1`
  - 作用：译码有效标志
  - 说明：当前实现中 `hit = en`

## 内部实现

模块内部使用以下纯组合逻辑：

- `assign bank_predecode = en ? (32'b1 << addr[9:5]) : 32'b0;`
- `assign word_predecode = en ? (32'b1 << addr[4:0]) : 32'b0;`
- 双层 `generate for` 循环完成 `1024` 路输出展开

这类实现方式的特点是：

- 结构清晰
- 易于综合
- 适合做大规模 one-hot 译码器建模与实验

## 例子

### 例 1

当：

- `en = 1`
- `addr[9:5] = 3`
- `addr[4:0] = 5`

则：

- `bank_sel[3] = 1`
- `word_sel[5] = 1`
- `decode_out[3 * 32 + 5] = decode_out[101] = 1`

其余位为 `0`。

### 例 2

当：

- `en = 0`

则所有输出均为 `0`。
