import numpy as np
import matplotlib.pyplot as plt
import re

# 定義 4 維 Hilbert 空間的均勻機率下限 (完全混合態保真度)
MAXIMALLY_MIXED_FIDELITY = 0.25
# 測試後最佳的閥值
BEST_THRESHOLD = 0.78

# =====================================================================
# 核心引擎 (共用計算邏輯)
# =====================================================================
def _simulate_core(L, p, threshold, purify_gate_count=3):
    """
    執行量子純化模擬的核心計算引擎。
    
    參數：
        L: 網路總長度 (Node 0 到 L)
        p: 物理錯誤率
        threshold: 觸發純化的保真度閥值
        purify_gate_count: 執行一次純化所需的額外雜訊閘數量 (預設為 3)
        
    回傳：
        - f_baseline: 基準衰減陣列
        - f_optimized: 優化後的保真度陣列
        - events: 包含觸發節點、純化前後保真度及決策原因的字典陣列
        - total_success_prob: 抵達終點的總成功率
    """
    # 輔助位元保真度 (假設來自相鄰節點，距離為 1)
    f_ancilla = MAXIMALLY_MIXED_FIDELITY + (1.0 - MAXIMALLY_MIXED_FIDELITY) * (1 - p)**1
    
    # 1. 計算基準線 (僅自然衰減)
    f_baseline = np.zeros(L + 1)
    f_b = 1.0
    f_baseline[0] = f_b
    for x in range(1, L + 1):
        f_b = MAXIMALLY_MIXED_FIDELITY + (f_b - MAXIMALLY_MIXED_FIDELITY) * (1 - p)
        f_baseline[x] = f_b

    # 2. 計算動態優化路徑
    f_optimized = np.zeros(L + 1)
    f_opt = 1.0
    f_optimized[0] = f_opt
    events = []
    
    # 初始化總成功率為 100%
    total_success_prob = 1.0 
    
    for x in range(1, L + 1):
        f_old = f_opt 
        # 進行一步自然衰減
        f_opt = MAXIMALLY_MIXED_FIDELITY + (f_opt - MAXIMALLY_MIXED_FIDELITY) * (1 - p)
        f_decayed = f_opt 
        
        event_info = {
            'node': x,
            'f_old': f_old,
            'f_decayed': f_decayed,
            'triggered': False,
            'reason': '',
            'p_succ': 1.0 
        }
        
        # 條件判斷：低於閥值才考慮純化
        if f_opt < threshold:
            if x == L:
                event_info['reason'] = '[SKIP] Target node reached (No purify)'
            else:
                # 計算純化成功率與躍升後的保真度
                p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
                f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**purify_gate_count)
                
                # 確保純化後保真度有實質提升
                if f_jump > f_opt:
                    event_info['triggered'] = True
                    event_info['f_jumped'] = f_jump
                    event_info['p_succ'] = p_succ 
                    
                    f_opt = f_jump 
                    total_success_prob *= p_succ 
                else:
                    event_info['reason'] = '[SKIP] Gain insufficient to overcome gate noise'
                    
        events.append(event_info)
        f_optimized[x] = f_opt

    return f_baseline, f_optimized, events, total_success_prob


# =====================================================================
# 功能 1：獲取指令序列與 C++ 語法解析
# =====================================================================
def get_purification_sequence(L=100, p=0.05, threshold=BEST_THRESHOLD):
    """
    計算需要純化的節點，並回傳格式化的高階指令字串。
    回傳格式: list of tuple (node_index, command_string)
    """
    _, _, events, _ = _simulate_core(L, p, threshold)
    commands = []
    
    for event in events:
        if event['triggered']:
            x = event['node']
            cmd_str = f"{{M,{x-1},{x}}},{{M,{x},{x+1}}},{{P,{x+1},{x+2}}}"
            commands.append((x, cmd_str))
            
    return commands

def parse_to_cpp_instructions(command_string, L):
    """
    將高階純化指令解析為 C++ 量子電路語法。
    例如將 {M,0,1} 轉換為對應的 CNOT/SWAP 與條件判斷邏輯。
    """
    pattern = r'\{([A-Z]+),(\d+),(\d+)\}'
    matches = re.findall(pattern, command_string)
    
    parsed_instructions = []
    
    for match in matches:
        gate_type = match[0]
        a = int(match[1])
        b = int(match[2])
        
        if gate_type == 'M':
            if a == 0 and b == 1:
                total_qubits = 2 * L
                parsed_instructions.append(f"{total_qubits},{{Label,start}},{{H,0}},{{CNOT,0,1}}")
            else:
                parsed_instructions.append(f"{{SWAP,{a},{b}}}")
                
        elif gate_type == 'P':
            p_logic = (
                f"{{CNOT,{a},{a+L}}},"
                f"{{SWAP,{a+L},{a+L+1}}},"
                f"{{CNOT,{b},{a+L+1}}},"
                f"{{If,{{M,{a+L+1},1}},{{Reset}},{{Goto,start}}}},"
                f"{{INIT,{a+L},0}},"
                f"{{INIT,{a+L+1},0}}"
            )
            parsed_instructions.append(p_logic)
            
    return ",".join(parsed_instructions)


# =====================================================================
# 功能 2：輸出詳細決策日誌 
# =====================================================================
def print_simulation_logs(L=20, p=0.05, threshold=BEST_THRESHOLD):
    """
    印出執行時的詳細決策步驟
    """
    _, f_optimized, events, total_prob = _simulate_core(L, p, threshold)
    
    print(f"{'='*100}")
    print(f"{'QUANTUM PURIFICATION DECISION LOG':^95}")
    print(f"{'='*100}")
    print(f"{'Node':<6} | {'Operation':<10} | {'Fidelity':<10} | {'P_succ':<8} | {'Action Detail'}")
    print(f"{'-'*100}")
    print(f"{0:<6} | {'Init':<10} | {1.0:<10.4f} | {'-':<8} | System Initialization (Start Node)")

    for ev in events:
        x = ev['node']
        f_decayed = ev['f_decayed']
        detail = f"Natural decay: {ev['f_old']:.4f} -> {f_decayed:.4f}"
        
        if ev['triggered']:
            p_succ_str = f"{ev['p_succ']:.4f}"
            print(f"{x:<6} | {'PURIFY':<10} | {ev['f_jumped']:<10.4f} | {p_succ_str:<8} | {detail} | Trigger Purify -> {ev['f_jumped']:.4f}")
        else:
            reason = f" | {ev['reason']}" if ev['reason'] else ""
            print(f"{x:<6} | {'Decay':<10} | {f_decayed:<10.4f} | {'-':<8} | {detail}{reason}")

    print(f"{'-'*100}")
    print(f"Final Fidelity at Node {L}: {f_optimized[-1]:.4f}")
    print(f"Total Success Probability (Yield): {total_prob * 100:.4f}%")
    print(f"{'='*100}\n")


# =====================================================================
# 功能 3：可視化保真度震盪圖表
# =====================================================================
def plot_fidelity_graph(L=100, p=0.05, threshold=BEST_THRESHOLD):
    """
    繪製保真度的變化曲線，圖例設定於左下角
    """
    f_baseline, f_optimized, events, total_prob = _simulate_core(L, p, threshold)
    
    nodes = np.arange(L + 1)
    purify_nodes = [e['node'] for e in events if e['triggered']]
    purify_fidelities = [f_optimized[n] for n in purify_nodes]

    plt.figure(figsize=(12, 6))
    plt.plot(nodes, f_baseline, color='gray', linestyle='--', alpha=0.6, label='Baseline (Decay Only)')
    plt.plot(nodes, f_optimized, color='#1f77b4', linewidth=2, label='Optimized (With Purification)')
    plt.scatter(purify_nodes, purify_fidelities, 
                color='#2ca02c', s=35, label=f'Purification Triggers ({len(purify_nodes)} times)', zorder=5)
    
    plt.axvline(x=L, color='red', linestyle=':', alpha=0.5, label='Target Node (No Purify)')
    plt.axvline(x=0, color='orange', linestyle=':', alpha=0.5, label='Start Node (No Purify)')

    title_str = (f'Quantum Fidelity Oscillation (L={L}, p={p}, th={threshold})\n'
                 f'Final Fidelity: {f_optimized[-1]:.4f}  |  Total Success Rate: {total_prob*100:.4f}%')
    plt.title(title_str, fontsize=14)
    plt.xlabel('Node Index')
    plt.ylabel('Fidelity')
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle=':', alpha=0.5)
    
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.show()

# =====================================================================
# 參數輸入輔助函式
# =====================================================================
def get_user_parameters():
    """
    提示使用者輸入網路長度、錯誤率與純化閥值。
    """
    print(f"{'='*100}")
    print(f"{'QUANTUM PURIFICATION SIMULATOR SETUP':^50}")
    print(f"{'='*100}")
    
    try:
        l_in = input(f"{'Enter Network Length (L) [Default: 20]':<45}: ")
        total_length = int(l_in) if l_in.strip() else 20
    except ValueError:
        total_length = 20

    try:
        p_in = input(f"{'Enter Error Rate (p) [Default: 0.05]':<45}: ")
        error_rate = float(p_in) if p_in.strip() else 0.05
    except ValueError:
        error_rate = 0.05

    try:
        th_in = input(f"{'Enter Threshold [Default: 0.78]':<45}: ")
        threshold = float(th_in) if th_in.strip() else BEST_THRESHOLD
    except ValueError:
        threshold = BEST_THRESHOLD

    print(f"{'='*100}\n")
    return total_length, error_rate, threshold

# =====================================================================
# 主程式執行區塊
# =====================================================================
if __name__ == "__main__":
    
    # 獲取使用者輸入
    TOTAL_LENGTH, ERROR_RATE, THRESHOLD = get_user_parameters()

    # print(">>> [Execution 1] Fetching Purification Command Array & C++ Parsing")
    # commands_array = get_purification_sequence(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    
    # for step, cmd in commands_array:
    #     print(f"\n[Node {step:02d} Triggered]")
    #     print(f"High-Level Cmd : {cmd}")
    #     # 示範呼叫 C++ 語法解析器
    #     cpp_str = parse_to_cpp_instructions(cmd, L=TOTAL_LENGTH)
    #     print(f"C++ Parsed Str : {cpp_str}")
        
    print(">>> [Execution 2] Outputting Detailed Step-by-Step Logs\n")
    print_simulation_logs(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    
    print(">>> [Execution 3] Rendering Plot\n")
    plot_fidelity_graph(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)