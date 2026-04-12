module decoder_8to256 (
    input  wire        en,
    input  wire [7:0]  addr,
    output reg  [255:0] decode_out
);
    integer i;

    always @(*) begin
        decode_out = 256'b0;

        if (en) begin
            for (i = 0; i < 256; i = i + 1) begin
                if (addr == i[7:0]) begin
                    decode_out[i] = 1'b1;
                end
            end
        end
    end

endmodule
