import math

def generate_quantum_circuit(L):
    # 若 L < 5 的特殊情況：建立第一貝爾態後不斷 SWAP
    if L < 5:
        # 最前面加上總 Qubit 數 L*2
        circuit = [str(L * 2), "{H,0}", "{CNOT,0,1}"]
        for i in range(1, L-1):
            circuit.append(f"{{SWAP,{i},{i+1}}}")
        
        result_str = '"' + ",".join(circuit) + '"'
        # 在 L < 5 的邏輯中沒有測量操作，因此兩種情況結果相同
        return result_str, result_str

    # L >= 5 的情況
    m = (L - 1) // 2

    # 將步驟 1 到 5 包裝成函式，方便上排與下排(加上位移 L)重複呼叫
    def get_steps_1_to_5(offset=0):
        seq_m = []    # 包含測量的電路
        seq_nom = []  # 不含測量的電路

        # 步驟 1
        seq_m.extend([f"{{H,{m+1+offset}}}", f"{{CNOT,{m+1+offset},{m+offset}}}"])
        seq_nom.extend([f"{{H,{m+1+offset}}}", f"{{CNOT,{m+1+offset},{m+offset}}}"])

        # 步驟 2
        seq_m.append(f"{{SWAP,{m+offset},{m-1+offset}}}")
        seq_nom.append(f"{{SWAP,{m+offset},{m-1+offset}}}")

        # 步驟 3
        seq_m.extend([
            f"{{CNOT,{m-1+offset},{m+offset}}}", 
            f"{{CNOT,{m+1+offset},{m+offset}}}", 
            f"{{CNOT,{m+offset},{m+1+offset}}}", # 修正：先執行 CNOT (延遲測量)
            f"{{M,{m+offset}}}",                  # 修正：再執行 M
        ])
        seq_nom.extend([
            f"{{CNOT,{m-1+offset},{m+offset}}}", 
            f"{{CNOT,{m+1+offset},{m+offset}}}", 
            f"{{CNOT,{m+offset},{m+1+offset}}}"
        ])

        # 步驟 4
        t_limit = (L - 5) // 2
        for t in range(t_limit):
            seq_m.extend([
                f"{{H,{m-2-t+offset}}}", f"{{H,{m+2+t+offset}}}",
                f"{{CNOT,{m-2-t+offset},{m-1-t+offset}}}", f"{{CNOT,{m+2+t+offset},{m+1+t+offset}}}",
                f"{{CNOT,{m-1-t+offset},{m-2-t+offset}}}", f"{{CNOT,{m+1+t+offset},{m+2+t+offset}}}", # 修正：先 CNOT
                f"{{M,{m-1-t+offset}}}", f"{{M,{m+1+t+offset}}}",                                    # 修正：再測量
            ])
            seq_nom.extend([
                f"{{H,{m-2-t+offset}}}", f"{{H,{m+2+t+offset}}}",
                f"{{CNOT,{m-2-t+offset},{m-1-t+offset}}}", f"{{CNOT,{m+2+t+offset},{m+1+t+offset}}}",
                f"{{CNOT,{m-1-t+offset},{m-2-t+offset}}}", f"{{CNOT,{m+1+t+offset},{m+2+t+offset}}}"
            ])

        # 步驟 5
        if L % 2 == 0:
            seq_m.append(f"{{SWAP,{L-3+offset},{L-2+offset}}}")
            seq_nom.append(f"{{SWAP,{L-3+offset},{L-2+offset}}}")
            
        return seq_m, seq_nom

    # 初始化總電路串列，最前面加上總 Qubit 數 L*2
    circuit_m = [str(L * 2)]
    circuit_nom = [str(L * 2)]

    # 執行上方排的操作 (偏移量為 0)
    top_m, top_nom = get_steps_1_to_5(offset=0)
    circuit_m.extend(top_m)
    circuit_nom.extend(top_nom)

    # 步驟 6: 執行下方排的操作 (偏移量為 L)
    bottom_m, bottom_nom = get_steps_1_to_5(offset=L)
    circuit_m.extend(bottom_m)
    circuit_nom.extend(bottom_nom)

    # 步驟 7
    circuit_m.extend([
        f"{{H,1}}", f"{{H,{L-2}}}", 
        f"{{CNOT,1,{L+1}}}", f"{{CNOT,{L-2},{2*L-2}}}",
        f"{{CNOT,{L+1},1}}", f"{{CNOT,{2*L-2},{L-2}}}", # 修正：先 CNOT
        f"{{M,{L+1}}}", f"{{M,{2*L-2}}}",               # 修正：再測量
        f"{{H,1}}", f"{{H,{L-2}}}"
    ])
    circuit_nom.extend([
        f"{{H,1}}", f"{{H,{L-2}}}", 
        f"{{CNOT,1,{L+1}}}", f"{{CNOT,{L-2},{2*L-2}}}",
        f"{{CNOT,{L+1},1}}", f"{{CNOT,{2*L-2},{L-2}}}",
        f"{{H,1}}", f"{{H,{L-2}}}"
    ])

    # 步驟 8
    circuit_m.extend([
        f"{{H,0}}", f"{{H,{L-1}}}",
        f"{{CNOT,0,1}}", f"{{CNOT,{L-1},{L-2}}}",
        f"{{CNOT,1,0}}", f"{{CNOT,{L-2},{L-1}}}", # 修正：先 CNOT
        f"{{M,1}}", f"{{M,{L-2}}}",                # 修正：再測量
    ])
    circuit_nom.extend([
        f"{{H,0}}", f"{{H,{L-1}}}",
        f"{{CNOT,0,1}}", f"{{CNOT,{L-1},{L-2}}}",
        f"{{CNOT,1,0}}", f"{{CNOT,{L-2},{L-1}}}"
    ])

    # 轉換成目標格式並加上雙引號
    final_m = '"' + ",".join(circuit_m) + '"'
    final_nom = '"' + ",".join(circuit_nom) + '"'

    return final_m, final_nom

# 測試用區塊
if __name__ == "__main__":
    while True:
        try:
            user_input = input("請輸入整數 I (輸入負數或非整數以退出): ")
            L_val = int(user_input) + 1
            if L_val < 0:
                break
            
            with_measurement, without_measurement = generate_quantum_circuit(L_val)
            print("\n--- 可以測量的量子電路 ---")
            print(with_measurement)
            print("\n--- 不可以測量的量子電路 ---")
            print(without_measurement)
            print("-" * 30 + "\n")
        except ValueError:
            print("程式結束。")
            break