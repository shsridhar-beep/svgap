module tb;
    logic clk = 0;
    logic rst_n = 0;
    logic start = 0;
    logic done;

    response_engine dut (.*);
    always #5 clk = ~clk;

    initial begin
        repeat (2) @(posedge clk);
        @(negedge clk) rst_n = 1;
        @(negedge clk) start = 1;
        @(negedge clk) start = 0;
        repeat (8) begin
            @(posedge clk);
            if (done) begin
                $display("FUNCTIONAL_PASS temporal_response");
                $finish;
            end
        end
        $fatal(1, "done was never observed");
    end
endmodule
