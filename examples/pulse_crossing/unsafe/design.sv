module pulse_crossing (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic pulse_in,
    output logic dst_pulse
);
    logic src_pulse;
    logic pulse_meta;

    always_ff @(posedge src_clk) begin
        if (!rst_n) src_pulse <= 1'b0;
        else src_pulse <= pulse_in;
    end

    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            pulse_meta <= 1'b0;
            dst_pulse  <= 1'b0;
        end else begin
            pulse_meta <= src_pulse;
            dst_pulse  <= pulse_meta;
        end
    end
endmodule
