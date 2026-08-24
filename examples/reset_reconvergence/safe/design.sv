module reset_reconvergence (
    input logic clk, rst_a_n, rst_b_n, data_in,
    output logic data_out
);
    always_ff @(posedge clk or negedge rst_a_n) begin
        if (!rst_a_n) data_out <= 1'b0;
        else data_out <= data_in;
    end
endmodule
