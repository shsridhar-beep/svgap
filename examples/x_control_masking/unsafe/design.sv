module x_control_masking (
    input logic clk,
    input logic [1:0] select,
    input logic a, b,
    output logic y
);
    always_ff @(posedge clk) begin
        casex (select)
            2'b0x: y <= a;
            2'b1x: y <= b;
        endcase
    end
endmodule
