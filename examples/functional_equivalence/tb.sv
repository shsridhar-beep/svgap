module tb;
    logic [7:0] a;
    logic [7:0] b;
    logic [1:0] op;
    logic [7:0] y;

    tiny_alu dut (.*);

    task automatic check(
        input logic [1:0] operation,
        input logic [7:0] expected
    );
        op = operation;
        #1;
        if (y !== expected)
            $fatal(1, "operation %0d mismatch", operation);
    endtask

    initial begin
        a = 8'h35;
        b = 8'h0f;
        check(2'd0, 8'h44);
        check(2'd1, 8'h26);
        check(2'd2, 8'h05);
        // Opcode 3 is absent from this finite functional suite.
        $display("FUNCTIONAL_PASS functional_equivalence");
        $finish;
    end
endmodule
