import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 功能 1：核心邏輯與回傳格式化指令 (Return Formatted Strings)
# =====================================================================
def get_purification_sequence(L=100, p=0.05, threshold=0.81):
    """
    計算需要純化的節點，並回傳格式化字串。
    嚴格排除第一個節點 (x=1) 與最後一個節點 (x=L)。
    回傳格式: list of tuple (node_index, command_string)
    """
    f_opt = 1.0
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    commands = []
    
    for x in range(1, L + 1):
        # 自然衰減
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        
        # 條件：低於門檻，且不是頭尾節點
        if f_opt < threshold and x > 1 and x < L:
            p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
            f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
            
            # 只有當純化真的有幫助時才執行
            if f_jump > f_opt:
                f_opt = f_jump
                
                # 產生格式化字串 (根據你的需求帶入相對位置)
                cmd_str = f"{{M,{x-1},{x}}},{{M,{x},{x+1}}},{{P,{x+1},{x+2}}}"
                commands.append((x, cmd_str))
                
    return commands


# =====================================================================
# 功能 2：輸出詳細決策日誌 (Print Execution Logs)
# =====================================================================
def print_simulation_logs(L=20, p=0.05, threshold=0.81):
    """
    在終端機印出每一步的保真度變化與決策過程，供 Debug 對齊使用。
    為了避免洗頻，預設以較短的 L 執行示範。
    """
    f_opt = 1.0
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    
    print(f"\n{'='*75}")
    print(f"{'QUANTUM PURIFICATION DECISION LOG':^75}")
    print(f"{'='*75}")
    print(f"{'Node':<6} | {'Operation':<10} | {'Fidelity':<10} | {'Action Detail'}")
    print(f"{'-'*75}")
    print(f"{0:<6} | {'Init':<10} | {f_opt:<10.4f} | 系統初始化")

    for x in range(1, L + 1):
        f_old = f_opt
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        op_type = "Decay"
        detail = f"自然衰減 {f_old:.4f} -> {f_opt:.4f}"
        
        if f_opt < threshold:
            if x == 1:
                detail += " | [SKIP] 起點不純化"
            elif x == L:
                detail += " | [SKIP] 抵達目標位元，不純化"
            else:
                p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
                f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
                
                if f_jump > f_opt:
                    f_before = f_opt
                    f_opt = f_jump
                    op_type = "PURIFY"
                    cmd_str = f"{{M,{x-1},{x}}},{{M,{x},{x+1}}},{{P,{x+1},{x+2}}}"
                    detail = f"執行純化 -> {f_opt:.4f} (Return: {cmd_str})"
                else:
                    detail += " | [SKIP] 純化增益不足抵銷雜訊"

        print(f"{x:<6} | {op_type:<10} | {f_opt:<10.4f} | {detail}")
    print(f"{'='*75}\n")


# =====================================================================
# 功能 3：可視化保真度震盪圖表 (Plot Fidelity Graph)
# =====================================================================
def plot_fidelity_graph(L=100, p=0.05, threshold=0.81):
    """
    繪製保真度的變化曲線，包含基準衰減線與純化震盪線。
    """
    nodes = np.arange(L + 1)
    f_baseline = np.zeros(L + 1)
    f_optimized = np.zeros(L + 1)
    purify_events = []
    
    f_ancilla = 0.25 + 0.75 * (1 - p)**1
    
    # 1. 基準線計算
    f_b = 1.0
    f_baseline[0] = f_b
    for x in range(1, L + 1):
        f_b = 0.25 + (f_b - 0.25) * (1 - p)
        f_baseline[x] = f_b

    # 2. 優化路線計算
    f_opt = 1.0
    f_optimized[0] = f_opt
    
    for x in range(1, L + 1):
        f_opt = 0.25 + (f_opt - 0.25) * (1 - p)
        
        if f_opt < threshold and x > 1 and x < L:
            p_succ = f_opt * f_ancilla + (1 - f_opt) * (1 - f_ancilla)
            f_jump = (f_opt * f_ancilla / p_succ) * ((1 - p)**3)
            if f_jump > f_opt:
                f_opt = f_jump
                purify_events.append(x)
                
        f_optimized[x] = f_opt

    # 3. 繪圖
    plt.figure(figsize=(12, 6))
    plt.plot(nodes, f_baseline, color='gray', linestyle='--', alpha=0.6, label='Baseline (Decay Only)')
    plt.plot(nodes, f_optimized, color='#1f77b4', linewidth=2, label='Optimized (With Purification)')
    plt.scatter(purify_events, [f_optimized[i] for i in purify_events], 
                color='#2ca02c', s=35, label='Purification Triggers', zorder=5)
    
    # 標記起點與終點保護區
    plt.axvline(x=L, color='red', linestyle=':', alpha=0.5, label='Target Node (No Purify)')
    plt.axvline(x=1, color='orange', linestyle=':', alpha=0.5, label='Start Node (No Purify)')

    plt.title(f'Quantum Fidelity Oscillation (L={L}, p={p})', fontsize=14)
    plt.xlabel('Node Index')
    plt.ylabel('Fidelity')
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.show()


# =====================================================================
# 主程式執行區塊
# =====================================================================
if __name__ == "__main__":
    # 設定共用參數
    TOTAL_LENGTH = 25
    ERROR_RATE = 0.05
    THRESHOLD = 0.81

    # 執行功能 1：取得字串陣列
    print(">>> 執行功能 1：獲取純化指令字串陣列")
    commands_array = get_purification_sequence(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    for step, cmd in commands_array:
        print(f"Node {step:02d} -> {cmd}")
        
    # 執行功能 2：印出 Logs
    print("\n>>> 執行功能 2：輸出逐步 Logs")
    print_simulation_logs(L=TOTAL_LENGTH, p=ERROR_RATE, threshold=THRESHOLD)
    
    # 執行功能 3：繪製圖表
    print(">>> 執行功能 3：繪製圖表 (請查看彈出視窗)")
    # 為了圖表好看，繪圖通常用比較長的 L (例如 100) 來觀察震盪
    plot_fidelity_graph(L=100, p=ERROR_RATE, threshold=THRESHOLD)