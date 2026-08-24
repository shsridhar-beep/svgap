module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic data_in = 0;
    logic data_out;

    synchronizer_depth dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;

    initial begin
        repeat (2) @(posedge src_clk);
        rst_n = 1;
        data_in = 1;
        repeat (6) @(posedge dst_clk);
        if (data_out !== 1'b1) $fatal(1, "level did not cross");
        $display("FUNCTIONAL_PASS synchronizer_depth");
        $finish;
    end
endmodule
