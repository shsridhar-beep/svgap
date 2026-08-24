module tb;
    logic clk = 0;
    logic rst_n = 0;
    logic trigger = 0;
    logic pulse;

    pulse_generator dut (.*);
    always #5 clk = ~clk;

    initial begin
        repeat (2) @(posedge clk);
        @(negedge clk) rst_n = 1;
        @(negedge clk) trigger = 1;
        @(negedge clk) trigger = 0;
        @(posedge clk);
        if (pulse !== 1'b1)
            $fatal(1, "pulse was not observed");
        // This ordinary smoke test stops at first success and never checks the
        // deassertion cycle.
        $display("FUNCTIONAL_PASS temporal_pulse");
        $finish;
    end
endmodule
