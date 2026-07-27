module comb_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic [1:0] src_data,
    output logic dst_parity
);
    logic src_a, src_b;
    logic dst_meta;
    wire parity_comb = src_a ^ src_b;

    always_ff @(posedge src_clk) begin
        if (!rst_n) begin
            src_a <= 0;
            src_b <= 0;
        end else begin
            src_a <= src_data[0];
            src_b <= src_data[1];
        end
    end

    // Unsafe: independently changing source flops feed combinational logic
    // immediately before the first synchronizer stage.
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            dst_meta   <= 0;
            dst_parity <= 0;
        end else begin
            dst_meta   <= parity_comb;
            dst_parity <= dst_meta;
        end
    end
endmodule
