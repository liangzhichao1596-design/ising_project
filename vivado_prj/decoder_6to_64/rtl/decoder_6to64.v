module decoder_6to64 (
    input  wire       en,
    input  wire [5:0] addr,
    output reg  [63:0] decode_out
);
    integer i;

    always @(*) begin
        decode_out = 64'b0;

        if (en) begin
            for (i = 0; i < 64; i = i + 1) begin
                if (addr == i[5:0]) begin
                    decode_out[i] = 1'b1;
                end
            end
        end
    end

endmodule
