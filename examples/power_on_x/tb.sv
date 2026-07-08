module tb;
    logic clk = 0;
    logic rst_n = 0;
    logic load = 0;
    logic mode_in = 0;
    logic data_in = 1;
    logic data_out;

    power_on_x dut (.*);
    always #5 clk = ~clk;

    initial begin
        repeat (2) @(posedge clk);
        if (data_out !== 1'b0)
            $fatal(1, "nominal reset observation differed");
        rst_n = 1;
        @(negedge clk);
        load = 1;
        mode_in = 1;
        data_in = 1;
        @(posedge clk);
        #1;
        load = 0;
        if (data_out !== 1'b1)
            $fatal(1, "loaded mode was not observed");
        $display("FUNCTIONAL_PASS power_on_x data_out=%0b", data_out);
        $finish;
    end
endmodule
