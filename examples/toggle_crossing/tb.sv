module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic event_in = 0;
    logic dst_toggle;
    toggle_crossing dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;
    initial begin
        repeat (2) @(posedge src_clk);
        rst_n = 1;
        @(negedge src_clk) event_in = 1;
        @(negedge src_clk) event_in = 0;
        repeat (5) @(posedge dst_clk);
        $display("FUNCTIONAL_PASS toggle_crossing");
        $finish;
    end
endmodule
