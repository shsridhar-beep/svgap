module selective_reset (
    input logic clk, rst_n, enable,
    output logic [1:0] mode
);
    always_ff @(posedge clk) begin
        if (!rst_n) mode <= 2'b01;
        else if (enable) mode <= mode + 1'b1;
    end
endmodule
