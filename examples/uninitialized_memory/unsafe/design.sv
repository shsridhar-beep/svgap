module uninitialized_memory (
    input logic clk, write_enable,
    input logic [1:0] address,
    input logic [7:0] write_data,
    output logic [7:0] read_data
);
    logic [7:0] memory [0:3];
    always_ff @(posedge clk) begin
        if (write_enable) memory[address] <= write_data;
        read_data <= memory[address];
    end
endmodule
