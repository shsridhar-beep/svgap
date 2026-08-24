module toggle_crossing (
    input logic src_clk, dst_clk, rst_n, event_in,
    output logic dst_toggle
);
    logic src_toggle;
    logic toggle_meta;
    always_ff @(posedge src_clk) begin
        if (!rst_n) src_toggle <= 1'b0;
        else if (event_in) src_toggle <= ~src_toggle;
    end
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            toggle_meta <= 1'b0;
            dst_toggle  <= 1'b0;
        end else begin
            toggle_meta <= src_toggle;
            dst_toggle  <= toggle_meta;
        end
    end
endmodule
