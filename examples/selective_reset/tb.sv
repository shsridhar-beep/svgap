module tb;
    logic clk = 0, rst_n = 0, enable = 0;
    logic [1:0] mode;
    selective_reset dut (.*);
    always #5 clk = ~clk;
    initial begin
        repeat (2) @(posedge clk); rst_n = 1;
        repeat (2) @(posedge clk);
        $display("FUNCTIONAL_PASS selective_reset");
        $finish;
    end
endmodule
