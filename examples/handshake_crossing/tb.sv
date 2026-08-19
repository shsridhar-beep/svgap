module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic start = 0;
    logic request_seen;
    logic acknowledgment_seen;
    handshake_crossing dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;
    initial begin
        repeat (2) @(posedge src_clk);
        rst_n = 1;
        start = 1;
        repeat (8) @(posedge dst_clk);
        $display("FUNCTIONAL_PASS handshake_crossing");
        $finish;
    end
endmodule
