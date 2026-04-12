`timescale 1ns / 1ps

module top (
    input  [31:0] a,
    input  [31:0] b,
    input  [4:0]  alu_op,
    output reg [31:0] y,
    output        zero,
    output        negative,
    output        carry_out,
    output        overflow,
    output        parity_even,
    output        eq,
    output        lt_signed,
    output        lt_unsigned
);

    // Operation encoding
    localparam ALU_ADD       = 5'd0;
    localparam ALU_SUB       = 5'd1;
    localparam ALU_AND       = 5'd2;
    localparam ALU_OR        = 5'd3;
    localparam ALU_XOR       = 5'd4;
    localparam ALU_NOR       = 5'd5;
    localparam ALU_SLL       = 5'd6;
    localparam ALU_SRL       = 5'd7;
    localparam ALU_SRA       = 5'd8;
    localparam ALU_ROL       = 5'd9;
    localparam ALU_ROR       = 5'd10;
    localparam ALU_SLT       = 5'd11;
    localparam ALU_SLTU      = 5'd12;
    localparam ALU_MAX       = 5'd13;
    localparam ALU_MIN       = 5'd14;
    localparam ALU_ABS       = 5'd15;
    localparam ALU_BYTE_SWAP = 5'd16;
    localparam ALU_POPCOUNT  = 5'd17;
    localparam ALU_CLZ       = 5'd18;
    localparam ALU_CTZ       = 5'd19;
    localparam ALU_MUL_LOW   = 5'd20;
    localparam ALU_MUL_HIGH  = 5'd21;
    localparam ALU_AVG       = 5'd22;
    localparam ALU_PACK      = 5'd23;
    localparam ALU_SAT_ADD   = 5'd24;
    localparam ALU_SAT_SUB   = 5'd25;
    localparam ALU_BITREV    = 5'd26;
    localparam ALU_EQ        = 5'd27;
    localparam ALU_XNOR      = 5'd28;
    localparam ALU_PASS_A    = 5'd29;
    localparam ALU_PASS_B    = 5'd30;

    wire signed [31:0] a_signed;
    wire signed [31:0] b_signed;
    wire [4:0]         shamt;
    wire [63:0]        mul_u;
    wire signed [63:0] mul_s;

    reg  [32:0] sum_ext;
    reg  [32:0] diff_ext;
    reg         carry_r;
    reg         overflow_r;

    assign a_signed = a;
    assign b_signed = b;
    assign shamt = b[4:0];
    assign mul_u = a * b;
    assign mul_s = a_signed * b_signed;

    function [31:0] popcount32;
        input [31:0] value;
        integer i;
        begin
            popcount32 = 32'd0;
            for (i = 0; i < 32; i = i + 1) begin
                popcount32 = popcount32 + value[i];
            end
        end
    endfunction

    function [31:0] clz32;
        input [31:0] value;
        integer i;
        begin
            clz32 = 32'd32;
            for (i = 31; i >= 0; i = i - 1) begin
                if (value[i] && (clz32 == 32'd32)) begin
                    clz32 = 31 - i;
                end
            end
        end
    endfunction

    function [31:0] ctz32;
        input [31:0] value;
        integer i;
        begin
            ctz32 = 32'd32;
            for (i = 0; i < 32; i = i + 1) begin
                if (value[i] && (ctz32 == 32'd32)) begin
                    ctz32 = i;
                end
            end
        end
    endfunction

    function [31:0] reverse_bits32;
        input [31:0] value;
        integer i;
        begin
            reverse_bits32 = 32'd0;
            for (i = 0; i < 32; i = i + 1) begin
                reverse_bits32[i] = value[31 - i];
            end
        end
    endfunction

    always @(*) begin
        sum_ext = {1'b0, a} + {1'b0, b};
        diff_ext = {1'b0, a} - {1'b0, b};

        y = 32'd0;
        carry_r = 1'b0;
        overflow_r = 1'b0;

        case (alu_op)
            ALU_ADD: begin
                y = sum_ext[31:0];
                carry_r = sum_ext[32];
                overflow_r = (~(a[31] ^ b[31])) & (a[31] ^ sum_ext[31]);
            end

            ALU_SUB: begin
                y = diff_ext[31:0];
                carry_r = ~diff_ext[32];
                overflow_r = (a[31] ^ b[31]) & (a[31] ^ diff_ext[31]);
            end

            ALU_AND:       y = a & b;
            ALU_OR:        y = a | b;
            ALU_XOR:       y = a ^ b;
            ALU_NOR:       y = ~(a | b);
            ALU_SLL:       y = a << shamt;
            ALU_SRL:       y = a >> shamt;
            ALU_SRA:       y = a_signed >>> shamt;

            ALU_ROL: begin
                if (shamt == 5'd0) begin
                    y = a;
                end else begin
                    y = (a << shamt) | (a >> (32 - shamt));
                end
            end

            ALU_ROR: begin
                if (shamt == 5'd0) begin
                    y = a;
                end else begin
                    y = (a >> shamt) | (a << (32 - shamt));
                end
            end

            ALU_SLT:       y = {31'd0, (a_signed < b_signed)};
            ALU_SLTU:      y = {31'd0, (a < b)};
            ALU_MAX:       y = (a_signed > b_signed) ? a : b;
            ALU_MIN:       y = (a_signed < b_signed) ? a : b;

            ALU_ABS: begin
                if (a[31]) begin
                    y = (~a) + 32'd1;
                    overflow_r = (a == 32'h8000_0000);
                end else begin
                    y = a;
                end
            end

            ALU_BYTE_SWAP: y = {a[7:0], a[15:8], a[23:16], a[31:24]};
            ALU_POPCOUNT:  y = popcount32(a);
            ALU_CLZ:       y = clz32(a);
            ALU_CTZ:       y = ctz32(a);
            ALU_MUL_LOW:   y = mul_u[31:0];
            ALU_MUL_HIGH:  y = mul_s[63:32];
            ALU_AVG:       y = (a & b) + ((a ^ b) >> 1);
            ALU_PACK:      y = {a[15:0], b[15:0]};

            ALU_SAT_ADD: begin
                if ((~(a[31] ^ b[31])) && (a[31] ^ sum_ext[31])) begin
                    y = a[31] ? 32'h8000_0000 : 32'h7fff_ffff;
                    overflow_r = 1'b1;
                end else begin
                    y = sum_ext[31:0];
                    carry_r = sum_ext[32];
                end
            end

            ALU_SAT_SUB: begin
                if ((a[31] ^ b[31]) && (a[31] ^ diff_ext[31])) begin
                    y = a[31] ? 32'h8000_0000 : 32'h7fff_ffff;
                    overflow_r = 1'b1;
                end else begin
                    y = diff_ext[31:0];
                    carry_r = ~diff_ext[32];
                end
            end

            ALU_BITREV: y = reverse_bits32(a);
            ALU_EQ:     y = {31'd0, (a == b)};
            ALU_XNOR:   y = ~(a ^ b);
            ALU_PASS_A: y = a;
            ALU_PASS_B: y = b;

            default: y = 32'd0;
        endcase
    end

    assign zero = (y == 32'd0);
    assign negative = y[31];
    assign carry_out = carry_r;
    assign overflow = overflow_r;
    assign parity_even = ~^y;
    assign eq = (a == b);
    assign lt_signed = (a_signed < b_signed);
    assign lt_unsigned = (a < b);

endmodule
