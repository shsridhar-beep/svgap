module cdc_reconvergence (
    input logic src_clk, dst_clk, rst_n, a_in, b_in,
    output logic y_a,
    output logic y_b
);
    logic a_src, b_src;
    logic a_meta, a_sync;
    logic b_meta, b_sync;
    always_ff @(posedge src_clk) begin
        if (!rst_n) a_src <= 1'b0;
        else a_src <= a_in;
    end
    always_ff @(posedge src_clk) begin
        if (!rst_n) b_src <= 1'b0;
        else b_src <= b_in;
    end
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin a_meta <= 0; a_sync <= 0; end
        else begin a_meta <= a_src; a_sync <= a_meta; end
    end
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin b_meta <= 0; b_sync <= 0; end
        else begin b_meta <= b_src; b_sync <= b_meta; end
    end
    assign y_a = a_sync;
    assign y_b = b_sync;
endmodule
