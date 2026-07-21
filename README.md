# 客製化 MRP 系統 — 本機測試版

依據 `MRP__規格書v16.md` 建置的本機測試系統。後端 FastAPI + SQLite,前端 React(Vite)。
僅供本機開發測試使用,未包含帳密登入、部署設定。

## 系統需求

- Python 3.11+
- Node.js 18+

## 啟動方式

### 1. 後端(FastAPI + SQLite)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 建立示範資料(多層 BOM:原料→半成品→成品→組合禮盒,含刻意製造的缺口)
python -m app.seed

# 啟動 API(預設 http://127.0.0.1:8000)
uvicorn app.main:app --reload --port 8000
```

首次執行 `python -m app.seed` 會清空並重建 `backend/mrp_local.db`(SQLite 檔案型資料庫,免安裝資料庫伺服器)。
若不想用示範資料、想從空白開始,略過此步驟即可(啟動 API 時會自動建立空白資料表)。

### 2. 前端(React + Vite)

另開一個終端機:

```bash
cd frontend
npm install
npm run dev      # 預設 http://127.0.0.1:5173
```

Vite 開發伺服器已設定 `/api` proxy 轉發至 `http://127.0.0.1:8000`,啟動後直接開啟
`http://127.0.0.1:5173` 即可使用,不需另外設定 CORS 或 API 網址。

## 角色權限模擬

本機測試版未做正式登入,改以畫面右上角的「目前操作角色」下拉選單模擬三種角色
(透過 HTTP Header 傳遞給後端,非安全機制,僅供功能測試):

| 角色 | 說明 |
|---|---|
| 系統管理員(admin) | 所有操作 |
| 採購人員(procurement) | 可登記在途採購、確認到貨、標記/取消忽略缺口 |
| 唯讀訪客(viewer) | 僅可查詢,執行上述操作會被拒絕(403) |

## 建議的測試流程(對應規格書第4節模組)

1. **商品管理 / BOM 管理**:若未執行 seed,可先手動建立商品與 BOM,或用批次匯入(新增/更新兩介面各自的 CSV/Excel 範本欄位見畫面說明)。
2. **通路管理**:建立通路(大宗/飯店/B2C),於「資料匯入中心」上傳大宗季預測、飯店月預測。
3. **資料匯入中心**:上傳銷貨/銷退歷史(供 B2C 近3月均量+YOY 計算)、每日庫存快照。
4. **MRP 運算儀表板**:點選「執行 MRP 運算」,即可看到淨需求、可銷售天數、缺貨警示。
5. **缺口追溯**:選一個組合品/成品,沿 BOM 逐層往下看每個節點的缺口狀態。
6. **採購建議**:對觸發缺口的商品「登記在途」或「忽略」;在「在途清單」分頁確認到貨(支援部分到貨)。
7. **忽略清單複核**:查看目前被忽略的商品,或取消忽略。
8. **加工配送管理**:建立加工廠/包裝廠、匯入委外加工排程(ERP 匯出格式),輸入原料/成品可分配量產生配送清單。
9. **系統設定/權限**:查看角色權限說明與異動紀錄(交接用)。

## 專案結構

```
backend/
  app/
    models.py          # 15 張資料表(對應規格書 2.1~2.15)
    schemas.py          # Pydantic 讀寫模型
    database.py          # SQLite 連線設定
    deps.py              # 簡易角色權限模擬
    seed.py               # 示範資料腳本
    routers/              # 各模組 API 路由
    services/
      bom_service.py           # BOM 多層展開(3.1)
      forecast_service.py       # 三通路需求預測(3.2)
      demand_explosion.py       # 跨節點相依需求展開(供 MRP 引擎使用)
      mrp_engine.py              # 缺貨觸發/淨需求/建議採購量/前置時間反推(3.3, 3.4, 3.6)
      gap_trace_service.py       # 缺口追溯
      import_service.py           # 各模組批次匯入邏輯(含每日庫存特殊規則 2.7.1)
      distribution_service.py      # 原料/成品配送清單分配邏輯(3.7)
      changelog_service.py          # 異動紀錄

frontend/
  src/
    api.js                # API client(自動帶入角色 Header)
    context/UserContext.jsx # 角色切換狀態
    components/Layout.jsx    # 側邊選單 + 角色切換 UI
    pages/                     # 對應規格書第4節各功能模組頁面
```

## 已知簡化之處(本機測試版,非正式系統)

- 無正式登入/帳密機制,角色以前端下拉選單模擬(HTTP Header 傳遞)。
- `suggested_order_deadline` 採「該節點自身可銷售天數 − 自身前置時間」計算;由於下層節點的需求
  已經是上層需求逐層展開後的相依需求(demand_explosion),「逐層反推」透過各節點各自套用自己的
  前置時間自然達成,細節見 `mrp_engine.py` 內註解。
- B2C 預測的「近3個月」定義為運算月份往前推的3個完整月份(不含當月),「去年同期」為同一組月份
  往前推一年;此為規格書未完全明確之處的合理實作選擇。
