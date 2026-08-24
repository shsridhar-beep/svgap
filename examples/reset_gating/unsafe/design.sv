module reset_gating (
    input logic clk, rst_n, reset_enable, data_in,
    output logic data_out
);
    logic gated_rst_n;
    assign gated_rst_n = rst_n & reset_enable;
    always_ff @(posedge clk or negedge gated_rst_n) begin
        if (!gated_rst_n) data_out <= 1'b0;
        else data_out <= data_in;
    end
endmodule
