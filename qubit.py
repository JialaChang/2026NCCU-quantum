from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt

def create_circuit(num: int, path: list[int]):
    """
    num is the number of qubits\n
    path determine how to build connect by swap
    """
    # create qubits
    qc = QuantumCircuit(num)
    start_node = path[0]
    next_node = path[1]
    # add H gate in start node
    qc.h(start_node)
    # add CNOT in next node control by start node
    qc.cx(start_node, next_node)
    # swap qubit
    for i in range(1, len(path) - 1):
        qc.swap(path[i], path[i + 1])

    return qc


def create_ladder_node(L: int):
    """
    L is the length of circuit
    """
    #  1  -  2  -  3  ---  L   - L+1
    #        |     |       |
    # L+2 - L+3 - L+4 --- 2L+1 - 2L+2

    # init the dict
    graph = {}
    total_nodes = 2 * L + 2
    for i in range(total_nodes):
        graph[i] = []

    # connect horizontal line
    for i in range(L):
        # upper conn
        graph[i].append(i + 1)
        graph[i + 1].append(i)
        # lower conn
        graph[i + L + 1].append(i + L + 2)
        graph[i + L + 2].append(i + L + 1)
    
    # connect vertical line
    # first and last no connect
    for i in range(1, L):
        graph[i].append(i + L + 1)
        graph[i + L + 1].append(i)


if __name__ == "__main__":

    circuit_path = [0, 1, 7, 8, 9, 3, 4, 5]
    final_qc = create_circuit(12, circuit_path)
    # measure qubit
    final_qc.measure_all()

    # quantum simulator 
    simulator = AerSimulator()
    job = simulator.run(final_qc, shots=1024)  # run n times
    result = job.result()
    # output text
    counts = result.get_counts()
    print(f"output: {counts}")
    # output picture
    final_qc.draw('mpl')
    plt.show()