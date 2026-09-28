module temporal_pulse_properties;
    (* anyseq *) logic clk;
    (* anyseq *) logic rst_n;
    (* anyseq *) logic trigger;
    logic pulse;
    logic f_past_valid;
    (* keep *) logic pulse_seen;

    pulse_generator dut (.*);

    always_ff @(posedge clk) begin
        pulse_seen <= f_past_valid && rst_n && pulse;
        f_past_valid <= 1'b1;
        if (!f_past_valid)
            assume (!rst_n);
        else
            assume (rst_n);
        if (f_past_valid && $past(trigger))
            assume (!trigger);
        if (f_past_valid && $past(rst_n && pulse))
            assert (!pulse);
    end
endmodule
