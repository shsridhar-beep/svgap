module comb_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic [1:0] src_data,
    output logic dst_parity
);
    logic src_parity;
    logic dst_meta;

    // Register the combinational result before it enters the CDC path.
    always_ff @(posedge src_clk) begin
        if (!rst_n)
            src_parity <= 0;
        else
            src_parity <= src_data[0] ^ src_data[1];
    end

    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            dst_meta   <= 0;
            dst_parity <= 0;
        end else begin
            dst_meta   <= src_parity;
            dst_parity <= dst_meta;
        end
    end
endmodule
