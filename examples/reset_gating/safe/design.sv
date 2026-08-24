module reset_gating (
    input logic clk, rst_n, reset_enable, data_in,
    output logic data_out
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) data_out <= 1'b0;
        else data_out <= data_in;
    end
endmodule
