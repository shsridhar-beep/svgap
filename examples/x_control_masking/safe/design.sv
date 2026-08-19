module x_control_masking (
    input logic clk,
    input logic [1:0] select,
    input logic a, b,
    output logic y
);
    always_ff @(posedge clk) begin
        case (select)
            2'b00: y <= a;
            2'b01: y <= b;
            default: y <= 1'b0;
        endcase
    end
endmodule
