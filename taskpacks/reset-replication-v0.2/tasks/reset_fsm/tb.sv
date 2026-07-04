module tb;
  logic clk = 0, reset_n = 0, start = 0, busy, done; reset_fsm dut (.*);
  always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #3 reset_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) start = 1; @(negedge clk) start = 0;
    repeat (5) begin @(posedge clk); if (done) begin
      #2 reset_n = 0; #1;
      if (busy || done) $fatal(1, "reset did not assert asynchronously");
      $display("FUNCTIONAL_PASS reset_fsm"); $finish; end end
    $fatal(1, "done was not observed");
  end
endmodule
