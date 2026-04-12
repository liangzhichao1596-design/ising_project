// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2024.1 (win64) Build 5076996 Wed May 22 18:37:14 MDT 2024
// Date        : Sat Apr 11 13:46:59 2026
// Host        : zcling running 64-bit major release  (build 9200)
// Command     : write_verilog E:/zcling/ising_project/vivado_prj/decoder_4to16/rtl/decoder_4_16.v
// Design      : decoder_4to16
// Purpose     : This is a Verilog netlist of the current design or from a specific cell of the design. The output is an
//               IEEE 1364-2001 compliant Verilog HDL file that contains netlist information obtained from the input
//               design files.
// Device      : xc7k70tfbv676-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* STRUCTURAL_NETLIST = "yes" *)
module decoder_4to16
   (en,
    addr,
    decode_out);
  input en;
  input [3:0]addr;
  output [15:0]decode_out;

  wire [3:0]addr;
  wire [3:0]addr_IBUF;
  wire [15:0]decode_out;
  wire [15:0]decode_out_OBUF;
  wire en;
  wire en_IBUF;

  IBUF \addr_IBUF[0]_inst 
       (.I(addr[0]),
        .O(addr_IBUF[0]));
  IBUF \addr_IBUF[1]_inst 
       (.I(addr[1]),
        .O(addr_IBUF[1]));
  IBUF \addr_IBUF[2]_inst 
       (.I(addr[2]),
        .O(addr_IBUF[2]));
  IBUF \addr_IBUF[3]_inst 
       (.I(addr[3]),
        .O(addr_IBUF[3]));
  OBUF \decode_out_OBUF[0]_inst 
       (.I(decode_out_OBUF[0]),
        .O(decode_out[0]));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT5 #(
    .INIT(32'h00010000)) 
    \decode_out_OBUF[0]_inst_i_1 
       (.I0(addr_IBUF[3]),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[0]),
        .I3(addr_IBUF[2]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[0]));
  OBUF \decode_out_OBUF[10]_inst 
       (.I(decode_out_OBUF[10]),
        .O(decode_out[10]));
  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[10]_inst_i_1 
       (.I0(addr_IBUF[1]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[3]),
        .I3(addr_IBUF[0]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[10]));
  OBUF \decode_out_OBUF[11]_inst 
       (.I(decode_out_OBUF[11]),
        .O(decode_out[11]));
  (* SOFT_HLUTNM = "soft_lutpair5" *) 
  LUT5 #(
    .INIT(32'h40000000)) 
    \decode_out_OBUF[11]_inst_i_1 
       (.I0(addr_IBUF[2]),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[0]),
        .I3(en_IBUF),
        .I4(addr_IBUF[3]),
        .O(decode_out_OBUF[11]));
  OBUF \decode_out_OBUF[12]_inst 
       (.I(decode_out_OBUF[12]),
        .O(decode_out[12]));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[12]_inst_i_1 
       (.I0(addr_IBUF[2]),
        .I1(addr_IBUF[0]),
        .I2(addr_IBUF[3]),
        .I3(addr_IBUF[1]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[12]));
  OBUF \decode_out_OBUF[13]_inst 
       (.I(decode_out_OBUF[13]),
        .O(decode_out[13]));
  (* SOFT_HLUTNM = "soft_lutpair6" *) 
  LUT5 #(
    .INIT(32'h40000000)) 
    \decode_out_OBUF[13]_inst_i_1 
       (.I0(addr_IBUF[1]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[0]),
        .I3(en_IBUF),
        .I4(addr_IBUF[3]),
        .O(decode_out_OBUF[13]));
  OBUF \decode_out_OBUF[14]_inst 
       (.I(decode_out_OBUF[14]),
        .O(decode_out[14]));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT5 #(
    .INIT(32'h40000000)) 
    \decode_out_OBUF[14]_inst_i_1 
       (.I0(addr_IBUF[0]),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[2]),
        .I3(en_IBUF),
        .I4(addr_IBUF[3]),
        .O(decode_out_OBUF[14]));
  OBUF \decode_out_OBUF[15]_inst 
       (.I(decode_out_OBUF[15]),
        .O(decode_out[15]));
  (* SOFT_HLUTNM = "soft_lutpair7" *) 
  LUT5 #(
    .INIT(32'h80000000)) 
    \decode_out_OBUF[15]_inst_i_1 
       (.I0(en_IBUF),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[0]),
        .I3(addr_IBUF[3]),
        .I4(addr_IBUF[2]),
        .O(decode_out_OBUF[15]));
  OBUF \decode_out_OBUF[1]_inst 
       (.I(decode_out_OBUF[1]),
        .O(decode_out[1]));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT5 #(
    .INIT(32'h00020000)) 
    \decode_out_OBUF[1]_inst_i_1 
       (.I0(addr_IBUF[0]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[1]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[1]));
  OBUF \decode_out_OBUF[2]_inst 
       (.I(decode_out_OBUF[2]),
        .O(decode_out[2]));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT5 #(
    .INIT(32'h00020000)) 
    \decode_out_OBUF[2]_inst_i_1 
       (.I0(addr_IBUF[1]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[0]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[2]));
  OBUF \decode_out_OBUF[3]_inst 
       (.I(decode_out_OBUF[3]),
        .O(decode_out[3]));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[3]_inst_i_1 
       (.I0(addr_IBUF[0]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[1]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[3]));
  OBUF \decode_out_OBUF[4]_inst 
       (.I(decode_out_OBUF[4]),
        .O(decode_out[4]));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT5 #(
    .INIT(32'h00020000)) 
    \decode_out_OBUF[4]_inst_i_1 
       (.I0(addr_IBUF[2]),
        .I1(addr_IBUF[0]),
        .I2(addr_IBUF[1]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[4]));
  OBUF \decode_out_OBUF[5]_inst 
       (.I(decode_out_OBUF[5]),
        .O(decode_out[5]));
  (* SOFT_HLUTNM = "soft_lutpair2" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[5]_inst_i_1 
       (.I0(addr_IBUF[0]),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[2]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[5]));
  OBUF \decode_out_OBUF[6]_inst 
       (.I(decode_out_OBUF[6]),
        .O(decode_out[6]));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[6]_inst_i_1 
       (.I0(addr_IBUF[1]),
        .I1(addr_IBUF[0]),
        .I2(addr_IBUF[2]),
        .I3(addr_IBUF[3]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[6]));
  OBUF \decode_out_OBUF[7]_inst 
       (.I(decode_out_OBUF[7]),
        .O(decode_out[7]));
  (* SOFT_HLUTNM = "soft_lutpair3" *) 
  LUT5 #(
    .INIT(32'h40000000)) 
    \decode_out_OBUF[7]_inst_i_1 
       (.I0(addr_IBUF[3]),
        .I1(addr_IBUF[1]),
        .I2(addr_IBUF[0]),
        .I3(en_IBUF),
        .I4(addr_IBUF[2]),
        .O(decode_out_OBUF[7]));
  OBUF \decode_out_OBUF[8]_inst 
       (.I(decode_out_OBUF[8]),
        .O(decode_out[8]));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT5 #(
    .INIT(32'h00020000)) 
    \decode_out_OBUF[8]_inst_i_1 
       (.I0(addr_IBUF[3]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[1]),
        .I3(addr_IBUF[0]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[8]));
  OBUF \decode_out_OBUF[9]_inst 
       (.I(decode_out_OBUF[9]),
        .O(decode_out[9]));
  (* SOFT_HLUTNM = "soft_lutpair4" *) 
  LUT5 #(
    .INIT(32'h00200000)) 
    \decode_out_OBUF[9]_inst_i_1 
       (.I0(addr_IBUF[0]),
        .I1(addr_IBUF[2]),
        .I2(addr_IBUF[3]),
        .I3(addr_IBUF[1]),
        .I4(en_IBUF),
        .O(decode_out_OBUF[9]));
  IBUF en_IBUF_inst
       (.I(en),
        .O(en_IBUF));
endmodule
