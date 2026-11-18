# 日本株・新高値監視

四季報の一次選別をGemini NotebookLMで行い、選別後の業績更新、TOPIX、流動性、日足・ボックスをこのリポジトリで確認します。2026-11-15時点の監視母集団は112銘柄です。

## 主なファイル

| ファイル | 役割 |
|---|---|
| scan.py | 確定日足と既存技術条件の計算、最終ゲートの適用 |
| candidate_gates.py | 四季報受入れ・銘柄同一性・業績・TOPIX・流動性・価格の統合 |
| audit/shikiho_candidates_2026.json | 利用者提供のNotebookLM選別112行と受入日・行ごとの証跡 |
| audit/security_identity.json | 公式コード・社名照合、上場廃止・不一致の個別処理 |
| audit/fundamental_evidence.json | 確認済みの業績資料・数値・対象期 |
| audit/disclosure_monitors.json | 実取得できたIR一覧の監視基準と対象外の明示 |
| check_disclosure_updates.py | 追加開示の検知。新資料を自動採用しない |
| audit/topix_membership.json | 公式移行措置リストと新規組入れイベント |
| check_topix_updates.py | TOPIX公式ニュースの新規・訂正検知 |
| stocks_data.json | Scriptable用データ。株価日と再評価日を別表示 |
| NewHighMonitor.js | Scriptable v8。候補・監視・保留・除外と理由の表示 |

## 運用

GitHub Actionsは毎営業日16:00 JSTに起動し、追加開示・TOPIXニュースを確認してから株価を計算します。起動遅延があり得るため、実行時刻だけでなく`data_date`と各確認日を確認してください。

```bash
python -m unittest discover -p 'test_*.py' -v
node test_monitor.js
python check_disclosure_updates.py
python check_topix_updates.py
python scan.py
```

NotebookLM選別の受入れは、こちらで原本確認済みという意味ではありません。元のコード・社名・選定理由と受入履歴を保存し、個別の不一致・上場廃止・業績条件未確認は別判定にします。

詳細は[運用仕様](docs/selection-gates.md)を参照してください。旧相場流・PF4.11の表示は互換出力であり、現在の最終候補`strategy.candidates`と区別します。PF4.11という過去の数字を今回の運用の実証結果とは扱いません。

## 変更と検証

今回の112銘柄受入れ・TOPIX公式登録・優先7社の業績確認は[2026-11-15実施記録](docs/operation-update-20261115.md)に記録します。数値閾値・損切り・予算は変更していません。テスト合格は収益性を保証しません。
