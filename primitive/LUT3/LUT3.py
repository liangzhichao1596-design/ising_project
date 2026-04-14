from __future__ import annotations

import argparse
from pathlib import Path
import sys


THIS_DIR = Path(__file__).resolve().parent
#THIS_dIR = E:\zcling\ising_project\primitive\LUT3
COMMON_DIR = THIS_DIR.parent / "common"
#COMMON_DIR = E:\zcling\ising_project\primitive\common
sys.path.append(str(COMMON_DIR))
#Python 导入模块（import xxx）时，只会去这些目录里找。

from ising_primitive_lib import parse_verilog_int, run_named_primitive
# 从 common 目录下的 ising_primitive_lib.py 文件中导入 parse_verilog_int 和 run_named_primitive 函数。

def build_parser() -> argparse.ArgumentParser:
    #-> argparse.ArgumentParser: 这是函数的返回类型提示，表示这个函数会返回一个 argparse.ArgumentParser 对象。
    parser = argparse.ArgumentParser(
        description="Generate the Ising function/report for a Xilinx LUT3 primitive."
    )
    #--help 参数是 argparse.ArgumentParser 的一个内置参数，用于提供命令行工具的帮助信息。当用户在命令行中使用 --help 参数时，argparse 会自动生成并显示帮助信息，说明该工具的用途和可用的参数。
    parser.add_argument(
        "--init",
        default="8'h00",
        help=(
            "LUT3 INIT value. Supported forms include 8'hAC, 0xAC, "
            "8'b10101100, or decimal. Default: 8'h00."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate early so the user gets a clear error before entering the common flow.
    parse_verilog_int(args.init)
    # 解析命令行输入
    # 例如用户运行：
    # python LUT3.py --init 8'hAC
    # 解析后，args.init 就是 "8'hAC"

    log_path = run_named_primitive("LUT3", THIS_DIR, ["--init", args.init])
    print(f"LUT3 INIT = 0x{parse_verilog_int(args.init):02X}")
    print(f"Ising report written to: {log_path}")


if __name__ == "__main__":
    main()
