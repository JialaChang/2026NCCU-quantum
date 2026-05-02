# Quantum Routing Simulator

## 專案簡介
本專案為針對 2026 電物競賽 (Ephys Challenge 2026) 開發之量子電路模擬系統。
主要功能為在雙腳梯子狀的特殊量子處理器 (QPU) 佈局中，設計並模擬量子電路，
使相距甚遠之兩端點量子位元 (e0 及 e1) 產生量子糾纏，形成指定的貝爾態 (Bell State)。
本系統結合 Python 前端與 C++ 運算後端，具備路徑規劃、自動避障與物理誤差模擬功能。

## 核心特點
* **混合架構設計**：前端使用 Python 處理參數輸入、圖論運算與視覺化；後端採用編譯後之 C++ 模組進行高精度物理誤差模擬，兼顧開發彈性與執行效能。
* **容錯路由機制**：內建廣度優先搜尋 (BFS) 演算法，具備橫向可擴充性，適用於任何長度 L 的梯型佈局。系統能動態避開自定義之損壞 (Broken) 節點，規劃出最短有效路徑。
* **完整貝爾態支援**：系統支援動態切換並生成四種標準貝爾態：$|\Phi^+\rangle$, $|\Phi^-\rangle$, $|\Psi^+\rangle$, $|\Psi^-\rangle$，並自動映射對應之量子邏輯閘 (H, CNOT, X, Z)。
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

### 2. 獨立執行檔版本 (免安裝環境)
若您不想配置 Python 環境，請依照以下步驟操作：
1.  前往 [Releases](../../releases) 頁面下載 `QuantumSimulator.zip`。
2.  解壓縮至任意資料夾（請勿移動解壓後的資料夾內部結構）。
3.  執行 `QuantumSimulator.exe` 即可啟動模擬器。

*注意：若移動 `_internal` 資料夾或其中的 DLL 檔案，將導致程式無法載入 Python 運行時環境。*

## 技術來源與致謝 (Credits & Acknowledgments)

本專案之底層量子模擬運算核心由以下開源專案支援，特此致謝：

*   **C++ 模擬引擎**：[Qubit_Simulation](https://github.com/ufve0704terfy/Qubit_Simulation)
*   **技術提供者**：[ufve0704terfy](https://github.com/ufve0704terfy)

該核心負責處理高精度量子態演化及物理誤差模型之運算，本專案則基於此引擎開發前端自動化路由與視覺化介面。