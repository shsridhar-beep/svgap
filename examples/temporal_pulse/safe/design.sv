module pulse_generator (
    input  logic clk,
    input  logic rst_n,
    input  logic trigger,
    output logic pulse
);
    always_ff @(posedge clk) begin
        if (!rst_n)
            pulse <= 1'b0;
        else
            pulse <= trigger;
    end
endmodule
