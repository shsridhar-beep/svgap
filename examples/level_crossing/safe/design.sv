module level_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic toggle,
    output logic dst_level
);
    logic src_level;
    logic dst_meta;

    always_ff @(posedge src_clk) begin
        if (!rst_n)
            src_level <= 1'b0;
        else if (toggle)
            src_level <= ~src_level;
    end

    // Safe reference shape for a stable single-bit level: two destination flops.
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            dst_meta  <= 1'b0;
            dst_level <= 1'b0;
        end else begin
            dst_meta  <= src_level;
            dst_level <= dst_meta;
        end
    end
endmodule
