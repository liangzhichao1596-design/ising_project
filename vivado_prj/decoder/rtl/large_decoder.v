module large_decoder (
    input  wire        en,
    input  wire [9:0]  addr,
    output wire [31:0] bank_sel,
    output wire [31:0] word_sel,
    output wire [1023:0] decode_out,
    output wire        hit
);

    localparam integer PREDECODE_WIDTH = 32;
    localparam integer DECODE_WIDTH = 1024;

    wire [31:0] bank_predecode;
    wire [31:0] word_predecode;

    assign bank_predecode = en ? (32'b1 << addr[9:5]) : 32'b0;
    assign word_predecode = en ? (32'b1 << addr[4:0]) : 32'b0;

    assign bank_sel = bank_predecode;
    assign word_sel = word_predecode;
    assign hit = en;

    genvar i;
    genvar j;
    generate
        for (i = 0; i < PREDECODE_WIDTH; i = i + 1) begin : gen_bank
            for (j = 0; j < PREDECODE_WIDTH; j = j + 1) begin : gen_word
                assign decode_out[i * PREDECODE_WIDTH + j] = bank_predecode[i] & word_predecode[j];
            end
        end
    endgenerate

endmodule
