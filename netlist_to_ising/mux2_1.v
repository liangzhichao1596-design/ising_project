// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.1 (win64) Build 5076996 Wed May 22 18:37:14 MDT 2024
// Date        : Sat Apr  4 19:26:09 2026
// Host        : zcling running 64-bit major release  (build 9200)
// Command     : write_verilog E:/zcling/vivado_project/mux2_1.v
// Design      : mux2_1
// Purpose     : This is a Verilog netlist of the current design or from a specific cell of the design. The output is an
//               IEEE 1364-2001 compliant Verilog HDL file that contains netlist information obtained from the input
//               design files.
// Device      : xc7a35tfgg484-2
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* STRUCTURAL_NETLIST = "yes" *)
module mux2_1
   (in1,
    in2,
    sel,
    out);
  input in1;
  input in2;
  input sel;
  output out;

  wire in1;
  wire in1_IBUF;
  wire in2;
  wire in2_IBUF;
  wire out;
  wire out_OBUF;
  wire sel;
  wire sel_IBUF;

  IBUF in1_IBUF_inst
       (.I(in1),
        .O(in1_IBUF));
  IBUF in2_IBUF_inst
       (.I(in2),
        .O(in2_IBUF));
  OBUF out_OBUF_inst
       (.I(out_OBUF),
        .O(out));
  LUT3 #(
    .INIT(8'hAC)) 
    out_OBUF_inst_i_1
       (.I0(in1_IBUF),
        .I1(in2_IBUF),
        .I2(sel_IBUF),
        .O(out_OBUF));
  IBUF sel_IBUF_inst
       (.I(sel),
        .O(sel_IBUF));
endmodule
