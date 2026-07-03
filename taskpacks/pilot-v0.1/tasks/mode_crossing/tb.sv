module tb;
    logic cfg_clk = 0, core_clk = 0, rst_n = 0, set_mode = 0, mode_in = 0;
    logic core_mode;
    mode_crossing dut (.*);
    always #4 cfg_clk = ~cfg_clk;
    always #7 core_clk = ~core_clk;
    initial begin
        repeat (3) @(posedge cfg_clk);
        @(negedge cfg_clk) begin rst_n = 1; set_mode = 1; mode_in = 1; end
        @(negedge cfg_clk) set_mode = 0;
        repeat (5) @(posedge core_clk);
        if (core_mode !== 1'b1) $fatal(1, "mode did not cross");
        $display("FUNCTIONAL_PASS mode_crossing");
        $finish;
    end
endmodule
