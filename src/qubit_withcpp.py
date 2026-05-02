import os
import sys
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, ClassicalRegister


# =========================================================
# 環境設定與 C++ 量子模擬引擎載入
# =========================================================
def setup_environment():
    """
    設定 Windows DLL 搜尋路徑並動態載入 C++ 編譯模組
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        os.add_dll_directory(current_dir)
    except AttributeError:
        os.environ['PATH'] = current_dir + os.pathsep + os.environ['PATH']

    msys_path = r"C:\msys64\mingw64\bin"
    if os.path.exists(msys_path):
        try:
            os.add_dll_directory(msys_path)
        except AttributeError:
            pass

    try:
        import quantum_cpp  # type: ignore
        return quantum_cpp
    except ImportError as e:
        print(f"[Error] Failed to load C++ module: {e}")
        sys.exit(1)

quantum_cpp = setup_environment()


# =========================================================
# 硬體拓樸建立與尋路演算法
# =========================================================
def create_ladder_node(L: int):
    """
    建立雙腳梯形 (Ladder) 拓樸圖結構。
    L 為單側電路長度，總量子位元數為 2L + 2。
    """
    # 初始化圖結構字典
    graph = {i: [] for i in range(2 * L + 2)}
    
    # 建立水平連線 (上排與下排)
    for i in range(L):
        graph[i].append(i + 1)
        graph[i + 1].append(i)
        
        graph[i + L + 1].append(i + L + 2)
        graph[i + L + 2].append(i + L + 1)
    
    # 建立垂直連線 (避開起點 e0 與終點 e1)
    for i in range(1, L):
        graph[i].append(i + L + 1)
        graph[i + L + 1].append(i)
        
    return graph

def find_best_path(graph, start, end, broken_nodes=None):
    """
    使用 BFS (廣度優先搜尋) 演算法尋找最短路由路徑。
    具備容錯機制，可自動繞開定義為損壞 (broken) 的節點。
    """
    if broken_nodes is None:
        broken_nodes = []
        
    if start in broken_nodes or end in broken_nodes:
        print("[Warning] Start or End node is broken.")
        return []

    queue = deque([start])
    backward = {start: None}
    broken_set = set(broken_nodes)
    
    while queue:
        curr = queue.popleft()
        
        # 抵達目標節點，回溯建立完整路徑
        if curr == end:
            path = []
            while curr is not None:
                path.append(curr)
                curr = backward[curr]
            return path[::-1]
            
        # 走訪相鄰節點 (避開已走訪與損壞節點)
        for neighbor in graph[curr]:
            if neighbor not in backward and neighbor not in broken_set:
                backward[neighbor] = curr
                queue.append(neighbor)
    return []


# =========================================================
# 量子電路生成與 C++ 模擬核心
# =========================================================
def to_cpp_expression(num_qubits, path, target_bell='Phi+'):
    """
    將路由路徑與目標貝爾態轉換為 C++ 模擬器之指令字串。
    支援位元翻轉 (X) 與相位翻轉 (Z) 以產生四種貝爾基底。
    """
    if not path:
        return ""
    instr = [f"{num_qubits}"]
    
    # 於起點與次節點建立基本糾纏態 (Phi+)
    instr.append(f"{{H,{path[0]}}}")
    instr.append(f"{{CNOT,{path[0]},{path[1]}}}")
    
    # 根據目標貝爾態施加對應之邏輯閘
    if target_bell in ['Phi-', 'Psi-']:
        instr.append(f"{{Z,{path[0]}}}")
    if target_bell in ['Psi+', 'Psi-']:
        instr.append(f"{{X,{path[1]}}}")
    
    # 沿路徑傳遞量子態 (SWAP)
    for i in range(1, len(path) - 1):
        instr.append(f"{{SWAP,{path[i]},{path[i+1]}}}")
        
    # 測量起點與終點位元
    instr.extend([f"{{M,{path[0]}}}", f"{{M,{path[-1]}}}"])
    return ", ".join(instr)

def build_qiskit_circuit(num_qubit, path, target_bell='Phi+'):
    """
    建構 Qiskit 量子電路物件，包含目標貝爾態之邏輯轉換。
    供前端驗證與視覺化使用。
    """
    qc = QuantumCircuit(num_qubit)
    if not path:
        return qc
        
    # 建立基本糾纏態 (Phi+)
    qc.h(path[0])
    qc.cx(path[0], path[1])
    
    # 根據目標貝爾態施加相位 (Z) 或位元 (X) 翻轉
    if target_bell in ['Phi-', 'Psi-']:
        qc.z(path[0])
    if target_bell in ['Psi+', 'Psi-']:
        qc.x(path[1])
    
    # 沿路徑進行 SWAP
    for i in range(1, len(path) - 1):
        qc.swap(path[i], path[i+1])
        
    cr = ClassicalRegister(2, 'meas')
    qc.add_register(cr)
    qc.measure(path[0], 0)
    qc.measure(path[-1], 1)
    
    return qc

def run_cpp_simulation(num_qubit, path, cpp_engine, target_bell='Phi+'):
    """
    初始化並執行 C++ 後端高精度物理模擬。
    包含單次快照(計算累積誤差)與多次測量(Shots僅統計目標雙位元之機率分佈)。
    """
    if not path:
        return
        
    # 1. 執行單次模擬以獲取物理誤差快照 (Snapshot)
    sim_single = cpp_engine.QubitSimulation(num_qubit)
    cfg = cpp_engine.SimulationConfig()
    cfg.error_rate = 0.02
    cfg.apply_errors = True  

    cpp_expr = to_cpp_expression(num_qubit, path, target_bell)
    result = cpp_engine.CircuitExpression.Parse(cpp_expr).ExecuteWithCapture(sim_single, cfg)
    final_snap = result.snapshots[-1]

    # 2. 執行多次測量 (Shots) 以統計目標雙位元 (e0, e1) 的機率分佈
    shots = 1000
    counts = {'00': 0, '01': 0, '10': 0, '11': 0}
    
    for _ in range(shots):
        sim_shot = cpp_engine.QubitSimulation(num_qubit)
        cpp_engine.CircuitExpression.Parse(cpp_expr).ExecuteWithCapture(sim_shot, cfg)
        
        # 僅捕捉起點與終點的測量結果
        m_start = sim_shot.GetMeasurementResult(path[0])
        m_end = sim_shot.GetMeasurementResult(path[-1])
        counts[f"{m_start}{m_end}"] += 1

    # 輸出終端機標準化報表 (固定總寬度 100 字元)
    print(f"\n{'-'*100}\n{'C++ QUANTUM SIMULATION REPORT':^100}\n{'-'*100}")
    print(f"{'Configuration':<35} | {'Value':>62}")
    print(f"{'-'*100}")
    print(f"{'Total Qubits':<35} | {num_qubit:>62}")
    print(f"{'Target Bell State':<35} | {target_bell:>62}")
    print(f"{'Error Rate':<35} | {cfg.error_rate:>61.2%}")
    print(f"{'C++ Command':<35} | {cpp_expr:>62}") 
    print(f"{'-'*100}")
    print(f"{'Execution Results (Last Snapshot)':<35} | {'Value':>62}")
    print(f"{'-'*100}")
    print(f"{'Cumulative Errors':<35} | {final_snap.cumulative_errors:>62}")
    
    # 獨立出目標雙位元的聯合機率統計區塊
    title = f"TARGET QUBITS DISTRIBUTION: Q[{path[0]}] & Q[{path[-1]}] (1000 Shots)"
    print(f"\n{'-'*100}\n{title:^100}\n{'-'*100}")
    for state, count in counts.items():
        if count > 0:
            print(f"|{state}> | {count/shots*100:>85.1f}%")
    
    print(f"\n{'-'*100}\n{'QUBIT ERROR DISTRIBUTION':^100}\n{'-'*100}")
    
    if not final_snap.qubit_error_accum:
        print(f"{'[Warning] Vector empty. Is error accumulation implemented?':^100}")
    else:
        for q, err in enumerate(final_snap.qubit_error_accum):
            print(f"Q[{q:<2}] | {err*100:>90.2f}%")
    print(f"{'-'*100}\n")

# =========================================================
# 圖形化介面與主流程控制
# =========================================================
def show_simulation_dashboard(L, graph, path, broken_nodes, qc):
    """
    利用 Matplotlib 建立雙視窗儀表板。
    左側顯示硬體拓樸與路由路徑；右側顯示生成的量子電路圖。
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    G = nx.Graph()
    for node, neighbors in graph.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
            
    # 定義梯形拓樸之二維座標 (上排 y=1, 下排 y=0)
    pos = {i: (i, 1) for i in range(L + 1)}
    pos.update({i + L + 1: (i, 0) for i in range(L + 1)})
        
    path_set = set(path)
    path_edges = set(zip(path, path[1:]))
    
    # 根據節點狀態分配視覺化顏色
    node_colors = [
        'black' if n in broken_nodes else
        'green' if path and n == path[0] else
        'red' if path and n == path[-1] else
        'skyblue' if n in path_set else 'lightgrey'
        for n in G.nodes()
    ]
            
    edge_colors = ['blue' if (u, v) in path_edges or (v, u) in path_edges else 'black' for u, v in G.edges()]
    widths = [3 if c == 'blue' else 1 for c in edge_colors]

    nx.draw(G, pos, ax=ax1, with_labels=True, node_color=node_colors, 
            edge_color=edge_colors, width=widths, node_size=800, font_weight='bold')
    ax1.set_title(f"Network Topology (L={L}) | Broken: {broken_nodes}")

    if len(path) > 0:
        qc.draw('mpl', ax=ax2)
        ax2.set_title("Generated Quantum Circuit")
    else:
        ax2.text(0.5, 0.5, 'No Path Available', horizontalalignment='center', verticalalignment='center', fontsize=20)
        ax2.axis('off')

    plt.tight_layout()
    plt.show(block=True)

def run_simulation_flow():
    """處理單次模擬之參數輸入、路徑規劃與執行流程"""
    print(f"\n{'-'*100}")
    
    # 目標貝爾態設定
    print("Target Bell State Selection:")
    print("  [1] Phi+ : (|00> + |11>) / sqrt(2)  (Default)")
    print("  [2] Phi- : (|00> - |11>) / sqrt(2)")
    print("  [3] Psi+ : (|01> + |10>) / sqrt(2)")
    print("  [4] Psi- : (|01> - |10>) / sqrt(2)")
    bell_choice = input(f"{'Enter choice (1-4) [Default: 1]':<45}: ").strip()
    
    bell_map = {'1': 'Phi+', '2': 'Phi-', '3': 'Psi+', '4': 'Psi-'}
    target_bell = bell_map.get(bell_choice, 'Phi+')
    print(f"\n[Info] Target Bell State set to: {target_bell}\n")

    # 硬體參數設定
    try:
        L_in = input(f"{'Enter Ladder Length (L) [Default: 5]':<45}: ")
        L = int(L_in) if L_in.strip() else 5
    except ValueError:
        L = 5
        
    broken_in = input(f"{'Enter Broken Nodes (e.g.: 2,10) [Default: None]':<45}: ")
    broken_nodes = []
    if broken_in.strip():
        try:
            broken_nodes = [int(x.strip()) for x in broken_in.split(',')]
        except ValueError:
            pass

    num_qubit = 2 * L + 2
    start_node = 0
    end_node = L
    
    print(f"\n[Info] Planning path from Q[{start_node}] to Q[{end_node}]...")
    ladder_graph = create_ladder_node(L)
    path = find_best_path(ladder_graph, start_node, end_node, broken_nodes)
    
    if not path:
        print("[Error] Simulation aborted due to unroutable path.")
        show_simulation_dashboard(L, ladder_graph, path, broken_nodes, QuantumCircuit(num_qubit))
        return
        
    print(f"[Success] Path mapped: {path}")
    
    # 建構電路物件供 matplotlib 繪圖使用
    qc = build_qiskit_circuit(num_qubit, path, target_bell)

    # 執行 C++ 模擬後端
    run_cpp_simulation(num_qubit, path, quantum_cpp, target_bell)
    
    print("\n[Info] A pop-up window is rendering the dashboard. Close it to continue...")
    show_simulation_dashboard(L, ladder_graph, path, broken_nodes, qc)

if __name__ == "__main__":
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{'='*100}\n{'QUANTUM ROUTING SIMULATOR':^100}\n{'='*100}")
        print("  [1] Start New Simulation")
        print("  [0] Exit Simulator")
        print(f"{'='*100}")
        
        choice = input("Select an option: ")
        
        if choice == '0':
            print("\nExiting simulator. Goodbye!")
            break
        elif choice == '1':
            run_simulation_flow()
            input("\nPress [Enter] to return to main menu...")
        else:
            input("\nInvalid option. Press [Enter] to try again...")