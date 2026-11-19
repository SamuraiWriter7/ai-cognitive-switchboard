# AI Cognitive Switchboard v0.1

- プロトコルバージョン `0.1`
- リポジトリ `ai-cognitive-switchboard`
- 文書種別 規範仕様

## 1. 目的と適用範囲

**AIはスイッチを要求できるが、自分で通電できない。**

AI Cognitive Switchboardは、対象AIが使用する実行環境の設定について、変更の要求、認可、適用の確認、停止を分離するプロトコルである。「認知」は実行環境の設定を指し、モデル内部の変更、意識、推論品質、出力が指定モードに完全に従うことを意味しない。

v0.1は固定5スイッチ、適用範囲、期限、失効および検証に必要な最小限の記録を定義する。スイッチの設定は、ツール、データ、ネットワーク、外部書き込みに対する権限を付与しない。動的なポリシー生成、記憶の保存方式、課金、他仕様との正式な相互運用は対象外とする。

## 2. 規範用語と信頼境界

**MUST** は必須、**MUST NOT** は禁止、**SHOULD** は合理的な理由がない限り従う推奨とする。

| 役割 | 責務 |
| --- | --- |
| Subject Agent | 変更を要求できる。認可、レビュー、適用・停止の証明を発行できない |
| Authorizer | 認証済みの人間、固定ポリシーの評価機構、または認可権限を持つ外部コントローラーとして認可する |
| Controller | 認可と適用条件を確認し、設定を適用・停止し、観測結果を記録する |
| Runtime Gate | 処理開始と各保護操作の直前に、最新の有効性と操作権限を検証する |

AuthorizerとControllerは同一サービスでもよい。ただし対象AIが認証情報、ポリシー、信頼された記録ストア、確認記録、適用コード、実行時ゲートを改変できない境界を設けることをMUSTとする。`kind` や `actor_id` の自己申告を本人性の証拠として扱ってはならない（MUST NOT）。固定ポリシーによる認可は、対象AIが変更できない版に拘束する。

## 3. Switch State

設定は以下の5項目をすべて含む。省略による継承と部分更新は認めない。

| フィールド | 値 | 意味 |
| --- | --- | --- |
| `memory` | `OFF` / `READ_ONLY` / `READ_WRITE` | 管理対象の永続記憶へのアクセス設定 |
| `external_brain` | `OFF` / `ON` | 登録済みの外部知識アダプターの選択 |
| `reasoning_mode` | `default` / `creative` / `skeptical` / `audit` | 版を固定した推論プロファイルの選択 |
| `question_pack` | `null` または空でないID文字列 | 版を固定した問いセットの選択 |
| `human_review_required` | boolean | 設定の有効化と、その設定下で行う保護操作に対する人間レビュー条件 |

`memory: OFF` は管理対象アダプターの読み書きを禁止するが、会話履歴や既存データを削除しない。`READ_ONLY` は作成、更新、削除を禁止する。`READ_WRITE` と `external_brain: ON` は設定上の選択にすぎず、操作時の独立した権限検査を省略できない。Question Pack、外部知識、その他の入力の内容を認可として解釈してはならない（MUST NOT）。

## 4. スイッチボードレコード

レコードは不変スナップショットとする。状態を進めるときは新しい `record_id` を発行し、直前のIDを `supersedes_ref` で参照する。ここで「時刻」はUTCの `YYYY-MM-DDTHH:MM:SSZ` または `YYYY-MM-DDTHH:MM:SS.sZ` 形式とし、小数秒は1〜6桁、秒は00〜59とする。実在する日時を解析して比較することをMUSTとし、文字列順で代用しない。

以下の全フィールドは必須とする。欠けているフィールドと明示的な `null` は区別する。レコードと規定の入れ子オブジェクトでは、未知のフィールドを拒否する。

| フィールド | 型・条件 |
| --- | --- |
| `protocol_version` | 固定文字列 `0.1` |
| `record_id` | 信頼された記録ストアで一意のID |
| `switchboard_id` | スイッチボードID |
| `subject_agent` | 対象AIのID |
| `status` | `requested` / `authorized` / `active` / `held` / `denied` / `expired` / `revoked` / `completed` |
| `requested_state` | 完全なSwitch State |
| `authorized_state` | 完全なSwitch State、または `null` |
| `effective_state` | 完全なSwitch State、または `null` |
| `requested_by` | `{kind, actor_id}`。`kind` は `agent` / `human` / `controller` |
| `authorization` | §5.1のオブジェクト、または `null` |
| `activated_by` | `{kind, actor_id}` または `null`。`kind` は `controller` に固定 |
| `scope` | `{task_id, session_id, resource_refs}`。IDは空でない文字列、リソース参照は重複のない文字列配列 |
| `created_at` | 初回要求の作成時刻。後続レコードでも変えない |
| `expires_at` | この要求チェーンの期限。`created_at < expires_at` を満たす |
| `activated_at` | 現在の設定を有効化した時刻、または `null` |
| `human_review_required` | 実際に適用されるレビュー条件のboolean |
| `human_review` | §5.2のオブジェクト、または `null` |
| `bindings` | `{mode_profile_ref, memory_ref, external_brain_ref, question_pack_ref}`。各値は不変参照、または `null` |
| `trace_id` | 要求チェーンの相関ID |
| `receipt_refs` | §7.3のReceiptを指す、重複のない文字列配列 |
| `reason` | 空白のみではない説明。判断、保留、拒否、停止の根拠を記録する |
| `supersedes_ref` | 初回は `null`、以降は直前の `record_id` |

IDおよび参照は空白のみではない文字列とする。`effective_state: null` は、このレコードに基づく稼働設定が存在しないことを示す。アダプターが実際に停止したことの証明ではない。

## 5. 認可・人間レビュー・参照

### 5.1 認可

`authorization` の全フィールドを以下とする。

| フィールド | 型・条件 |
| --- | --- |
| `authorization_id` | 認可ID |
| `kind` | `human` / `policy` / `controller` |
| `actor_id` | 認可主体ID |
| `authority_ref` | 認可主体の権限根拠を指す信頼済み不変参照 |
| `decision_ref` | 具体的な承認内容を指す信頼済み不変参照 |
| `authorized_at` | 認可時刻 |
| `valid_until` | 認可の失効時刻。上限を含まない |

認可の根拠は、当該要求チェーン、対象AI、完全な `authorized_state`、`scope`、`bindings`、適用されるレビュー条件と有効期間に拘束する。参照を解決し、実際の判定内容と照合することをMUSTとする。参照文字列が存在するだけでは認可を証明しない。

`authorization` と `authorized_state` は同時に存在するか、双方とも `null` でなければならない。認可がある場合は `created_at <= authorized_at < expires_at <= authorization.valid_until` を満たす。Authorizerは要求とは異なる設定を承認できる。その場合は相違と理由を記録し、変更後の設定に対する必要なレビューを確認する。

### 5.2 人間レビュー

`human_review` は `review_id`、`reviewer_id`、`decision`、`reviewed_at`、`valid_until`、`evidence_ref` を持つ。`decision` は `approved` または `rejected` とする。レビューの証拠には、認証済みの人間による判断であることと、対象AI、設定、適用範囲、参照およびレビュー対象が一致することを求める。

レコードの `human_review_required` は、要求State、承認Stateが存在する場合はそのState、固定ポリシーそれぞれのレビュー条件の論理和とする。承認Stateがある場合は、その同名フィールドとレコード上の値が一致しなければならない。`true` が要求された場合、`false` へ緩和してはならない（MUST NOT）。

`authorized` と `active` でレビュー必須の場合、承認済みのレビューが必要であり、`created_at <= reviewed_at <= authorized_at < expires_at <= human_review.valid_until` を満たす。拒否されたレビュー、本人性が確認できないレビュー、AIによる代理レビューを承認として扱わない。設定のレビューと個別操作のレビューは別であり、会話中の返答や問い返しもレビューの代わりにはならない。

### 5.3 Bindings

`authorized_state` が存在するとき、以下を満たすことをMUSTとする。

| 参照 | 条件 |
| --- | --- |
| `mode_profile_ref` | 選択したモードの版を固定した参照が必須 |
| `memory_ref` | `memory` が `OFF` なら `null`、それ以外は参照が必須 |
| `external_brain_ref` | `external_brain` が `OFF` なら `null`、`ON` なら参照が必須 |
| `question_pack_ref` | `question_pack` が `null` なら `null`、それ以外は該当IDの版を固定した参照が必須 |

非null参照はすべて `scope.resource_refs` に含まれ、登録済みの変更不能な版へ解決できなければならない。参照先への操作権限は別途検証する。要求段階では参照をすべて `null` にできる。未登録・可変・解決不能な参照では有効化しない。

## 6. 状態と許可される遷移

| 状態 | 必須条件 |
| --- | --- |
| `requested` | チェーンの起点。`supersedes_ref`、承認State、認可および実効Stateは `null` |
| `authorized` | 直前の要求または保留からの認可。承認Stateと認可があり、実効Stateは `null` |
| `active` | 有効な認可、承認State、Controller、有効化時刻、一致する適用Receiptがある。実効Stateと承認Stateが全5項目で一致する |
| `held` | 実効Stateは `null`。処理を許可せず、未解決の条件を `reason` に記録する |
| `denied` | 実効Stateは `null`。拒否理由を記録する |
| `expired` | 実効Stateは `null`。その遷移の検証に用いる信頼済み時刻が `expires_at` 以上である |
| `revoked` | 実効Stateは `null`。認可を履歴として保持し、認可または必須レビューの取消しを `reason` に記録する。根拠は信頼された記録から照合する |
| `completed` | 実効Stateは `null`。終了理由と確認済みの停止Receiptを記録する |

`active` 以外では `activated_by` と `activated_at` は `null` とする。認可後の非稼働状態では、認可と承認Stateを変更せず履歴として保持する。過去の適用と停止の結果は先行レコードとReceiptから確認する。

| 遷移元 | 許可する遷移先 |
| --- | --- |
| `requested` | `authorized` / `held` / `denied` / `expired` |
| `authorized` | `active` / `held` / `revoked` / `expired` |
| `active` | `held` / `revoked` / `expired` / `completed` |
| `held` | `authorized` / `denied` / `revoked` / `expired` |
| `denied` / `expired` / `revoked` / `completed` | なし |

チェーンを検査する際は、直前参照の欠落、循環、分岐、および古い先行レコードからの更新を拒否する。認可は初回の `authorized` で追加し、それ以前は `authorization` と `authorized_state` を `null` とする。最初のレコードは `requested` とし、後続レコードは同じ `switchboard_id`、`subject_agent`、`trace_id`、`requested_by`、`requested_state`、`scope`、`created_at`、`expires_at` を維持する。一度認可した `authorized_state`、`authorization`、`bindings` および承認済みのレビュー条件・根拠は変更しない。認可後にこれらを変える場合、または終端後に再試行する場合は、新しい要求チェーンを開始する。

`held` から直接 `active` に戻してはならない（MUST NOT）。再開には有効な認可、レビュー、範囲、参照、期限を再検証する。前の適用が不完全だった場合や停止が未確認の場合は、その隔離または停止が確認されるまで再適用しない。期限切れや失効を `held` に置き換えて認可を維持することはできない。

## 7. 適用、失効、停止

### 7.1 適用

1. Controllerは対象・適用範囲を確認し、最新レコードが `authorized` であることと、認可、レビュー、参照、期限および独立した権限を検証する。
2. 保護された処理を閉じたまま設定を準備する。同一実行環境の同じ対象AI・タスク・セッションには、同時に複数の設定を有効化してはならない（MUST NOT）。直列化または比較更新によって競合を防ぐ。
3. 実際のアダプター設定を観測し、全5項目が承認Stateと一致したことを確認する。`authorized_at <= activated_at < expires_at` を満たし、適用を記録する直前にも認可と必要なレビューが有効であることを確認する。
4. 一致を確認した適用Receiptを伴う `active` を、最新レコードとして確定してからゲートを開く。
5. 部分適用、不一致、確認不能の場合はゲートを閉じたまま `held` とし、途中まで反映された設定の隔離または取り消しを行う。適用失敗または未確認のReceiptを `held` レコードに関連付け、隔離や停止の観測も記録する。部分適用を成功と記録してはならない（MUST NOT）。

### 7.2 期限切れ・失効時の扱い

時刻が `expires_at` に達するか、認可が取り消され、または必須レビューが無効になった場合、現在の記録がまだ `active` であっても新規の保護操作を許可してはならない（MUST NOT）。認可やレビューの現況を確かめられない場合もゲートを閉じる。

稼働を終えるときは、ゲートを閉じてから、管理対象の処理を停止し、対象アダプターを切り離し、その結果を観測する。`expired` や `revoked` は許可が無効になったことを表す。その記録のために停止確認を待ってはならない（MUST NOT）。既に稼働していた場合や部分適用が起きていた場合、停止が未確認なら完全適合とは判定しない。`completed` は停止が確認できた場合にだけ記録する。

取消不能な既発生の効果は停止によって消えない。観測できた効果と未確認の事項を別々に記録する。以前の設定に戻すときも、過去のStateをコピーして有効化せず、現在有効な認可の下で新しい要求から開始する。

### 7.3 確認記録（Receipt）

Receiptには `receipt_id`、`record_ref`、`controller_id`、`event`、`observed_at`、`result`、`evidence_ref` を含める。`event` は `applied` / `stopped` / `recovery`、`result` は `confirmed` / `failed` / `unknown` とする。`observed_at` は観測時刻とし、`evidence_ref` は観測根拠を指す。

`active` に必要なReceiptは、当該レコードを指す `applied/confirmed` で、発行主体が `activated_by.actor_id` と一致し、観測した全項目が承認Stateと一致しなければならない。観測時刻は `authorized_at <= observed_at <= activated_at` を満たす。

`stopped/confirmed` は、対象となる適用試行を特定でき、ゲートの閉鎖と、管理対象の処理・アダプターの停止または同等の隔離を確認した場合に限る。`record_ref` は停止対象の適用試行を特定できるレコードを指す。停止が未確認の場合は `failed` または `unknown` として記録し、確認済みと読み替えない。終端レコード確定後に得た停止Receiptは、先行レコードを参照する追記として信頼された記録ストアに残す。終端レコード本体は書き換えない。`recovery/confirmed` はそれだけで認可や `active` の根拠にならない。

## 8. 実行時ゲート

実行環境は処理開始時と各保護操作の直前に、以下をすべて検証することをMUSTとする。

1. 信頼されたストアから取得した最新レコードが `active` である。
2. 対象AI、タスク、セッション、および当該操作が利用する管理対象リソースが `scope` に含まれる。
3. 現在時刻が `activated_at <= now < expires_at` を満たす。
4. 認可、必須レビューおよび不変参照は現在も有効であり、認可された内容と一致する。
5. 観測可能な実際の設定は承認Stateと一致し、操作自体が独立した権限と必要な操作別レビューを満たす。

いずれかが不明または不成立なら、操作を許可しない。旧レコードや会話中の返答によってゲートを再開してはならない（MUST NOT）。過去の `active` レコードは履歴として有効でも、現在の実行許可にはならない。

## 9. 適合検査

| 検査 | 判定対象 |
| --- | --- |
| 構造検査 | `schemas/switchboard-v0.1.schema.json` が単一レコードの必須項目、型、列挙、未知項目、状態別のnull条件などを検査する |
| 意味検査 | `scripts/validate.py` が、設定の完全一致、レビュー条件の緩和、時刻の順序、設定と参照の整合を検査する。遷移や根拠は、先行レコードと信頼できる検証入力が与えられた場合に照合する |
| 実行時検査 | 主体認証、認可根拠、現在の状態・失効情報・独立権限、実際の適用と停止を、実行環境または明示した模擬環境で検査する |

各レイヤーの結果を区別する。規則への明示的な違反はFAILとする。必要な根拠を取得できず違反の有無を判定できない場合は未検証とし、そのレイヤーのPASSにはしない。例えば、単一の `active` レコードから、参照先の認可やReceiptの真正性を結論づけてはならない（MUST NOT）。

### 9.1 最小リポジトリの例

| パス | サンプル検証での期待結果 |
| --- | --- |
| `examples/valid-switch.json` | PASS。認可と適用がレコード内で整合する |
| `examples/denied-switch.json` | PASS。拒否が正しく記録され、実効Stateが存在しない |
| `examples/unauthorized-activation.json` | FAIL。認可なしで `active` を名乗る |

この表のPASSはサンプルで実施した検査の結果であり、実行環境の適合証明ではない。FAILが期待された例では、仕様違反を検出したときにテストが成功する。

### 9.2 実行環境で確認するケース

| ケース | 期待する動作 |
| --- | --- |
| 認可された5項目のうち一部だけが適用された | `active` を記録せず、処理を保留して隔離または取り消しを確認する |
| 時刻が `expires_at` に一致した | 次の保護操作を許可しない。停止が未確認なら停止済みと記録しない |
| 有効化後に認可が取り消された | 期限内でも次の保護操作を拒否する。旧レコードを使った再開も拒否する |
| 停止の観測が失敗した | ゲートを閉じたままとし、完了とは判定しない |
| AIが認可主体や人間レビューを自己申告した | 本人性と権限を独立に検証し、根拠がなければ有効化しない |
| 設定外・範囲外の操作を要求した | スイッチが有効でも操作を拒否する。`READ_ONLY` での書き込みも同様 |

## 10. 後続版との境界

v0.1では固定5スイッチを維持する。`companion` プロファイル、9状態の伴走型推論FSM、認知クラッチはv0.2の検証候補であり、この版では有効なモードや状態として追加しない。

Switchboardは「どの設定を使ってよいか」、伴走型推論FSMは「認可された設定のもとでいつ問い返し、中断し、再開するか」を担当する。問い返しへの返答は方向を更新できるが、認可、権限上のレビュー、失効の解除を代替しない。

HVIによる動的な問い返し判定は比較実験後の候補とする。Memory Cartridge、Question Packの詳細型、TACPや外部権限プロトコルとの接続も独立した拡張候補であり、v0.1での相互運用適合は宣言しない。
