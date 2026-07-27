module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic [1:0] src_data = 0;
    logic dst_parity;

    comb_crossing dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;

    initial begin
        repeat (3) @(posedge src_clk);
        rst_n = 1;
        src_data = 2'b01;
        repeat (3) @(posedge src_clk);
        repeat (5) @(posedge dst_clk);
        if (dst_parity !== 1'b1) $fatal(1, "parity did not cross");
        $display("FUNCTIONAL_PASS comb_crossing");
        $finish;
    end
endmodule
