module reset_domain_crossing (
    input logic clk, rst_a_n, rst_b_n, data_in,
    output logic source_observed,
    output logic destination_observed
);
    logic source_state;
    logic destination_state;
    always_ff @(posedge clk or negedge rst_a_n) begin
        if (!rst_a_n) source_state <= 1'b0;
        else source_state <= data_in;
    end
    always_ff @(posedge clk or negedge rst_b_n) begin
        if (!rst_b_n) destination_state <= 1'b0;
        else destination_state <= data_in;
    end
    assign source_observed = source_state;
    assign destination_observed = destination_state;
endmodule
