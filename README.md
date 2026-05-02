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

## 目錄結構與相依檔案
請確保專案目錄結構如下。為確保 C++ 引擎能正確載入，編譯檔與依賴之動態連結庫 (DLL) 必須與主程式位於同一資料夾：
```text
quantum_project/
├── README.md
└── src/
    ├── qubit_withcpp.py      # 主程式進入點
    ├── quantum_cpp.pyd       # 編譯後之 C++ 量子模擬引擎
    ├── libstdc++-6.dll       # MSYS2 依賴函式庫
    ├── libgcc_s_seh-1.dll    # MSYS2 依賴函式庫
    └── libwinpthread-1.dll   # MSYS2 依賴函式庫
```

## 執行與部署說明

### 1. 原始碼開發模式 (需安裝 Python 與依賴項)
本專案之 C++ 核心元件已預編譯並放置於 `src` 資料夾中。
*   **啟動指令**：`python src/qubit_withcpp.py`
*   **必要元件**：請確保 `src/` 下包含 `quantum_cpp.pyd` 與相關 `.dll` 檔案。

#### 環境套件建置
本專案使用 `pyproject.toml` 管理依賴項。請根據您的包管理器選擇以下方式之一建置環境：

* **使用 uv (推薦，快速且現代的包管理器)**：
  1. 安裝 uv：`pip install uv` 或參考 [uv 安裝指南](https://github.com/astral-sh/uv)。
  2. 建置環境並安裝依賴：`uv sync`。
  3. 啟動虛擬環境：`uv run python src/qubit_withcpp.py`。

* **不使用 uv (使用 pip)**：
  1. 確保 Python >= 3.13 已安裝。
  2. 安裝依賴：`pip install -e .` (從 pyproject.toml 安裝)。

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
   ```
   pyinstaller --onefile --windowed src/qubit_withcpp.py
   ```
   * `--onefile`：生成單一 exe 檔案。
   * `--windowed`：隱藏控制台視窗 (適用於 GUI 應用，若有控制台輸出請移除)。
4. 打包完成後，`dist/` 資料夾中將生成 `qubit_withcpp.exe`。
5. 將 `src/` 中的 `quantum_cpp.pyd` 及相關 `.dll` 檔案複製到 `dist/` 資料夾，確保 exe 能載入 C++ 引擎。

*注意：打包後的 exe 包含所有依賴，但檔案大小可能較大。測試 exe 功能以確保正常運作。*

## 技術來源與致謝

本專案之底層量子模擬運算核心由以下開源專案支援，特此致謝：

*   **C++ 模擬引擎**：[Qubit_Simulation](https://github.com/ufve0704terfy/Qubit_Simulation) - 提供高精度量子態演化及物理誤差模型之運算核心。
*   **技術提供者**：[ufve0704terfy](https://github.com/ufve0704terfy) - 開發並維護底層 C++ 模擬引擎。

本專案則基於此引擎開發前端自動化路由與視覺化介面。若您對底層模擬技術有興趣，請參考上述專案。