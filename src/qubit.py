from qiskit import QuantumCircuit, ClassicalRegister
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from collections import deque

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

    return graph


def find_best_path(graph, start, end):
    """
    use BFS algorithm to find path
    """
    queue = deque([start])
    backward = {start: None}
    while queue:
        # get the first of queue
        curr = queue.popleft()

        # find end return path
        if curr == end:
            path = []
            # backward the path
            while curr is not None:
                path.append(curr)
                curr = backward[curr]
            # reserve the path
            return path[::-1]
        
        # traverse node's nieghbor
        for nieghbor in graph[curr]:
            # dont go back
            if nieghbor not in backward:
                backward[nieghbor] = curr
                queue.append(nieghbor)
    
    return []


if __name__ == "__main__":

    # generate path of circuit
    L = 5
    num_qubit = 2 * L + 2
    ladder_graph = create_ladder_node(L)
    start_node = 0
    end_node = L
    dynamic_path = find_best_path(ladder_graph, start_node, end_node)
    print(f"plan path: {dynamic_path}")

    final_qc = create_circuit(num_qubit, dynamic_path)
    # measure qubit
    cr = ClassicalRegister(2, 'meas')
    final_qc.add_register(cr)
    final_qc.measure(dynamic_path[0], 0)
    final_qc.measure(dynamic_path[-1], 1)

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