module power_on_x (
    input  logic clk,
    input  logic rst_n,
    input  logic load,
    input  logic mode_in,
    input  logic data_in,
    output logic data_out
);
    logic mode;

    // The nominal test initializes mode through load before relying on it, but
    // the declared power-on contract requires reset coverage.
    always_ff @(posedge clk) begin
        if (load)
            mode <= mode_in;
    end

    // Four-state simulation takes the else branch when mode is X. That nominal
    // behavior hides the alternative silicon power-on value mode=1.
    always_comb begin
        if (mode)
            data_out = data_in;
        else
            data_out = 1'b0;
    end
endmodule
