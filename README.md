# AI_stock_market_daily

台股監控與提醒程式。程式會抓取市場資料，依照加權模型產生 HTML Email 報告與社群圖片，目前主要追蹤台灣加權指數、台積電、聯發科、台達電、鴻海、廣達、緯創、緯穎。

正式工作目錄：

C:\Users\zergv\Documents\GitHub\AI_stock_market_daily

GitHub repo：

https://github.com/ryan-AI-stock/AI_stock_market_daily

目前主要分支：

main

## 主要檔案

- stock_market_tracking_system.py：主程式，負責抓資料、計算訊號、產生 HTML/PDF 報告與上傳 Google Drive。
- config.json：追蹤標的、指標門檻、Email、重大事件、新聞與 Google Drive 設定。
- .github/workflows/daily_run.yml：GitHub Actions 每日自動執行設定。
- preview_email.bat：本機雙擊產生 HTML 預覽用。
- email_preview.html：本機執行後產生的預覽檔，不應提交到 Git。

## 目前模型

使用中長線安全投資取向的加權分數模型，分別計算買進分數與賣出分數。主要指標包含趨勢、季線支撐位置、三大法人、MACD、KD、OBV、量能、基本面趨勢、估值與乖離、匯率、利率。

BIAS60 用來判斷中期過熱或超跌。接近過熱時，買進分數會降級；當 BIAS60 顯示過熱時，買進分數會被鎖定為 0，避免追高。

新版模型特別加入：

- 季線附近支撐反彈：多頭修正或盤整中，若股價靠近季線後反彈，可列入小部位試單條件。
- 接近過熱降級：離季線過遠或接近 BIAS60 歷史高位時，即使趨勢強也不追價。
- 法人合計方向優先：三大法人合計賣超時，不會只因部分法人買超就給買進分數。
- 基本面與估值輔助：若資料源可取得，會納入營收/獲利成長、PE、PB 等中長線參考；資料不足時不硬湊分數。

## 報告呈現原則

報告上方有「評分標準」可展開區塊。

今日總覽與各股詳細指標都整理為投資者容易理解的格式：

- 市場狀態
- 操作方向
- 說明原因

例如：

大多頭 / 過熱鎖定 / 禁止追買，核心部位續抱觀察

## 交易邏輯方向

目前模型偏向風險控管與分批進出提醒，不是單純追求大多頭報酬最大化。

- 大多頭：少賣，弱賣出通常只提醒，不急著下車。
- 多頭修正：保留核心部位，中強訊號才考慮減碼。
- 盤整：較適合依訊號分批操作。
- 空頭：賣出訊號權重提高，買進訊號保守看待。

同一等級訊號連續出現時，不建議每天重複交易。

## 產出與發布

程式會產生：

- Email 完整報告。
- 自用備份 PDF，供自用 Google Drive 存檔，檔名格式為「每日台股報告_YYYYMMDD.pdf」。
- 免費觀眾固定 PDF 報告，輸出到 Google Drive 指定資料夾。

免費觀眾固定報告目前設定為：

- 固定檔名：每日台股報告.pdf
- 免費觀眾資料夾不產生日期版，避免 LINE 關鍵字回覆需要每天更換。

LINE 官方帳號關鍵字回覆只需要設定固定 PDF 的分享連結。每日更新時，程式會覆蓋同名檔案，網址不需要每天手動更改。

## 顏色規則

多數地方採用台股閱讀習慣：

- 紅色：上漲、買超、偏多
- 綠色：下跌、賣超、偏空

例外：趨勢環境目前特別設定為：

- 多頭健康：綠色
- 空頭確認：紅色

## 本機測試

在正式工作目錄執行：

python stock_market_tracking_system.py

執行後會產生 email_preview.html、免費觀眾摘要 PDF 與自用完整備份 PDF。Email 發送目前已關閉。

## GitHub Actions

GitHub Actions 設定為每天台灣時間下午 16:00 執行一次，16:15 備援觸發；程式會避免同日重複寄送。

目前 Email 發送已關閉，主要閱讀方式改為 Google Drive PDF。

Google Drive 上傳需要在 GitHub Organization 或 repo 的 Secrets 設定 GOOGLE_OAUTH_CLIENT_ID、GOOGLE_OAUTH_CLIENT_SECRET、GOOGLE_OAUTH_REFRESH_TOKEN 與 DAILY_REPORT_DRIVE_FOLDER_ID。

免費觀眾固定報告頁可用 Organization / repo Variables 設定 PUBLIC_REPORT_DRIVE_FOLDER_ID；若未設定，會使用 config.json 的 public_report.folder_id。

## 給新 Codex 聊天的接手提示

如果開新聊天，請先確認：

git status
python -m py_compile stock_market_tracking_system.py

之後所有修改、測試、commit、push 都應該在正式工作目錄進行：

C:\Users\zergv\Documents\GitHub\AI_stock_market_daily

舊的 Codex 日期資料夾不再作為主要工作區。
