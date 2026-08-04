module tb;
    logic clk = 0;
    logic arst_n = 0;
    logic enable = 0;
    logic [3:0] count;

    reset_release dut (.*);
    always #5 clk = ~clk;

    initial begin
        repeat (2) @(posedge clk);
        #2 arst_n = 1;
        enable = 1;
        repeat (6) @(posedge clk);
        if (count === 4'bxxxx || count == 0)
            $fatal(1, "counter did not leave reset");
        @(negedge clk);
        #2 arst_n = 0;
        #1;
        if (count !== 0)
            $fatal(1, "reset did not assert asynchronously");
        $display("FUNCTIONAL_PASS reset_release count=%0d", count);
        $finish;
    end
endmodule
