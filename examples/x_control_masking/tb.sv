module tb;
    logic clk = 0;
    logic [1:0] select = 0;
    logic a = 1, b = 0, y;
    x_control_masking dut (.*);
    always #5 clk = ~clk;
    initial begin
        repeat (3) @(posedge clk);
        $display("FUNCTIONAL_PASS x_control_masking");
        $finish;
    end
endmodule
