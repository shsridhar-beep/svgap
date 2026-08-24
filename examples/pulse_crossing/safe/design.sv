module pulse_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic pulse_in,
    output logic dst_pulse
);
    logic src_toggle;
    logic toggle_meta;
    logic toggle_sync;
    logic toggle_delay;

    always_ff @(posedge src_clk) begin
        if (!rst_n) src_toggle <= 1'b0;
        else if (pulse_in) src_toggle <= ~src_toggle;
    end

    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            toggle_meta  <= 1'b0;
            toggle_sync  <= 1'b0;
            toggle_delay <= 1'b0;
        end else begin
            toggle_meta  <= src_toggle;
            toggle_sync  <= toggle_meta;
            toggle_delay <= toggle_sync;
        end
    end

    assign dst_pulse = toggle_sync ^ toggle_delay;
endmodule
