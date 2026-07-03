module tb;
    logic sensor_clk = 0, mgmt_clk = 0, rst_n = 0;
    logic temp_high = 0, voltage_low = 0, mgmt_alarm;
    alarm_crossing dut (.*);
    always #5 sensor_clk = ~sensor_clk;
    always #8 mgmt_clk = ~mgmt_clk;
    initial begin
        repeat (3) @(posedge sensor_clk);
        @(negedge sensor_clk) begin rst_n = 1; temp_high = 1; voltage_low = 1; end
        repeat (3) @(posedge sensor_clk);
        repeat (5) @(posedge mgmt_clk);
        if (mgmt_alarm !== 1'b1) $fatal(1, "alarm did not cross");
        $display("FUNCTIONAL_PASS alarm_crossing");
        $finish;
    end
endmodule
