import os
import sys
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, ClassicalRegister
from qiskit.circuit import Gate

import qubit_set
import re

# =========================================================
# 環境設定與 C++ 量子模擬引擎載入
# =========================================================
def setup_environment():
    """
    設定 Windows DLL 搜尋路徑並動態載入 C++ 編譯模組。
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
    建立雙腳梯形 (Ladder) 拓樸圖結構\n
    L 為單側電路長度，總量子位元數為 2L + 2\n
    """
    #  1  -  2  -  3  ---  L   - L+1
    #        |     |       |
    # L+2 - L+3 - L+4 --- 2L+1 - 2L+2

    graph = {i: [] for i in range(2 * L + 2)}
    
    # 建立水平連線 (上排與下排)
    for i in range(L):
        graph[i].append(i + 1)
        graph[i + 1].append(i)
        
        graph[i + L + 1].append(i + L + 2)
        graph[i + L + 2].append(i + L + 1)
    
    # 建立垂直連線 (避開起點與終點，確保梯形結構)
    for i in range(1, L):
        graph[i].append(i + L + 1)
        graph[i + L + 1].append(i)
        
    return graph

def find_best_path(graph, start, end, broken_nodes=None):
    """
    使用 BFS (廣度優先搜尋) 演算法尋找最短路由路徑\n
    具備容錯機制，可自動繞開定義為損壞 (broken) 的節點\n
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
def to_cpp_expression(L, target_bell='Phi+'):
    cpp_expr_raw, cpp_expr_raw_without = qubit_set.generate_quantum_circuit(L+1)
    clean_expr = cpp_expr_raw_without.strip('"')
    extra_instr = []
    if target_bell in ['Phi-', 'Psi-']: extra_instr.append(f"{{Z,0}}")
    if target_bell in ['Psi+', 'Psi-']: extra_instr.append(f"{{X,{L}}}")
    extra_instr.extend([f"{{M,0}}", f"{{M,{L}}}"])
    return clean_expr + "," + ",".join(extra_instr)

def build_qiskit_circuit(num_qubit, cpp_expr):
    print(cpp_expr)
    # 建立一個擁有 num_qubit 量子位元和 num_qubit 古典位元的電路 (單一匯流排畫圖乾淨)
    qc = QuantumCircuit(num_qubit, num_qubit)
    
    # 解析最基本的 {GATE, 參數1, 參數2...} 格式，不再需要解析 If
    pattern = r'\{([A-Za-z]+),([0-9,]+)\}'
    instructions = re.findall(pattern, cpp_expr)
    
    for gate, params_str in instructions:
        params = [int(p) for p in params_str.split(',')]
        if gate == 'H': qc.h(params[0])
        elif gate == 'X': qc.x(params[0])
        elif gate == 'Z': qc.z(params[0])
        elif gate == 'CNOT': qc.cx(params[0], params[1])
        elif gate == 'SWAP': qc.swap(params[0], params[1])
        elif gate == 'M':
            # 將測量結果統一輸出到底部的匯流排對應位置
            qc.measure(params[0], params[0])
            
    return qc


# =========================================================
# 執行單次模擬以取得快照
# =========================================================
def _run_single_trace(num_qubit, cpp_expr, cfg, cpp_engine):
    """
    執行單次模擬以獲取物理誤差快照 (Snapshot) 及其累積資訊
    """
    sim_single = cpp_engine.QubitSimulation(num_qubit)
    
    # 解析指令並執行
    parsed_circuit = cpp_engine.CircuitExpression.Parse(cpp_expr)
    result = parsed_circuit.ExecuteWithCapture(sim_single, cfg)
    
    pre_meas_snap = None
    for snap in result.snapshots:
        if "Parity" in snap.step_label or "M," in snap.step_label:
            break
        pre_meas_snap = snap
        
    return result, pre_meas_snap


# =========================================================
# 執行多次測量以統計分佈
# =========================================================
def _run_shot_statistics(num_qubit, cpp_expr, cfg, cpp_engine, path, expected_parity, shots=1000):
    """
    執行多次測量 (Shots) 以統計目標雙位元的分佈，並驗證宇稱守恆率
    """
    counts = {'00': 0, '01': 0, '10': 0, '11': 0}
    parity_success_count = 0
    
    # 預先編譯 C++ 電路表達式
    parsed_circuit = cpp_engine.CircuitExpression.Parse(cpp_expr)
    
    for _ in range(shots):
        sim_shot = cpp_engine.QubitSimulation(num_qubit)
        parsed_circuit.ExecuteWithCapture(sim_shot, cfg)
        
        m_start = sim_shot.GetMeasurementResult(path[0])
        m_end = sim_shot.GetMeasurementResult(path[-1])
        counts[f"{m_start}{m_end}"] += 1
        
        # 驗證宇稱守恆：(起點結果 + 終點結果) mod 2 是否符合預期
        if m_start != -1 and m_end != -1:
            actual_parity = (m_start + m_end) % 2
            if actual_parity == expected_parity:
                parity_success_count += 1
                
    return counts, parity_success_count

def run_cpp_simulation(num_qubit, path, cpp_engine, target_bell='Phi+'):
    """
    初始化並執行 C++ 後端高精度物理模擬的主函式\n
    負責統合單次追蹤與多次統計，並將結果格式化輸出\n
    """
    # 邊界保護：避免路徑過短導致非法指令
    if not path or len(path) < 2:
        print("[Error] Path invalid or too short for simulation.")
        return
        
    cfg = cpp_engine.SimulationConfig()

    # 轉換器
    L_val = (num_qubit - 2) // 2
    cpp_expr = to_cpp_expression(L_val, target_bell)
    # cpp_expr = to_cpp_expression(num_qubit, path, target_bell)
    expected_parity = 0 if target_bell in ['Phi+', 'Phi-'] else 1

    # 執行單次軌跡追蹤
    result, pre_meas_snap = _run_single_trace(num_qubit, cpp_expr, cfg, cpp_engine)
    
    # 執行大量測量統計 (1000 Shots)
    shots = 1000
    counts, parity_success_count = _run_shot_statistics(num_qubit, cpp_expr, cfg, cpp_engine, path, expected_parity, shots)

    # 整合輸出：移除誤差相關資訊
    print(f"\n{'-'*100}\n{'INTEGRATED QUANTUM FIDELITY & PARITY ANALYSIS':^100}\n{'-'*100}")
    print(f"Target State         : {target_bell} (Expected Parity: {'Even(0)' if expected_parity==0 else 'Odd(1)'})")
    print(f"{'-'*100}")

    # 目標位元分佈與宇稱守恆率
    print(f"\nMeasurement Distribution ({shots} Shots):")
    for state, count in counts.items():
        if count > 0:
            print(f"  > |{state}> : {count/shots*100:.1f}%")
            
    print(f"\n[Result] Parity Conservation Rate : {parity_success_count/shots*100:.1f}%")
    print(f"{'-'*100}\n")


# =========================================================
# 圖形化介面與主流程控制
# =========================================================
def show_simulation_dashboard(L, graph, path, broken_nodes, qc):
    """
    利用 Matplotlib 建立雙視窗儀表板\n
    左側顯示硬體拓樸與路由路徑；右側顯示生成的量子電路圖\n
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 3]}, constrained_layout=True)
    
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
            edge_color=edge_colors, width=widths, node_size=500, font_weight='bold')
    ax1.set_title(f"Network Topology (L={L}, I={L+1}) | Broken: {broken_nodes}")

    # 若成功找到路徑，則繪製對應的量子電路圖
    if len(path) > 0:
        qc.draw('mpl', ax=ax2, fold=-1)
        ax2.set_title("Generated Quantum Circuit")
    else:
        ax2.text(0.5, 0.5, 'No Path Available', horizontalalignment='center', verticalalignment='center', fontsize=20)
        ax2.axis('off')

    plt.subplots_adjust(hspace=0.5)
    plt.show(block=True)


def run_simulation_flow():
    """
    處理單次模擬之參數輸入、路徑規劃與執行流程。
    """
    print(f"\n{'-'*100}")
    
    # 步驟 1：目標貝爾態設定
    print("Target Bell State Selection:")
    print("  [1] Phi+ : (|00> + |11>) / sqrt(2)  (Default)")
    print("  [2] Phi- : (|00> - |11>) / sqrt(2)")
    print("  [3] Psi+ : (|01> + |10>) / sqrt(2)")
    print("  [4] Psi- : (|01> - |10>) / sqrt(2)")
    bell_choice = input(f"\n{'Enter choice (1-4) [Default: 1]':<45}: ").strip()
    
    bell_map = {'1': 'Phi+', '2': 'Phi-', '3': 'Psi+', '4': 'Psi-'}
    target_bell = bell_map.get(bell_choice, 'Phi+')
    print(f"\n[Info] Target Bell State set to: {target_bell}")

    # 步驟 2：硬體參數與損壞節點設定
    try:
        L_in = input(f"\n{'Enter Ladder Length (L) [Default: 5]':<45}: ")
        L = int(L_in) if L_in.strip() else 5
    except ValueError:
        L = 5
        
    broken_in = input(f"\n{'Enter Broken Nodes (e.g.: 2,10) [Default: None]':<45}: ")
    broken_nodes = []
    if broken_in.strip():
        try:
            broken_nodes = [int(x.strip()) for x in broken_in.split(',')]
        except ValueError:
            pass

    # 步驟 4：建立拓樸與尋路
    num_qubit = 2 * L + 2
    start_node = 0
    end_node = L
    
    print(f"\n[Info] Planning path from Q[{start_node}] to Q[{end_node}]...")
    ladder_graph = create_ladder_node(L)
    path = find_best_path(ladder_graph, start_node, end_node, broken_nodes)
    
    # 檢查是否尋路失敗或路徑過短
    if not path or len(path) < 2:
        print("[Error] Simulation aborted due to unroutable or invalid path.")
        show_simulation_dashboard(L, ladder_graph, path, broken_nodes, QuantumCircuit(num_qubit))
        return
        
    print(f"[Success] Path mapped: {path}")
    
    # 步驟 5：建構電路物件並執行 C++ 後端模擬
    cpp_expr = to_cpp_expression(L, target_bell)
    qc = build_qiskit_circuit(num_qubit, cpp_expr)
    run_cpp_simulation(num_qubit, path, quantum_cpp, target_bell)
    # qc = build_qiskit_circuit(num_qubit, path, target_bell)
    # run_cpp_simulation(num_qubit, path, quantum_cpp, target_bell)
    
    # 步驟 6：顯示結果儀表板
    print("[Info] A pop-up window is rendering the dashboard. Close it to continue...")
    show_simulation_dashboard(L, ladder_graph, path, broken_nodes, qc)


if __name__ == "__main__":
    while True:
        # 終端機清空指令
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"{'='*100}\n{'QUANTUM ROUTING SIMULATOR':^100}\n{'='*100}")
        print("  [1] Start New Simulation")
        print("  [0] Exit Simulator")
        print(f"{'='*100}")
        
        choice = input("Select an option: ")
        
        if choice == '0':
            print("\nExiting simulator. Goodbye!\n")
            break
        elif choice == '1':
            run_simulation_flow()
            input("\nPress [Enter] to return to main menu...")
        else:
            input("\nInvalid option. Press [Enter] to try again...")