module arithmetic_unit (
    input  logic [7:0] a,
    input  logic [7:0] b,
    input  logic       mode,
    output logic [7:0] y
);
    always_comb begin
        if (mode)
            y = a - b;
        else
            y = a + b;
    end
endmodule
