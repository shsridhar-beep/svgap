module tb;
    logic clk = 0, rst_a_n = 0, rst_b_n = 0, data_in = 0;
    logic source_observed, destination_observed;
    reset_domain_crossing dut (.*);
    always #5 clk = ~clk;
    initial begin
        repeat (2) @(posedge clk); rst_a_n = 1; rst_b_n = 1; data_in = 1;
        repeat (3) @(posedge clk);
        $display("FUNCTIONAL_PASS reset_domain_crossing");
        $finish;
    end
endmodule
