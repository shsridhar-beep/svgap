module temporal_backpressure_properties;
    (* anyseq *) logic clk;
    (* anyseq *) logic rst_n;
    (* anyseq *) logic s_valid;
    (* anyseq *) logic [7:0] s_data;
    (* anyseq *) logic m_ready;
    logic s_ready;
    logic m_valid;
    logic [7:0] m_data;
    logic f_past_valid;

    elastic_buffer dut (.*);

    always_ff @(posedge clk) begin
        f_past_valid <= 1'b1;
        if (!f_past_valid)
            assume (!rst_n);
        else
            assume (rst_n);
        if (f_past_valid && $past(rst_n && m_valid && !m_ready)) begin
            assert (m_valid);
            assert (m_data == $past(m_data));
        end
    end
endmodule
