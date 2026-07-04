module tb;
  logic clk = 0, ext_rst_n = 0, event_valid = 0; logic [7:0] event_count;
  reset_events dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #1 ext_rst_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) event_valid = 1; repeat (4) @(posedge clk);
    @(negedge clk) event_valid = 0; #1;
    if (event_count !== 4) $fatal(1, "unexpected count %0d", event_count);
    #2 ext_rst_n = 0; #1;
    if (event_count !== 0) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_events"); $finish;
  end
endmodule
