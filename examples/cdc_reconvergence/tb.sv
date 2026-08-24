module tb;
    logic src_clk = 0, dst_clk = 0, rst_n = 0, a_in = 0, b_in = 0;
    logic y_a, y_b;
    cdc_reconvergence dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;
    initial begin
        repeat (2) @(posedge src_clk); rst_n = 1; a_in = 1; b_in = 1;
        repeat (5) @(posedge dst_clk);
        $display("FUNCTIONAL_PASS cdc_reconvergence");
        $finish;
    end
endmodule
