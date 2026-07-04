module tb;
  logic clk = 0, por_n = 0, load = 0; logic [3:0] load_value = 0; logic expired;
  reset_timer dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #1 por_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) begin load = 1; load_value = 3; end
    @(negedge clk) load = 0; repeat (5) @(posedge clk);
    if (expired !== 1'b1) $fatal(1, "timer did not expire");
    @(negedge clk); #2 por_n = 0; #1;
    if (expired !== 0) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_timer"); $finish;
  end
endmodule
