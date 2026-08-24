module arithmetic_unit (
    input  logic [7:0] a,
    input  logic [7:0] b,
    input  logic       mode,
    output logic [7:0] y
);
    always_comb begin
        y = a + b;
        // synopsys translate_off
        if (mode)
            y = a - b;
        // synopsys translate_on
    end
endmodule
