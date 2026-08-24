module tb;
    logic wr_clk = 0, rd_clk = 0, rst_n = 0;
    logic [2:0] wr_pointer_seen, rd_pointer_seen;
    async_fifo_shape dut (.*);
    always #5 wr_clk = ~wr_clk;
    always #7 rd_clk = ~rd_clk;
    initial begin
        repeat (2) @(posedge wr_clk); rst_n = 1;
        repeat (7) @(posedge rd_clk);
        $display("FUNCTIONAL_PASS async_fifo_shape");
        $finish;
    end
endmodule
