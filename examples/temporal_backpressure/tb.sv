module tb;
    logic clk = 0;
    logic rst_n = 0;
    logic s_valid = 0;
    logic [7:0] s_data = 0;
    logic s_ready;
    logic m_valid;
    logic [7:0] m_data;
    logic m_ready = 1;

    elastic_buffer dut (.*);
    always #5 clk = ~clk;

    task automatic send(input logic [7:0] value);
        @(negedge clk);
        s_valid = 1;
        s_data = value;
        @(negedge clk);
        s_valid = 0;
        if (m_valid !== 1'b1 || m_data !== value)
            $fatal(1, "transfer mismatch");
    endtask

    initial begin
        repeat (2) @(posedge clk);
        @(negedge clk) rst_n = 1;
        send(8'h35);
        send(8'hca);
        $display("FUNCTIONAL_PASS temporal_backpressure");
        $finish;
    end
endmodule
