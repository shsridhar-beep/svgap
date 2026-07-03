module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic toggle = 0;
    logic dst_level;

    level_crossing dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;

    initial begin
        repeat (3) @(posedge src_clk);
        @(negedge src_clk) rst_n = 1;
        @(negedge src_clk) toggle = 1;
        @(negedge src_clk) toggle = 0;
        repeat (5) @(posedge dst_clk);
        if (dst_level !== 1'b1) $fatal(1, "level did not cross");
        $display("FUNCTIONAL_PASS level_crossing");
        $finish;
    end
endmodule
