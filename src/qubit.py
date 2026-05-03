import os
import sys
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, ClassicalRegister
from qiskit.circuit import Gate

from purify import _simulate_core, print_simulation_logs, BEST_THRESHOLD

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
def to_cpp_expression(num_qubits, path, target_bell='Phi+', error_rate=0.05, threshold=BEST_THRESHOLD):
    """
    將路由路徑與目標貝爾態轉換為 C++ 模擬器之指令字串。
    """
    # 邊界保護：確保路徑至少有起點和終點
    if not path or len(path) < 2:
        return ""
        
    # 接收引入自 purify 的 4 個 return 值
    L_path = len(path) - 1
    _, _, events, _ = _simulate_core(L_path, error_rate, threshold)

    # 建立 C++ 量子電路字串格式        
    instr = [f"{num_qubits}"]
    
    # 建立基本糾纏態 (Phi+)
    instr.append(f"{{H,{path[0]}}}")
    instr.append(f"{{CNOT,{path[0]},{path[1]}}}")
    
    # 目標貝爾態轉換：根據需求施加 Z 閘或 X 閘
    if target_bell in ['Phi-', 'Psi-']:
        instr.append(f"{{Z,{path[0]}}}")
    if target_bell in ['Psi+', 'Psi-']:
        instr.append(f"{{X,{path[1]}}}")
        
    # 沿路徑傳遞量子態 (透過 SWAP 操作)
    for i in range(1, len(path) - 1):
        instr.append(f"{{SWAP,{path[i]},{path[i+1]}}}")
        
        # 動態插入純化 Parity 指令
        if events[i]['triggered']:
            # [修改點] 只傳入要做測量的 qubits
            instr.append(f"{{Parity,{path[0]},{path[i+1]}}}")
                
    # 測量起點與終點位元
    instr.extend([f"{{M,{path[0]}}}", f"{{M,{path[-1]}}}"])
    # print("[Debug] C++ command: \"" + ", ".join(instr) + "\"")
    return ", ".join(instr)

def build_qiskit_circuit(num_qubit, path, target_bell='Phi+', error_rate=0.05, threshold=BEST_THRESHOLD):
    """
    建構 Qiskit 量子電路物件，包含目標貝爾態之邏輯轉換\n
    供前端驗證與視覺化使用\n
    """
    qc = QuantumCircuit(num_qubit)
    if not path or len(path) < 2:
        return qc
        
    # 接收引入自 purify 的 4 個 return 值
    L_path = len(path) - 1
    _, _, events, _ = _simulate_core(L_path, error_rate, threshold)
        
    # 建立基本糾纏態
    qc.h(path[0])
    qc.cx(path[0], path[1])
    
    # 狀態轉換
    if target_bell in ['Phi-', 'Psi-']:
        qc.z(path[0])
    if target_bell in ['Psi+', 'Psi-']:
        qc.x(path[1])
        
    # 畫出自定義的 Purify 區塊
    parity_gate = Gate(name='Purify', num_qubits=2, params=[])
    
    # 沿路徑進行 SWAP
    for i in range(1, len(path) - 1):
        qc.swap(path[i], path[i+1])
        
        # 如果有進行純化才畫出盒子
        # if events[i]['triggered']:
        #     qc.append(parity_gate, [path[0], path[i+1]])
    
    # 標準單點測量
    cr = ClassicalRegister(2, 'meas')
    qc.add_register(cr)
    qc.measure(path[0], 0)
    qc.measure(path[-1], 1)
    
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
        # === 修改：確保在沒有發生 Parity 時，碰到單點測量 (M) 也能正確截斷以取得測量前快照 ===
        if "Parity" in snap.step_label or "M," in snap.step_label:
            break
        pre_meas_snap = snap
        # ======================================================================================
        
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


def run_cpp_simulation(num_qubit, path, cpp_engine, target_bell='Phi+', threshold=BEST_THRESHOLD):
    """
    初始化並執行 C++ 後端高精度物理模擬的主函式\n
    負責統合單次追蹤與多次統計，並將結果格式化輸出\n
    """
    # 邊界保護：避免路徑過短導致非法指令
    if not path or len(path) < 2:
        print("[Error] Path invalid or too short for simulation.")
        return
        
    cfg = cpp_engine.SimulationConfig()
    cfg.error_rate = 0.05  # 設定 5% 雜訊
    cfg.apply_errors = True
    cfg.track_errors = True

    # 轉換器
    cpp_expr = to_cpp_expression(num_qubit, path, target_bell, cfg.error_rate, threshold)
    expected_parity = 0 if target_bell in ['Phi+', 'Phi-'] else 1

    # 執行單次軌跡追蹤
    result, pre_meas_snap = _run_single_trace(num_qubit, cpp_expr, cfg, cpp_engine)
    
    # 執行大量測量統計 (1000 Shots)
    shots = 1000
    counts, parity_success_count = _run_shot_statistics(num_qubit, cpp_expr, cfg, cpp_engine, path, expected_parity, shots)

    # 輸出終端機標準化報表 (維持全英文輸出以對齊介面風格)
    print(f"\n{'-'*100}\n{'STEP-BY-STEP ERROR DIFFUSION TRACE':^100}\n{'-'*100}")
    for snap in result.snapshots:
        if snap.error_record.occurred:
            err_type = str(snap.error_record.type).split('.')[-1]
            print(f"[Step {snap.step_index+1:02d}] {snap.step_label:<20} | {err_type}-Error occurred on Q[{snap.error_record.affected_qubit}]!")
        if "Parity" in snap.step_label:
            print(f"[Step {snap.step_index+1:02d}] {snap.step_label:<20} | Parity Measured! Wavefunction collapsed, error probability flushed.")

    # 整合輸出：將保真度、誤差分佈與宇稱守恆合併為單一分析區塊
    print(f"\n{'-'*100}\n{'INTEGRATED QUANTUM FIDELITY & PARITY ANALYSIS':^100}\n{'-'*100}")
    print(f"Target State         : {target_bell} (Expected Parity: {'Even(0)' if expected_parity==0 else 'Odd(1)'})")
    print(f"Hardware Error Rate  : {cfg.error_rate*100:.1f}% per multi-qubit gate")
    print(f"Total Physical Errors: {result.snapshots[-1].cumulative_errors} hits during this run")
    print(f"{'-'*100}")
    
    # 測量前的理論誤差累積 (顯示非零值)
    print("Pre-Measurement Error Probability (Before Collapse):")
    if pre_meas_snap and pre_meas_snap.qubit_error_accum:
        for q, err in enumerate(pre_meas_snap.qubit_error_accum):
            if err > 1e-9:
                print(f"  > Q[{q:<2}] accumulated error: {err*100:.2f}%")
    else:
        print("  > No significant errors accumulated prior to measurement.")

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
    ax1.set_title(f"Network Topology (L={L}) | Broken: {broken_nodes}")

    # 若成功找到路徑，則繪製對應的量子電路圖
    if len(path) > 0:
        qc.draw('mpl', ax=ax2, fold=-1, idle_wires=False)
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

    # 步驟 3：純化閥值輸入
    try:
        th_in = input(f"{'\nEnter Purification Threshold [Default: 0.78]':<45}: ")
        threshold = float(th_in) if th_in.strip() else BEST_THRESHOLD
    except ValueError:
        threshold = BEST_THRESHOLD

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
    
    # 判斷上排路徑是否為直線，決定是否啟用純化
    expected_straight_path = list(range(L + 1))
    is_straight_line = (path == expected_straight_path)

    if not is_straight_line:
        print("\n[Warning] Path is non-straight (routing around broken nodes)!")
        print("          Bottom row ancilla qubits are potentially occupied or unavailable.")
        print("          Dynamic Purification is automatically DISABLED for this run.")
        active_threshold = -1.0  # 設為不可能達到的負值，藉此關閉純化觸發
    else:
        active_threshold = threshold

    # 步驟 5：建構電路物件並執行 C++ 後端模擬
    qc = build_qiskit_circuit(num_qubit, path, target_bell, error_rate=0.05, threshold=active_threshold)
    run_cpp_simulation(num_qubit, path, quantum_cpp, target_bell, threshold=active_threshold)

    # 引入自 purify.py 的日誌輸出功能與互動式詢問
    if is_straight_line and active_threshold > 0:
        L_path = len(path) - 1
        # 使用引入的 4 個 return 值
        _, _, events, _ = _simulate_core(L_path, 0.05, active_threshold)
        
        # 如果有觸發事件，則詢問使用者是否觀看日誌
        if any(e['triggered'] for e in events):
            view_log = input(f"{'[Prompt] Purification triggered! View detailed logs? (y/n) [Default: n]':<65}: ").strip().lower()
            print('')
            if view_log == 'y':
                print_simulation_logs(L=L_path, p=0.05, threshold=active_threshold)
    
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