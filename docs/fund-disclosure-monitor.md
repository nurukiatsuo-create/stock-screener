ファンド保有関連開示の監視
どこで状況を見るか
GitHub の Actions → Fund disclosure monitor → 実行日時 を開きます。
実行中: Collect EDINET filings with progress logs に日付単位・書類単位の進捗を表示。
終了後: Summary に取得済み日数、銘柄、提出者、原資料へのリンク、失敗理由を表示。
Artifacts: `fund-disclosures-実行番号-試行番号` に report.md、status.json、filings.json、原本PDF、日次一覧JSON、銘柄一覧、スクリーナーのスナップショットを保存（90日）。
キー未設定・通信失敗・照合漏れは赤い失敗表示。取得途中の結果も可能な限り保存。
強制停止・時間切れ時はActionsの状態を優先。status.jsonがrunningなら最終チェックポイントであり、完了ではありません。
初期設定
EDINETでAPIキーを発行します: https://api.edinet-fsa.go.jp/api/auth/index.aspx?mode=1
このリポジトリの Settings → Secrets and variables → Actions → New repository secret に、名前 `EDINET_API_KEY` とキーを登録します。キーをコード・チャット・Issueに貼らないでください。
Actions → Fund disclosure monitor → Run workflow。初回は `baseline`（90日）を選択。
SummaryとArtifactsを確認します。
日次は毎日07:05 JST（直近3日を重複取得し遅延を補う）、週次は土曜09:00 JST（7日再確認）。開始はGitHubの混雑で遅れる場合があります。
定期実行が7日以上止まった場合や監視銘柄追加時はbaselineを実行してください。過去結果との差分台帳ではなく、実行ごとに対象期間と取得日時を保存する方式です。
自動化の範囲と残る作業
これは原資料の収集と要確認銘柄の整理です。ChatGPTで予定していた調査全体を自動再現するものではありません。
`collection_complete` は一覧・提供PDFの取得処理が完了した意味で、投資判断や全資料の調査完了を意味しません。
`research_complete` は常にfalseです。ファンド月報、企業IR、運用方針、保有割合・株数、共同保有、貸借、保有目的、投資理由と決算の整合は本文精査待ちです。
レポートには全監視銘柄についてこの未確認範囲を残します。取得したreport.mdとPDFをチャットで精査すれば出典を確認しながら調査を進められます。
EDINET書類一覧の `secCode` は提出者のコードのため、投資先の照合には使いません。
`issuerEdinetCode` と金融庁のコード一覧を照合します。350/360を対象とし変更報告や訂正を含む書類概要をそのまま保持します。
提出者がファンドか事業会社か個人かは自動断定しません。5%以下の機関保有等は把握できないため、未検出を保有なしとしません。
最新コード一覧を使うため、上場廃止・コード変更に伴う対応漏れは未対応として表示します。
保有確認結果を順位に加点する処理、自動注文、scan.pyやstocks_data.jsonの書換えはありません。
Python標準ライブラリのみ使用し、有料AI APIは呼びません。
検証と根拠
`python -m unittest discover -s tests -p 'test_fund_disclosures.py' -v`
金融庁 EDINET API仕様書Version2（2026年6月）:
https://disclosure2dl.edinet-fsa.go.jp/guide/static/disclosure/download/ESE140206.pdf
GitHubの定期実行と遅延の説明:
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
