module tb;
  logic clk = 0, global_reset_n = 0, write_en = 0; logic [3:0] config_in = 0, config_out;
  reset_config dut (.*); always #5 clk = ~clk;
  initial begin
    repeat (2) @(posedge clk); #3 global_reset_n = 1; repeat (3) @(posedge clk);
    @(negedge clk) begin write_en = 1; config_in = 4'ha; end
    @(posedge clk); #1; if (config_out !== 4'ha) $fatal(1, "write failed");
    #2 global_reset_n = 0; #1;
    if (config_out !== 0) $fatal(1, "reset did not assert asynchronously");
    $display("FUNCTIONAL_PASS reset_config"); $finish;
  end
endmodule
