module tb;
  logic clk = 0, rst_n = 0, set_fault = 0, clear_fault = 0, fault_latched;
  reset_status dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #4 rst_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) set_fault = 1; @(negedge clk) set_fault = 0;
    @(posedge clk); if (!fault_latched) $fatal(1, "fault not latched");
    @(negedge clk) clear_fault = 1; @(posedge clk); #1;
    if (fault_latched) $fatal(1, "fault not cleared");
    @(negedge clk) begin clear_fault = 0; set_fault = 1; end
    @(posedge clk); #1; if (!fault_latched) $fatal(1, "second set failed");
    #2 rst_n = 0; #1;
    if (fault_latched) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_status"); $finish;
  end
endmodule
