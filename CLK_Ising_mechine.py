from amplify import IsingPoly, SymbolGenerator
from amplify import IsingQuadraticModel
from amplify.client import FixstarsClient
from amplify import Solver
import numpy as np

client = FixstarsClient()
client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
client.parameters.timeout = 40000    # Timeout is 5 second
solver = Solver(client)

gen = SymbolGenerator(IsingPoly)  # Define Variable Variable Generator
q = gen.array(77)  # Generate a Binary array of length 2
num_steps = 5


q[2] = 1
q[5] = -1
q[76] = 1

result_2d_array = []

#input signal
clk_signal = [-1, -1, 1, 1, 1]
read_signal = [1, -1, 1, 1, 1]
write_signal = [-1, -1, -1, -1, -1]
din_signal = [1, 1, 1, 1, 1]
for t in range(num_steps):
    q[0] = clk_signal[t]
    q[2] = din_signal[t]
    q[6] = read_signal[t]
    q[9] = write_signal[t]
    if t - 1 < 0:
        q[1] = -1
    else:
        q[1] = clk_signal[t - 1]
    f = (2 * q[8] * q[11]) + (q[0]*q[11] - 2*q[0]*q[12] - 2*q[11]*q[12] + q[0] + q[11] - 2*q[12]) + (2 * q[7] * q[13]) + (q[6]*q[13] - 2*q[6]*q[14] - 2*q[13]*q[14] + q[6] + q[13] - 2*q[14]) + (q[12]*q[14] - 2*q[12]*q[15] - 2*q[14]*q[15] - q[12] - q[14] + 2*q[15]) + (2 * q[7] * q[16]) + (q[8]*q[16] - 2*q[8]*q[17] - 2*q[16]*q[17] + q[8] + q[16] - 2*q[17]) + (q[15]*q[17] - 2*q[15]*q[18] - 2*q[17]*q[18] - q[15] - q[17] + 2*q[18]) + (2 * q[10] * q[19]) + (q[8]*q[19] - 2*q[8]*q[20] - 2*q[19]*q[20] + q[8] + q[19] - 2*q[20]) + (q[18]*q[20] - 2*q[18]*q[21] - 2*q[20]*q[21] - q[18] - q[20] + 2*q[21]) + (2 * q[10] * q[22]) + (q[9]*q[22] - 2*q[9]*q[23] - 2*q[22]*q[23] + q[9] + q[22] - 2*q[23]) + (q[21]*q[23] - 2*q[21]*q[24] - 2*q[23]*q[24] - q[21] - q[23] + 2*q[24]) + (2 * q[1] * q[25]) + (2 * q[8] * q[26]) + (q[25]*q[26] - 2*q[25]*q[27] - 2*q[26]*q[27] + q[25] + q[26] - 2*q[27]) + (q[24]*q[27] - 2*q[24]*q[28] - 2*q[27]*q[28] - q[24] - q[27] + 2*q[28]) + (2 * q[7] * q[29]) + (2 * q[10] * q[30]) + (q[29]*q[30] - 2*q[29]*q[31] - 2*q[30]*q[31] + q[29] + q[30] - 2*q[31]) + (q[28]*q[31] - 2*q[28]*q[32] - 2*q[31]*q[32] - q[28] - q[31] + 2*q[32]) + (q[1]*q[8] - 2*q[1]*q[33] - 2*q[8]*q[33] + q[1] + q[8] - 2*q[33]) + (2 * q[0] * q[34]) + (q[33]*q[34] - 2*q[33]*q[35] - 2*q[34]*q[35] + q[33] + q[34] - 2*q[35]) + (q[32]*q[35] - 2*q[32]*q[36] - 2*q[35]*q[36] - q[32] - q[35] + 2*q[36]) + (2 * q[4] * q[37]) + (q[2]*q[37] - 2*q[2]*q[38] - 2*q[37]*q[38] + q[2] + q[37] - 2*q[38]) + (2 * q[10] * q[39]) + (q[38]*q[39] - 2*q[38]*q[40] - 2*q[39]*q[40] + q[38] + q[39] - 2*q[40]) + (q[36]*q[40] - 2*q[36]*q[41] - 2*q[40]*q[41] - q[36] - q[40] + 2*q[41]) + (2 * q[4] * q[42]) + (q[3]*q[42] - 2*q[3]*q[43] - 2*q[42]*q[43] + q[3] + q[42] - 2*q[43]) + (2 * q[7] * q[44]) + (q[43]*q[44] - 2*q[43]*q[45] - 2*q[44]*q[45] + q[43] + q[44] - 2*q[45]) + (q[41]*q[45] - 2*q[41]*q[46] - 2*q[45]*q[46] - q[41] - q[45] + 2*q[46]) + (2 * q[2] * q[47]) + (q[4]*q[47] - 2*q[4]*q[48] - 2*q[47]*q[48] + q[4] + q[47] - 2*q[48]) + (2 * q[10] * q[49]) + (q[48]*q[49] - 2*q[48]*q[50] - 2*q[49]*q[50] + q[48] + q[49] - 2*q[50]) + (q[46]*q[50] - 2*q[46]*q[51] - 2*q[50]*q[51] - q[46] - q[50] + 2*q[51]) + (2 * q[3] * q[52]) + (q[4]*q[52] - 2*q[4]*q[53] - 2*q[52]*q[53] + q[4] + q[52] - 2*q[53]) + (2 * q[7] * q[54]) + (q[53]*q[54] - 2*q[53]*q[55] - 2*q[54]*q[55] + q[53] + q[54] - 2*q[55]) + (q[51]*q[55] - 2*q[51]*q[56] - 2*q[55]*q[56] - q[51] - q[55] + 2*q[56]) + (2 * q[6] * q[57]) + (q[7]*q[57] - 2*q[7]*q[58] - 2*q[57]*q[58] + q[7] + q[57] - 2*q[58]) + (2 * q[8] * q[59]) + (q[58]*q[59] - 2*q[58]*q[60] - 2*q[59]*q[60] + q[58] + q[59] - 2*q[60]) + (q[56]*q[60] - 2*q[56]*q[61] - 2*q[60]*q[61] - q[56] - q[60] + 2*q[61]) + (2 * q[8] * q[62]) + (q[10]*q[62] - 2*q[10]*q[63] - 2*q[62]*q[63] + q[10] + q[62] - 2*q[63]) + (2 * q[9] * q[64]) + (q[63]*q[64] - 2*q[63]*q[65] - 2*q[64]*q[65] + q[63] + q[64] - 2*q[65]) + (q[61]*q[65] - 2*q[61]*q[66] - 2*q[65]*q[66] - q[61] - q[65] + 2*q[66]) + (q[4]*q[7] - 2*q[4]*q[67] - 2*q[7]*q[67] + q[4] + q[7] - 2*q[67]) + (q[67]*q[10] - 2*q[67]*q[68] - 2*q[10]*q[68] + q[67] + q[10] - 2*q[68]) + (2 * q[5] * q[69]) + (q[68]*q[69] - 2*q[68]*q[70] - 2*q[69]*q[70] + q[68] + q[69] - 2*q[70]) + (q[66]*q[70] - 2*q[66]*q[71] - 2*q[70]*q[71] - q[66] - q[70] + 2*q[71]) + (q[5]*q[7] - 2*q[5]*q[72] - 2*q[7]*q[72] + q[5] + q[7] - 2*q[72]) + (q[72]*q[10] - 2*q[72]*q[73] - 2*q[10]*q[73] + q[72] + q[10] - 2*q[73]) + (2 * q[4] * q[74]) + (q[73]*q[74] - 2*q[73]*q[75] - 2*q[74]*q[75] + q[73] + q[74] - 2*q[75]) + (q[71]*q[75] - 2*q[71]*q[76] - 2*q[75]*q[76] - q[71] - q[75] + 2*q[76])

    model = IsingQuadraticModel(f)
    result = solver.solve(model)
    for solution in result:
        #print(f"energy = {solution.energy}\nvalues = {solution.values}")
        decoded = q.decode(solution.values)
        q[5] = decoded[4]
        final_arr = np.concatenate( [np.array([solution.energy]), decoded] )
        result_2d_array.append(final_arr)

result_2d = np.array(result_2d_array)
result_2d_T = result_2d.T
print("转置后的最终二维数组：")
print(result_2d_T)