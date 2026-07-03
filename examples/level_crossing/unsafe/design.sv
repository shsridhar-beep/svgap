module level_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic toggle,
    output logic dst_level
);
    logic src_level;

    always_ff @(posedge src_clk) begin
        if (!rst_n)
            src_level <= 1'b0;
        else if (toggle)
            src_level <= ~src_level;
    end

    // Unsafe: the destination consumes the asynchronous level directly.
    always_ff @(posedge dst_clk) begin
        if (!rst_n)
            dst_level <= 1'b0;
        else
            dst_level <= src_level;
    end
endmodule
