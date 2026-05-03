import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 功能 1：核心邏輯與回傳格式化指令
# =====================================================================
def get_purification_sequence(L=100, p=0.05, threshold=0.81):
    """
    計算需要純化的節點，並回傳格式化字串。
    x=0 為初始化起點 (不進入衰減迴圈)。嚴格排除最後一個節點 (x=L) 進行純化。
    回傳格式: list of tuple (node_index, command_string)
    """
    f_opt = 1.0
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    commands = []
    
    for x in range(1, L + 1):
        # 進行一步自然衰減 (代表從 x-1 傳輸到了 x)
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        
        # 條件：低於門檻，且不為終點(L)
        if f_opt < threshold and x < L:
            p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
            f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
            
            # 確保純化後保真度有提升才執行
            if f_jump > f_opt:
                f_opt = f_jump
                
                # 動態產生相對應的指令字串
                cmd_str = f"{{M,{x-1},{x}}},{{M,{x},{x+1}}},{{P,{x+1},{x+2}}}"
                commands.append((x, cmd_str))
                
    return commands


# =====================================================================
# 功能 2：輸出詳細決策日誌
# =====================================================================
def print_simulation_logs(L=20, p=0.05, threshold=0.81):
    """
    印出執行時的詳細決策步驟。
    輸出保持英文格式以方便系統串接對齊。
    """
    f_opt = 1.0
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    
    print(f"\n{'='*80}")
    print(f"{'QUANTUM PURIFICATION DECISION LOG':^80}")
    print(f"{'='*80}")
    print(f"{'Node':<6} | {'Operation':<10} | {'Fidelity':<10} | {'Action Detail'}")
    print(f"{'-'*80}")
    print(f"{0:<6} | {'Init':<10} | {f_opt:<10.4f} | System Initialization (Start Node)")

    for x in range(1, L + 1):
        f_old = f_opt
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        op_type = "Decay"
        detail = f"Natural decay: {f_old:.4f} -> {f_opt:.4f}"
        
        if f_opt < threshold:
            if x == L:
                detail += " | [SKIP] Target node reached (No purify)"
            else:
                p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
                f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
                
                if f_jump > f_opt:
                    f_before = f_opt
                    f_opt = f_jump
                    op_type = "PURIFY"
                    cmd_str = f"{{M,{x-1},{x}}},{{M,{x},{x+1}}},{{P,{x+1},{x+2}}}"
                    detail = f"Trigger Purify -> {f_opt:.4f} (Return: {cmd_str})"
                else:
                    detail += " | [SKIP] Gain insufficient to overcome gate noise"

        print(f"{x:<6} | {op_type:<10} | {f_opt:<10.4f} | {detail}")
    print(f"{'='*80}\n")


# =====================================================================
# 功能 3：可視化保真度震盪圖表
# =====================================================================
def plot_fidelity_graph(L=100, p=0.05, threshold=0.81):
    """
    繪製保真度的變化曲線。
    圖例 (Legend) 設定於左下角，標題與圖例維持英文。
    起始保護線移至 x=0。
    """
    nodes = np.arange(L + 1)
    f_baseline = np.zeros(L + 1)
    f_optimized = np.zeros(L + 1)
    purify_events = []
    
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    
    # 1. 計算基準線 (僅衰減)
    f_b = 1.0
    f_baseline[0] = f_b
    for x in range(1, L + 1):
        f_b = 0.25 + (f_b - 0.25) * (1 - p)
        f_baseline[x] = f_b

    # 2. 計算動態優化路徑
    f_opt = 1.0
    f_optimized[0] = f_opt
    
    for x in range(1, L + 1):
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        
        # 條件：低於門檻，且不為終點(L)
        if f_opt < threshold and x < L:
            p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
            f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
            if f_jump > f_opt:
                f_opt = f_jump
                purify_events.append(x)
                
        f_optimized[x] = f_opt

    # 3. 繪製圖表
    plt.figure(figsize=(12, 6))
    plt.plot(nodes, f_baseline, color='gray', linestyle='--', alpha=0.6, label='Baseline (Decay Only)')
    plt.plot(nodes, f_optimized, color='#1f77b4', linewidth=2, label='Optimized (With Purification)')
    plt.scatter(purify_events, [f_optimized[i] for i in purify_events], 
                color='#2ca02c', s=35, label='Purification Triggers', zorder=5)
    
    # 標註受保護的節點區間 (頭尾)
    plt.axvline(x=L, color='red', linestyle=':', alpha=0.5, label='Target Node (No Purify)')
    plt.axvline(x=0, color='orange', linestyle=':', alpha=0.5, label='Start Node (No Purify)')

    # 圖表文字標註 (英文)
    plt.title(f'Quantum Fidelity Oscillation (L={L}, p={p})', fontsize=14)
    plt.xlabel('Node Index')
    plt.ylabel('Fidelity')
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle=':', alpha=0.5)
    
    # 圖例設定至左下角
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.show()


# =====================================================================
# 主程式執行區塊
# =====================================================================
if __name__ == "__main__":
    TOTAL_LENGTH = 25
    ERROR_RATE = 0.05
    THRESHOLD = 0.81

    # 功能 1
    print(">>> [Execution 1] Fetching Purification Command Array")
    commands_array = get_purification_sequence(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    for step, cmd in commands_array:
        print(f"Node {step:02d} -> {cmd}")
        
    # 功能 2
    print("\n>>> [Execution 2] Outputting Detailed Step-by-Step Logs")
    print_simulation_logs(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    
    # 功能 3
    print(">>> [Execution 3] Rendering Plot")
    plot_fidelity_graph(L=100, p=ERROR_RATE, threshold=THRESHOLD)