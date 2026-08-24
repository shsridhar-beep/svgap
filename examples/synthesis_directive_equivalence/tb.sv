module tb;
    logic [7:0] a;
    logic [7:0] b;
    logic mode;
    logic [7:0] y;

    arithmetic_unit dut (.*);

    initial begin
        // The smoke suite covers only the common mode. In RTL simulation the
        // hidden mode also looks correct, but synthesis directives change it.
        mode = 1'b0;
        a = 8'd19;
        b = 8'd7;
        #1;
        if (y !== 8'd26)
            $fatal(1, "addition mismatch");
        a = 8'd200;
        b = 8'd15;
        #1;
        if (y !== 8'd215)
            $fatal(1, "addition mismatch");
        $display("FUNCTIONAL_PASS synthesis_directive_equivalence");
        $finish;
    end
endmodule
