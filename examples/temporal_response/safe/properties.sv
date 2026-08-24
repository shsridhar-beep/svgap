module temporal_response_properties;
    (* anyseq *) logic clk;
    (* anyseq *) logic rst_n;
    (* anyseq *) logic start;
    logic done;
    logic f_past_valid;
    logic pending;
    logic [2:0] age;

    response_engine dut (.*);

    always_ff @(posedge clk) begin
        f_past_valid <= 1'b1;
        if (!f_past_valid)
            assume (!rst_n);
        else
            assume (rst_n);
        if (pending)
            assume (!start);

        if (!rst_n) begin
            pending <= 1'b0;
            age <= '0;
        end else if (start && !pending) begin
            pending <= 1'b1;
            age <= '0;
        end else if (pending && done) begin
            pending <= 1'b0;
        end else if (pending) begin
            assert (age < 3);
            age <= age + 1'b1;
        end
    end
endmodule
