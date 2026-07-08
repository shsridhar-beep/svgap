module tb;
    parameter logic SEED_BIT = 1'b1;
    parameter logic EXPECTED = 1'b0;
    logic clk = 0;
    logic rst_n = 1;
    logic load = 0;
    logic mode_in = 0;
    logic data_in = 1;
    logic data_out;

    power_on_x dut (.*);
    always #5 clk = ~clk;

    initial begin
        // Declared perturbation: choose a concrete power-on value for the
        // state element, then assert the external reset before any clock edge.
        #1 dut.mode = SEED_BIT;
        #1 rst_n = 0;
        #1;
        if (data_out !== EXPECTED)
            $fatal(1, "perturbed observation=%0b expected=%0b", data_out, EXPECTED);
        $display("PERTURBATION_PASS seed=%0b observation=%0b", SEED_BIT, data_out);
        $finish;
    end
endmodule
