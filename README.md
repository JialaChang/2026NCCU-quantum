# Quantum Routing Simulator

## 專案簡介
本專案為針對 2026 電物競賽 (Ephys Challenge 2026) 開發之量子電路模擬系統。  
主要功能為在雙腳梯子狀的特殊量子處理器 (QPU) 佈局中，設計並模擬量子電路，  
使相距甚遠之兩端點量子位元 (e0 及 e1) 產生量子糾纏，形成指定的貝爾態 (Bell State)。  
本系統結合 Python 前端與 C++ 運算後端，具備路徑規劃、自動避障與物理誤差模擬功能，  

## 核心特點
* **混合架構設計**：Python 前端進行參數輸入、圖論運算與視覺化；C++ 後端進行高精度物理誤差模擬
* **容錯路由機制**：BFS 演算法規劃最短路由，動態繞過損壞節點
* **貝爾態支援**：支援四種標準貝爾態 $|\Phi^+\rangle, |\Phi^-\rangle, |\Psi^+\rangle, |\Psi^-\rangle$
* **保真度優化**：動態純化機制，在路徑傳遞過程中主動提升糾纏態保真度
* **可視化分析**：整合 NetworkX 與 Qiskit，展示硬體拓樸與量子電路

## 模組說明
**qubit.py** - 主程式，負責路由規劃、電路生成與 C++ 模擬執行控制

**purify.py** - 保真度優化模組，計算保真度演化與純化決策

**核心演算法**：保真度按 $f_x = 0.25 + (f_{x-1} - 0.25)(1-p)$ 自然衰減，當 $f_x < \text{threshold}$ 時觸發純化

## 目錄結構
```text
quantum_project/
├── README.md
├── pyproject.toml
└── src/
    ├── qubit.py              # 量子路由模擬器（主程式進入點）
    ├── purify.py             # 量子純化優化模組
    ├── quantum_cpp.pyd       # 編譯後之 C++ 量子模擬引擎
    ├── libstdc++-6.dll       # MSYS2 依賴函式庫
    ├── libgcc_s_seh-1.dll    # MSYS2 依賴函式庫
    └── libwinpthread-1.dll   # MSYS2 依賴函式庫
```

## 執行與部署說明

### 環境建置

本專案使用 `pyproject.toml` 管理依賴項。請選擇以下方式之一建置環境：

#### 方案 1：使用 uv (推薦)

```bash
# 步驟 1：安裝 uv
pip install uv

# 步驟 2：建置環境與安裝依賴
uv sync

# 步驟 3：執行主程式
uv run python src/qubit.py
```

#### 方案 2：使用 pip

```bash
# 步驟 1：建立虛擬環境
python -m venv .venv

# 步驟 2：啟動虛擬環境
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\Activate.ps1

# 步驟 3：安裝依賴
pip install -e .

# 步驟 4：執行主程式
python src/qubit.py
```

### 執行選項

**主程式：**
```bash
# 使用 uv
uv run python src/qubit.py

# 使用 pip (需先啟動虛擬環境)
python src/qubit.py
```

**保真度優化模擬：**
```bash
python src/purify.py
```

### 獨立執行檔版本

若不想配置 Python 環境：
1. 下載 [Releases](../../releases) 頁面的 `QuantumSimulator.zip`
2. 解壓縮至任意資料夾
3. 執行 `QuantumSimulator.exe`

*注意：勿移動解壓後的資料夾結構，以免 DLL 依賴加載失敗*

### PyInstaller 打包

若需自行打包成 exe：
```bash
pip install pyinstaller
pyinstaller --onefile --console --name "QuantumSimulator" --collect-data qiskit src/qubit.py
```

將 `src/` 中的 `quantum_cpp.pyd` 及 `.dll` 檔案複製到 `dist/` 資料夾

## 使用示例

### 範例 1：基本路由模擬 (qubit.py)
執行主程式後，系統將提示輸入以下參數：
```
1. 選擇目標貝爾態 (1=Phi+, 2=Phi-, 3=Psi+, 4=Psi-)
2. 輸入梯子長度 L (預設 5)
3. 輸入損壞節點清單 (逗號分隔，可留空)
4. 輸入純化閥值 (預設 0.78)
```

**輸出範例：**
```
----------------------------------------------------------------------------------------------------
                           INTEGRATED QUANTUM FIDELITY & PARITY ANALYSIS                            
----------------------------------------------------------------------------------------------------
Target State         : Psi+ (Expected Parity: Odd(1))
Hardware Error Rate  : 5.0% per multi-qubit gate
Total Physical Errors: 0 hits during this run
----------------------------------------------------------------------------------------------------
Pre-Measurement Error Probability (Before Collapse):
  > Q[0 ] accumulated error: 22.62%
  > Q[5 ] accumulated error: 22.62%

Measurement Distribution (1000 Shots):
  > |00> : 4.8%
  > |01> : 46.9%
  > |10> : 43.1%
  > |11> : 5.2%

[Result] Parity Conservation Rate : 90.0%
----------------------------------------------------------------------------------------------------

```

### 範例 2：保真度優化模擬 (purify.py)
直接執行 `python src/purify.py` 將演示量子糾纏態的純化優化過程。

**輸出內容：**

```
===============================================================================================
                              QUANTUM PURIFICATION DECISION LOG                               
===============================================================================================
Node   | Operation  | Fidelity   | P_succ   | Action Detail
-----------------------------------------------------------------------------------------------
0      | Init       | 1.0000     | -        | System Initialization (Start Node)
1      | Decay      | 0.9625     | -        | Natural decay: 1.0000 -> 0.9625
2      | Decay      | 0.9269     | -        | Natural decay: 0.9625 -> 0.9269
⁝
19     | PURIFY     | 0.8471     | 0.7423   | Natural decay: 0.7888 -> 0.7619 | Trigger Purify -> 0.8471
20     | Decay      | 0.8172     | -        | Natural decay: 0.8471 -> 0.8172
-----------------------------------------------------------------------------------------------
Final Fidelity at Node 20: 0.8172
Total Success Probability (Yield): 22.88%
===============================================================================================
```

**保真度曲線圖**：展示基準衰減 vs. 優化後的保真度曲線，並標記純化觸發點

## 技術來源與致謝

本專案之底層量子模擬運算核心由以下開源專案支援，特此致謝：

*   **C++ 模擬引擎**：[Qubit_Simulation](https://github.com/ufve0704terfy/Qubit_Simulation) - 提供高精度量子態演化及物理誤差模型之運算核心。
*   **技術提供者**：[ufve0704terfy](https://github.com/ufve0704terfy) - 開發並維護底層 C++ 模擬引擎。

本專案則基於此引擎開發前端自動化路由與視覺化介面。若您對底層模擬技術有興趣，請參考上述專案。