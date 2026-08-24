module tb;
    logic clk = 0, rst_n = 0, reset_enable = 1, data_in = 0;
    logic data_out;
    reset_gating dut (.*);
    always #5 clk = ~clk;
    initial begin
        repeat (2) @(posedge clk); rst_n = 1; data_in = 1;
        repeat (2) @(posedge clk);
        if (data_out !== 1'b1) $fatal(1, "data did not propagate");
        $display("FUNCTIONAL_PASS reset_gating");
        $finish;
    end
endmodule
