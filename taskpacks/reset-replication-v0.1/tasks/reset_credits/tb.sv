module tb;
  logic clk = 0, async_reset_n = 0, consume = 0, replenish = 0; logic [3:0] credits;
  reset_credits dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #2 async_reset_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) replenish = 1; repeat (3) @(posedge clk);
    @(negedge clk) replenish = 0; @(negedge clk) consume = 1; @(posedge clk); #1;
    if (credits !== 2) $fatal(1, "unexpected credits %0d", credits);
    #2 async_reset_n = 0; #1;
    if (credits !== 0) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_credits"); $finish;
  end
endmodule
