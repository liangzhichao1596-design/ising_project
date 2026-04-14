from amplify import IsingPoly, SymbolGenerator
from amplify import IsingQuadraticModel
from amplify.client import FixstarsClient
from amplify import Solver

gen = SymbolGenerator(IsingPoly)  # Define Variable Variable Generator
q = gen.array(700)  # Generate a Binary array of length 2


f = 6 - q[0]*q[1] - q[1]*q[4] - q[2]*q[3] - q[3]*q[4] - q[4]*q[5] - q[6]*q[7] - q[1]*q[4]*q[6] + q[3]*q[4]*q[6]

model = IsingQuadraticModel(f)

client = FixstarsClient()
client.token = "AE/aeg4OhPovSYNQdfWsFQ2KD5xhvfkKykQ"
client.parameters.timeout = 20000    # Timeout is 5 second

solver = Solver(client)
result = solver.solve(model)
for solution in result:
    print(f"energy = {solution.energy}\nvalues = {solution.values}")