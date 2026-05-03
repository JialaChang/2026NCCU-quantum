# Quantum Routing Simulator

## 專案簡介
本專案為針對 2026 電物競賽 (Ephys Challenge 2026) 開發之量子電路模擬系統。

主要功能為在雙腳梯子狀的特殊量子處理器 (QPU) 佈局中，設計並模擬量子電路，
使相距甚遠之兩端點量子位元 (e0 及 e1) 產生量子糾纏，形成指定的貝爾態 (Bell State)。

本系統結合 Python 前端與 C++ 運算後端，具備路徑規劃、自動避障與物理誤差模擬功能，

## 核心特點
* **混合架構設計**：前端使用 Python 處理參數輸入、圖論運算與視覺化；後端採用編譯後之 C++ 模組進行高精度物理誤差模擬，兼顧開發彈性與執行效能。
* **容錯路由機制**：內建廣度優先搜尋 (BFS) 演算法，具備橫向可擴充性，適用於任何長度 L 的梯型佈局。系統能動態避開自定義之損壞 (Broken) 節點，規劃出最短有效路徑。
* **完整貝爾態支援**：系統支援動態切換並生成四種標準貝爾態：$|\phi^+\rangle$, $|\phi^-\rangle$, $|\psi^+\rangle$, $|\psi^-\rangle$，並自動映射對應之量子邏輯閘 (H, CNOT, X, Z)。
* **視覺化儀表板**：整合 NetworkX 與 Qiskit，於模擬完成後同步顯示實體硬體拓樸之路由狀態，以及生成之量子邏輯閘電路圖。
* **保真度統計分析**：提供單次物理誤差快照 (Snapshot)，並預設執行 1000 次測量 (Shots) 以統計目標雙位元之聯合機率分佈，支援雜訊環境下之保真度分析。

## 模組說明

### qubit.py - 量子路由模擬器主模組
本模組為系統的核心控制層，負責量子電路的路由規劃、貝爾態生成與 C++ 後端的執行控制。

**主要功能：**
- **硬體拓樸建立**：`create_ladder_node(L)` 生成 L 階的雙腳梯子結構
- **路由演算法**：`find_best_path()` 利用 BFS 演算法規劃最短路由，支援動態繞過損壞節點
- **貝爾態轉換**：支援四種貝爾態 ($|\Phi^+\rangle$, $|\Phi^-\rangle$, $|\Psi^+\rangle$, $|\Psi^-\rangle$)，自動映射所需邏輯閘序列
- **C++ 指令生成**：`to_cpp_expression()` 將路由路徑轉換為 C++ 模擬器之指令字串
- **Qiskit 電路構建**：`build_qiskit_circuit()` 生成等效的量子電路物件供前端視覺化
- **誤差追蹤**：`_run_single_trace()` 執行單次模擬並擷取物理誤差快照
- **統計分析**：`_run_shot_statistics()` 執行多次測量 (預設 1000 shots) 以統計聯合機率分佈與宇稱守恆率
- **視覺化儀表板**：`show_simulation_dashboard()` 同步顯示硬體拓樸路由圖與量子電路圖

**典型使用流程：**
```
run_simulation_flow()
  ↓ 使用者輸入目標貝爾態、梯子長度 L、損壞節點清單
  ↓ create_ladder_node() 建立拓樸
  ↓ find_best_path() 規劃路由
  ↓ build_qiskit_circuit() 生成電路
  ↓ run_cpp_simulation() 執行 C++ 模擬
  ↓ show_simulation_dashboard() 顯示結果儀表板
```

### purify.py - 量子纯化優化模組
本模組提供保真度優化與量子糾纏態純化之演算法實現。

**主要功能：**
- **核心模擬引擎**：`_simulate_core()` 計算保真度演化軌跡，包含自然衰減與主動純化過程
- **純化序列生成**：`get_purification_sequence()` 根據保真度閥值 (threshold) 自動決定需要純化的節點，回傳高階指令序列
- **C++ 語法解析**：`parse_to_cpp_instructions()` 將高階純化指令 (如 `{M,0,1}`, `{P,x,x+1}`) 轉換為 C++ 量子電路語法
- **決策日誌**：`print_simulation_logs()` 列印詳細的逐步決策過程，含保真度計算、觸發條件與純化成功率
- **保真度可視化**：`plot_fidelity_graph()` 繪製保真度振盪曲線，標記純化觸發點與最終成功率

**核心參數：**
- `L`：網路總長度 (梯子總節點數)
- `p`：物理錯誤率 (每個多位元閘之錯誤機率)
- `threshold`：觸發純化的保真度閥值 (典型值 0.78 ~ 0.81)
- `purify_gate_count`：執行一次純化所需的額外雜訊閘數量 (預設 3)

**演算法邏輯：**
- 保真度按 $f_x = 0.25 + (f_{x-1} - 0.25)(1-p)$ 自然衰減
- 當 $f_x < \text{threshold}$ 時計算純化收益：$p_\text{succ} = f_x f_\text{ancilla} + (1-f_x)(1-f_\text{ancilla})$
- 純化後保真度躍升至 $f_\text{jump} = \frac{f_x f_\text{ancilla}}{p_\text{succ}} \cdot (1-p)^{\text{gate\_count}}$
- 僅在 $f_\text{jump} > f_x$ 時執行純化；總成功率累乘各純化節點的 $p_\text{succ}$

## 目錄結構與相依檔案
請確保專案目錄結構如下。為確保 C++ 引擎能正確載入，編譯檔與依賴之動態連結庫 (DLL) 必須與主程式位於同一資料夾：
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

### 1. 原始碼開發模式 (需安裝 Python 與依賴項)
本專案之 C++ 核心元件已預編譯並放置於 `src` 資料夾中。

#### 主程式啟動

**使用 uv (推薦，快速且現代的包管理器)：**
```bash
uv run python src/qubit.py
```

**不使用 uv (使用 pip)：**
```bash
python src/qubit.py
```

#### 環境套件建置
本專案使用 `pyproject.toml` 管理依賴項。請根據您的包管理器選擇以下方式之一建置環境：

* **使用 uv (推薦)**：
  1. 安裝 uv：`pip install uv` 或參考 [uv 安裝指南](https://github.com/astral-sh/uv)。
  2. 建置環境並安裝依賴：`uv sync`。
  3. 啟動虛擬環境與主程式：`uv run python src/qubit.py`。

* **使用 pip**：
  1. 確保 Python >= 3.13 已安裝。
  2. 建立虛擬環境：`python -m venv .venv`。
  3. 啟動虛擬環境：`.venv\Scripts\activate` (Windows) 或 `source .venv/bin/activate` (Linux/macOS)。
  4. 安裝依賴：`pip install -e .` (從 pyproject.toml 安裝)。
  5. 執行主程式：`python src/qubit.py`。

#### 純化模組獨立使用
若只需執行保真度優化模擬，可直接執行：
```bash
python src/purify.py
```
此指令將依次執行：
1. 生成純化命令序列並展示 C++ 語法解析結果
2. 列印詳細的決策日誌
3. 繪製保真度振盪曲線

### 2. 獨立執行檔版本 (免安裝環境)
若您不想配置 Python 環境，請依照以下步驟操作：
1.  前往 [Releases](../../releases) 頁面下載 `QuantumSimulator.zip`。
2.  解壓縮至任意資料夾（請勿移動解壓後的資料夾內部結構）。
3.  執行 `QuantumSimulator.exe` 即可啟動模擬器。

*注意：若移動 `_internal` 資料夾或其中的 DLL 檔案，將導致程式無法載入 Python 運行時環境。*

### 3. 將Python程式轉換為獨立執行檔
若您需要將 Python 程式打包為獨立執行檔 (exe)，可以使用 PyInstaller (已包含在依賴項中)。

#### 建置步驟
1. 確保環境已建置 (參見上方環境套件建置)。
2. 安裝 PyInstaller (若未安裝)：`pip install pyinstaller` 或 `uv add pyinstaller`。
3. 執行打包指令：
   ```bash
   pyinstaller --onefile --windowed src/qubit.py
   ```
   * `--onefile`：生成單一 exe 檔案。
   * `--windowed`：隱藏控制台視窗 (適用於 GUI 應用，若有控制台輸出請移除)。
4. 打包完成後，`dist/` 資料夾中將生成 `qubit.exe`。
5. 將 `src/` 中的 `quantum_cpp.pyd` 及相關 `.dll` 檔案複製到 `dist/` 資料夾，確保 exe 能載入 C++ 引擎。

*注意：打包後的 exe 包含所有依賴，但檔案大小可能較大。測試 exe 功能以確保正常運作。*

## 使用示例

## 使用示例

### 範例 1：基本路由模擬 (qubit.py)
執行主程式後，系統將提示輸入以下參數：
```
1. 選擇目標貝爾態 (1=Phi+, 2=Phi-, 3=Psi+, 4=Psi-)
2. 輸入梯子長度 L (預設 5，代表 12 個量子位元)
3. 輸入損壞節點清單 (以逗號分隔，例如：2,10)
```

程式將執行以下流程：
- 建立梯形拓樸結構
- 利用 BFS 規劃從起點 (Q[0]) 至終點 (Q[L]) 的最短路由
- 生成指定貝爾態的量子電路
- 執行 C++ 後端物理誤差模擬
- 統計 1000 次測量的聯合機率分佈
- 輸出保真度分析與宇稱守恆率
- 顯示硬體拓樸與量子電路的雙視窗儀表板

**典型輸出範例：**
```
[Info] Target Bell State set to: Phi+
[Info] Planning path from Q[0] to Q[5]...
[Success] Path mapped: [0, 1, 2, 3, 4, 5]

INTEGRATED QUANTUM FIDELITY & PARITY ANALYSIS
─────────────────────────────────────────────────
Target State         : Phi+ (Expected Parity: Even(0))
Hardware Error Rate  : 5.0% per multi-qubit gate
Total Physical Errors: 3 hits during this run
─────────────────────────────────────────────────
Measurement Distribution (1000 Shots):
  > |00> : 45.2%
  > |11> : 44.8%

[Result] Parity Conservation Rate : 90.0%
```

### 範例 2：保真度優化模擬 (purify.py)
直接執行 `python src/purify.py` 將演示量子糾纏態的純化優化過程。

**預設參數：**
```python
TOTAL_LENGTH = 20       # 梯子長度
ERROR_RATE = 0.05       # 5% 物理錯誤率
THRESHOLD = 0.78        # 純化觸發閥值
```

**輸出內容：**
1. **純化命令序列**：列出每個觸發純化的節點及其對應的 C++ 指令
   ```
   [Node 03 Triggered]
   High-Level Cmd : {M,2,3},{M,3,4},{P,4,5}
   C++ Parsed Str : {SWAP,2,3},{CNOT,3,24},{SWAP,24,25},...
   ```

2. **決策日誌**：詳細的逐步決策表格
   ```
   Node | Operation | Fidelity | P_succ | Action Detail
   ─────┼───────────┼──────────┼────────┼─────────────────
      0 | Init      |   1.0000 |    -   | System Initialization
      1 | Decay     |   0.9750 |    -   | Natural decay: 1.0000 -> 0.9750
      2 | Decay     |   0.9506 |    -   | Natural decay: 0.9750 -> 0.9506
      3 | PURIFY    |   0.9612 |  0.85  | Trigger Purify -> 0.9612
   ```

3. **保真度曲線圖**：展示基準衰減 vs. 優化後的保真度，並標記純化觸發點

## 技術來源與致謝

本專案之底層量子模擬運算核心由以下開源專案支援，特此致謝：

*   **C++ 模擬引擎**：[Qubit_Simulation](https://github.com/ufve0704terfy/Qubit_Simulation) - 提供高精度量子態演化及物理誤差模型之運算核心。
*   **技術提供者**：[ufve0704terfy](https://github.com/ufve0704terfy) - 開發並維護底層 C++ 模擬引擎。

本專案則基於此引擎開發前端自動化路由與視覺化介面。若您對底層模擬技術有興趣，請參考上述專案。