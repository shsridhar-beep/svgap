module pulse_generator (
    input  logic clk,
    input  logic rst_n,
    input  logic trigger,
    output logic pulse
);
    logic hold_one_more;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            pulse <= 1'b0;
            hold_one_more <= 1'b0;
        end else begin
            pulse <= trigger || hold_one_more;
            hold_one_more <= trigger;
        end
    end
endmodule
