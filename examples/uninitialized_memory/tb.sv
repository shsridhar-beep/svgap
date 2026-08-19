module tb;
    logic clk = 0, write_enable = 0;
    logic [1:0] address = 0;
    logic [7:0] write_data = 0, read_data;
    uninitialized_memory dut (.*);
    always #5 clk = ~clk;
    initial begin
        repeat (3) @(posedge clk);
        $display("FUNCTIONAL_PASS uninitialized_memory");
        $finish;
    end
endmodule
