module tb;
  logic clk = 0, system_rst_n = 0, kick = 0, timeout; reset_watchdog dut (.*);
  always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #2 system_rst_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) kick = 1; @(negedge clk) kick = 0;
    repeat (6) begin @(posedge clk); if (timeout) begin
      #2 system_rst_n = 0; #1;
      if (timeout) $fatal(1, "reset did not assert asynchronously");
      $display("FUNCTIONAL_PASS reset_watchdog"); $finish; end end
    $fatal(1, "timeout was not observed");
  end
endmodule
