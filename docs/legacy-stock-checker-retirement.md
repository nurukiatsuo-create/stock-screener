# stock-checker 定時実行の停止手順

2026-10-14時点：停止未反映。GitHub連携はstock-checkerへの書込みが403で拒否されます。本体stock-screenerのREADME更新は成功しています。

対象は旧固定8銘柄の3ワークフローだけです。各ファイルのscheduleブロックを削除し、workflow_dispatchとjobsを残します。リポジトリ・コード・履歴は削除しません。復旧はコミット差分を戻します。

## .github/workflows/update.yml

変更後のファイル全文：

```yaml
name: Daily Stock Signal Update

on:
  # Retired 2026-10-14: scheduled runs removed; manual runs retained.
  workflow_dispatch: # 手動実行ボタン


permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install libraries
        run: pip install yfinance pandas numpy matplotlib

      - name: Run calculation script
        run: python generate.py

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add stock_data.json
          git diff --staged --quiet || (git commit -m "Auto update signals and charts [skip ci]" && git push)

```

## .github/workflows/ daily_check.yml

変更後のファイル全文：

```yaml
name: daily_check

on:
  workflow_dispatch:
  # Retired 2026-10-14: scheduled runs removed; manual runs retained.

jobs:
  run-checker:
    runs-on: ubuntu-latest
    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python環境をセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: 必要なライブラリをインストール
        run: |
          pip install yfinance pandas matplotlib mplfinance

      - name: ポートフォリオ判定を実行
        run: |
          if [ -f check_all_portfolio.py ]; then
            python check_all_portfolio.py
          elif [ -f check_stock.py ]; then
            python check_stock.py
          fi

      - name: 生成データとチャート画像をGitHubに保存
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add result.json chart*.png
          git commit -m "Auto update stock data [daily_check]" || exit 0
          git push

```

## .github/workflows/check_all.yml

変更後のファイル全文：

```yaml
name: check_all

on:
  workflow_dispatch:
  # Retired 2026-10-14: scheduled runs removed; manual runs retained.

jobs:
  run-checker:
    runs-on: ubuntu-latest
    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v4

      - name: Python環境をセットアップ
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: 必要なライブラリをインストール
        run: |
          pip install yfinance pandas matplotlib mplfinance

      - name: 総合ポートフォリオ判定を実行
        run: |
          python check_all_portfolio.py

      - name: 生成データとチャート画像をGitHubに保存
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add result.json chart*.png
          git commit -m "Update portfolio charts and data" || exit 0
          git push

```

変更後は3ファイルにscheduleがないこと、workflow_dispatchとjobsが残ることを確認します。既存の待機・実行中ジョブの確認も必要です。stock-screenerとFund disclosure monitorは変更しません。起動遅延の改善は未検証です。
