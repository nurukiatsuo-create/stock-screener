# 業績・TOPIXを接続した新高値監視

2026-11-15改訂。収益性の実証済みモデルではなく、出典と判定理由を追跡できる運用仕様。

## 判定の順序と出力

四季報抽出112銘柄を監視。各条件は独立に評価し、最後に統合する。

1. 四季報原本：source_verified=true、source_edition、source_locator、source_claim、verified_onが必要。抽出結果だけを原本確認済みとはみなさない。
2. 業績：最新の通期会社予想と前期実績の営業利益成長率20%以上、EPS成長率プラスが通常条件。四半期累計は補助情報で、通期の代わりに自動合格させない。営業利益を使えない金融業は比較基準を設計するまで個別審査。
3. 例外：通常条件未達は直ちに最終不合格にせず、上方修正・四季報独自増額・最高益の審査へ。根拠付き承認または却下が必要。
4. TOPIX：公式の完全な照合表により移行措置対象を除外。新規組み入れは実施日までS区分、実施後はA区分に属性を残す。S/Aは期待収益率を推定した順位ではない。
5. 技術：従来の過去250営業日高値、当日を除く20日平均比1.5倍、20～65本ボックス、初動3営業日、箱上限乖離3%以内を維持。
6. 流動性：5日平均の終値×出来高が4000万円以上。旧ランキングだけでなく最終候補にも適用。実際の売買代金の近似であり、価格は既存取得系の配当・分割調整基準。厳密な注文容量の評価には約定代金・板の確認が必要。
7. 資金：許容損失額・利用可能資金・流動性による上限を100株単位で試算。流動性上限は5日平均代金の1%（暫定）。許容損失額は未指定なのでnullを初期値とし、最大株数を推奨株数として表示しない。

strategy.version=3を維持し、selection_version=1を追加。candidatesは全必須条件を通過した候補のみ。technical_candidatesは技術条件のみの該当銘柄。observationsには各gateのpass/fail/unknownと理由を残す。

最終状態はcandidate/watch/pending/excludedで排他的。明確な除外理由があれば、他に未確認項目があってもexcludedとする。各条件別の集計は重複を含む。not_calculated_codesには抽出リストのうち株価計算に含まれていないコードを表示する。

## 業績と開示確認の区別

`audit/fundamental_evidence.json`は1社につき1件の現在評価する資料を保持。公表日・対象期間・比較可能性・出典と4数値が必要。過去版はgit履歴に残る。

assessmentは資料自体の評価、freshnessはその資料が今も最新かの確認状況。日付が変わっても数値評価を消さない。追加開示の確認ができなければ前回評価を表示しつつ新規候補への採用を停止する。

`audit/disclosure_checks.json`の各recordは次を保存する。

- code / checked_on / success / source_url
- evidence_key：audit_fundamentals.evidence_key(record)の値。資料・数値変更時には無効になる。
- new_disclosure_found：falseで追加開示なし、trueで新資料の再審査待ち。

実行時刻を開示確認済み時刻として記録してはいけない。現段階ではこのファイルへの登録は、実際に開示を確認した人・連携処理が行う。開示サイトの自動巡回は本改訂に含まない。

例外は根拠資料にexception_reviewを付ける。decision（approved/rejected）、reviewed_on、evidence_key、source_url、reasonが必須。承認にはgrounds（upward_revision/shikiho_revision/record_profitのいずれか）とsustainable=true、営業利益・EPSの黒字も必要。前年赤字・ゼロ基準の数値は別審査のままとし、この経路で自動承認しない。

公表時刻を持たない日付単位の評価であるため、場中の売買バックテストに転用しない。最新の112銘柄リストを過去に遡って使ったバックテストも行っていない。

## TOPIX入力

`audit/topix_membership.json`：verified / completeがtrue、JPXのsource_url、published_on、checked_on、valid_until、transition_codes、new_inclusionsが必要。new_inclusionsの要素はcode / effective_on。

valid_untilは次の見直し・再評価等を踏まえて確認者が指定する。期限切れ・重複・区分矛盾・非公式出典・未来の確認記録は確認待ち。リストが空でも未確認なら非該当とは判定しない。今回の初期ファイルは未確認状態であり、683/35という件数を推測で埋めていない。

## 日次処理・互換性

scan.pyが日足を計算してから必ずapply_selectionを呼ぶ。全件取得失敗では既存JSONを上書きしない。XTKS営業日カレンダーと既存の16時JST確定待ちを使用し、全銘柄同時に古い日付でも検出する。価格日と業績判定日は別表示。

保存済み価格の選別だけやり直す場合：`python refresh_selection.py --as-of YYYY-MM-DD`。これは株価を取得せず、data_date / updated_atを変更しない。screening_updated_atだけ更新する。as-ofは終日評価を意味し、場中の再現用ではない。

GitHub Actionsは平日16時JSTに計算し、関連コード・根拠データの変更時にも実行。JSONと業績監査レポートを保存する。

Scriptableの既存v6は候補配列を引き続き読める。業績・TOPIX別の未確認数や除外理由を表示するには、端末内のコードをNewHighMonitor.js（v7）に置き換える。GitHubのJS更新だけでは端末内のコードは自動更新されない。

## 未完了の検証・資料

四季報原本の照合、全銘柄の業績根拠登録、TOPIX完全リスト照合、許容損失額設定、実約定・コストを含むバックテストは未完了。テスト合格は収益性の証明ではない。技術のみ／業績追加／TOPIX追加の順で、その時点の資料を使い比較検証する。

## 株価取得制限への対応

同時取得数を4に抑制。部分取得失敗時は、期待する最新確定取引日と同じ日付の有効な保存済み観測だけ再利用する。古い営業日の価格、無効な箱、同一コードで矛盾する保存値は再利用しない。price_source / price_cached_updated_atとprice_fetch_summaryで出所を示し、失敗ログを消さない。全件取得失敗時の既存出力保護は維持する。

2026-11-15の初回再計算では取得先のアクセス制限が発生。部分取得と2026-11-13付保存データを統合した。再利用分で未保存の流動性指標は未取得のままとし、推測で補完しない。
