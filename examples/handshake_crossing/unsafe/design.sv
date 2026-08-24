module handshake_crossing (
    input logic src_clk, dst_clk, rst_n, start,
    output logic request_seen,
    output logic acknowledgment_seen
);
    logic src_request;
    logic request_meta;
    logic request_sync;
    logic dst_ack;

    always_ff @(posedge src_clk) begin
        if (!rst_n) src_request <= 1'b0;
        else src_request <= start;
    end
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            request_meta <= 1'b0;
            request_sync <= 1'b0;
            dst_ack      <= 1'b0;
        end else begin
            request_meta <= src_request;
            request_sync <= request_meta;
            dst_ack      <= request_sync;
        end
    end
    assign request_seen = request_sync;
    assign acknowledgment_seen = 1'b0;
endmodule
