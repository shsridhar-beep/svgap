module toggle_crossing (
    input logic src_clk, dst_clk, rst_n, event_in,
    output logic dst_toggle
);
    logic src_level;
    logic level_meta;
    always_ff @(posedge src_clk) begin
        if (!rst_n) src_level <= 1'b0;
        else src_level <= event_in;
    end
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            level_meta <= 1'b0;
            dst_toggle <= 1'b0;
        end else begin
            level_meta <= src_level;
            dst_toggle <= level_meta;
        end
    end
endmodule
