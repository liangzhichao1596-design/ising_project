module decoder_4to16 (
    input  wire        en,
    input  wire [3:0]  addr,
    output reg  [15:0] decode_out
);
    integer i;

    always @(*) begin
        decode_out = 16'b0;

        if (en) begin
            for (i = 0; i < 16; i = i + 1) begin
                if (addr == i[3:0]) begin
                    decode_out[i] = 1'b1;
                end
            end
        end
    end

endmodule
