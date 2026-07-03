module tb;
  logic clk = 0, arst_n = 0, enable = 0; logic [7:0] count;
  reset_counter dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #2 arst_n = 1; enable = 1;
    repeat (7) @(posedge clk);
    if (count === 8'hxx || count < 2) $fatal(1, "counter did not run: %0d", count);
    @(negedge clk); #2 arst_n = 0; #1;
    if (count !== 0) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_counter"); $finish;
  end
endmodule
