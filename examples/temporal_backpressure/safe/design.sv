module elastic_buffer (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       s_valid,
    input  logic [7:0] s_data,
    output logic       s_ready,
    output logic       m_valid,
    output logic [7:0] m_data,
    input  logic       m_ready
);
    assign s_ready = !m_valid || m_ready;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            m_valid <= 1'b0;
            m_data <= '0;
        end else if (s_ready) begin
            m_valid <= s_valid;
            if (s_valid)
                m_data <= s_data;
        end
    end
endmodule
