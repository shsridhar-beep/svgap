module gray_counter (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic enable,
    output logic [3:0] dst_count
);
    logic [3:0] src_count;
    logic [3:0] dst_meta;

    always_ff @(posedge src_clk) begin
        if (!rst_n)
            src_count <= 0;
        else if (enable)
            src_count <= src_count + 1'b1;
    end

    // Unsafe: a changing binary bus is synchronized bit-by-bit.
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            dst_meta  <= 0;
            dst_count <= 0;
        end else begin
            dst_meta  <= src_count;
            dst_count <= dst_meta;
        end
    end
endmodule
