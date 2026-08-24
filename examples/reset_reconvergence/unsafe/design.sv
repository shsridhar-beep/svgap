module reset_reconvergence (
    input logic clk, rst_a_n, rst_b_n, data_in,
    output logic data_out
);
    logic combined_rst_n;
    assign combined_rst_n = rst_a_n & rst_b_n;
    always_ff @(posedge clk or negedge combined_rst_n) begin
        if (!combined_rst_n) data_out <= 1'b0;
        else data_out <= data_in;
    end
endmodule
