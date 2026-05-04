![Python Version](https://img.shields.io/badge/python-3.13%2B-blue)
![Managed by uv](https://img.shields.io/badge/managed%20by-uv-purple)  

# Quantum Routing Simulator

## 專案簡介
本專案為針對 2026 電物競賽 (Ephys Challenge 2026) 開發之量子電路模擬系統。  
主要功能為在雙腳梯子狀的特殊量子處理器 (QPU) 佈局中，設計並模擬量子電路，  
使相距甚遠之兩端點量子位元 (e0 及 e1) 產生量子糾纏，形成指定的貝爾態 (Bell State)。  
本系統結合 Python 前端與 C++ 運算後端，具備路徑規劃、自動避障與物理誤差模擬功能，  

## 核心特點
* **混合架構設計**：Python 前端進行參數輸入、圖論運算與視覺化；C++ 後端進行量子電路模擬
* **容錯路由機制**：BFS 演算法規劃最短路由，動態繞過損壞節點
* **貝爾態支援**：支援四種標準貝爾態 $|\Phi^+\rangle, |\Phi^-\rangle, |\Psi^+\rangle, |\Psi^-\rangle$
* **可視化分析**：整合 NetworkX 與 Qiskit，展示硬體拓樸與量子電路

## 模組說明
**qubit.py** - 主程式，負責路由規劃、電路生成與 C++ 模擬執行控制

**qubit_set.py** - 量子電路生成模組，根據梯形拓樸長度自動產生最佳接線邏輯
- L < 5：快速模式，使用 H + CNOT 建立貝爾態後逐級 SWAP 傳遞
- L ≥ 5：多步驟模式，上下排對稱操作，8 個步驟完成端點糾纏

## 目錄結構
```text
quantum_project/
├── README.md
├── pyproject.toml
└── src/
    ├── qubit.py              # 量子路由模擬器（主程式進入點）
    ├── qubit_set.py          # 生成 C++ 量子電路格式字串
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

### 基本路由模擬 (qubit.py)
執行主程式後，系統將提示輸入以下參數：
```
1. 選擇目標貝爾態 (1=Phi+, 2=Phi-, 3=Psi+, 4=Psi-)
2. 輸入梯子長度 L (預設 5)
3. 輸入損壞節點清單 (逗號分隔，可留空)
```

**輸出範例：**
```
----------------------------------------------------------------------------------------------------
                           INTEGRATED QUANTUM FIDELITY & PARITY ANALYSIS                            
----------------------------------------------------------------------------------------------------
Target State         : Phi+ (Expected Parity: Even(0))
----------------------------------------------------------------------------------------------------

Measurement Distribution (1000 Shots):
  > |00> : 49.0%
  > |11> : 51.0%

[Result] Parity Conservation Rate : 100.0%
----------------------------------------------------------------------------------------------------

[Info] A pop-up window is rendering the dashboard. Close it to continue...
```

## 技術來源與致謝

本專案之底層量子模擬運算核心由以下開源專案支援，特此致謝：

*   **C++ 模擬引擎**：[Qubit_Simulation](https://github.com/ufve0704terfy/Qubit_Simulation) - 提供高精度量子態演化及物理誤差模型之運算核心。
*   **技術提供者**：[ufve0704terfy](https://github.com/ufve0704terfy) - 開發並維護底層 C++ 模擬引擎。

本專案則基於此引擎開發前端自動化路由與視覺化介面。若您對底層模擬技術有興趣，請參考上述專案。