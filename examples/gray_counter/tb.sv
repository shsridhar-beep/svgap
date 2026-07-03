module tb;
    logic src_clk = 0;
    logic dst_clk = 0;
    logic rst_n = 0;
    logic enable = 0;
    logic [3:0] dst_count;

    gray_counter dut (.*);
    always #5 src_clk = ~src_clk;
    always #7 dst_clk = ~dst_clk;

    initial begin
        repeat (3) @(posedge src_clk);
        @(negedge src_clk) begin
            rst_n = 1;
            enable = 1;
        end
        repeat (3) @(posedge src_clk);
        @(negedge src_clk) enable = 0;
        repeat (6) @(posedge dst_clk);
        if (dst_count !== 4'd3) $fatal(1, "expected stable count 3, got %0d", dst_count);
        $display("FUNCTIONAL_PASS gray_counter value=%h", dst_count);
        $finish;
    end
endmodule
