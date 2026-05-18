<table>
  <thead>
    <tr>
      <th style="text-align:center"><a href="README_ja.md">日本語</a></th>
      <th style="text-align:center"><a href="README.md">English</a></th>
    </tr>
  </thead>
</table>

# agent-room

agent-room は、LM Studio およびその他の OpenAI 互換ローカルチャットサーバー向けの、ローカルファースト型マルチエージェント議論ワークスペースです。ロールベースのエージェントの設定、複数ターンの会話の実行、参考資料の添付、再利用可能なプリセットの保存を行うための React UI を提供します。また、JSON ファーストの API および CLI ワークフローも公開しており、他の AI エージェントが機能を検出し、実行を起動し、ブラウザ UI を操作することなく保存されたトランスクリプトを読み取ることができます。

## 目次

- [プレビュー](#preview)
- [機能](#features)
- [必要要件](#requirements)
- [クイックスタート](#quick-start)
- [設定](#configuration)
- [アプリの使い方](#using-the-app)
- [エージェント API および CLI](#agent-api-and-cli)
- [開発](#development)
- [テスト](#testing)
- [プロジェクト構成](#project-structure)
- [トラブルシューティング](#troubleshooting)
- [ライセンス](#license)

## プレビュー

<img src="UI-image/UI-main.png" alt="agent-room シミュレーションビュー" width="480">

アクティブなトランスクリプト、エージェントの返答、添付ファイル、および実行コントロールを表示するシミュレーションビュー。

<img src="UI-image/UI-setting.png" alt="agent-room オーケストレーション設定ビュー" width="480">

プリセット、エージェントペルソナ、モデル ID、会話パターン、最大ターン数、および自動エージェント下書き作成のためのオーケストレーションビュー。

## 機能

- 名前、ペルソナ、カラー、モデル ID を持つ最大 8 つのエージェントを設定できます。
- ラウンドロビンまたはフリーフロー方式の発言者選択で会話を実行できます。
- Server-Sent Events 経由で UI のストリーミング実行を行い、アクティブな会話をキャンセルできます。
- プリセットを `./data/presets/` に、会話を `./data/conversations/` に保存します。
- プリセット JSON ファイルの保存、インポート、エクスポート、リロードができます。
- `trafilatura` で正規化された HTML/テキストとして取得した URL 参照を添付できます。
- 最大 10 MB、1 辺最大 4096 px の PNG、JPEG、または WebP 画像を添付できます。
- テーマからエージェントペルソナの下書きを作成するよう、設定済みのローカルモデルに依頼できます。
- マニフェストの検出、プリセットの参照、非ストリーミング実行、トランスクリプトの読み取りのための、エージェント指向の JSON API および CLI を使用できます。
- ビルド済みの React アプリを単一のローカルプロセスで FastAPI から提供します。

## 必要要件

- macOS 26 以降。
- Python 3.13 以降。
- Node.js 24 以降および npm。
- `uv`。
- LM Studio、またはモデルが読み込まれた他の OpenAI 互換チャットサーバー。
- `OPENAI_BASE_URL` でアクセス可能なローカルチャット API（デフォルト: `http://localhost:1234/v1`）。

## クイックスタート

リポジトリのルートから:

```bash
./start.sh
```

ランチャーは必要に応じて `.env.example` から `.env` を作成し、`uv sync` で Python 依存関係をインストールし、ビルド済み UI が存在しないまたは古い場合はフロントエンド依存関係をインストールし、React フロントエンドをビルドし、`127.0.0.1:${APP_PORT:-8000}` で FastAPI を起動し、`/api/health` が応答した後にアプリを開きます。

ランチャーターミナルで `Ctrl+C` を押すか、以下のコマンドを実行してアプリを停止します:

```bash
./stop.sh
```

## 設定

`.env.example` を手動で `.env` にコピーするか、`./start.sh` に作成させます。

| キー | デフォルト | 用途 |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://localhost:1234/v1` | OpenAI 互換 API のベース URL（通常は LM Studio）。 |
| `OPENAI_API_KEY` | `lm-studio` | 設定済み API に送信されるベアラートークン。 |
| `DEFAULT_MODEL` | `google/gemma-4-e2b` | 新しいエージェントおよびフォールバックモデルリストで使用されるデフォルトモデル ID。 |
| `MAX_TURNS` | `10` | バックエンドのデフォルト最大ターン数。 |
| `LOG_LEVEL` | `info` | Python ログレベル。 |
| `APP_PORT` | `8000` | ローカル FastAPI ポート。 |
| `APP_HOST` | `127.0.0.1` | ローカル FastAPI バインドホスト。ループバックのみに設定してください。 |

フロントエンドは `VITE_API_BASE_URL` も読み取ることができます。未設定の場合、API 呼び出しは `/api/models/` などの同一オリジンパスを使用します。

## アプリの使い方

1. LM Studio を起動し、チャットモデルを読み込みます。
2. `./start.sh` を実行します。
3. オーケストレーションビューを開きます。
4. エージェントを編集し、ラウンドロビンまたはフリーフローを選択し、最大ターン数を設定します。
5. 設定を再利用したい場合はプリセットを保存します。
6. シミュレーションビューを開きます。
7. プロンプトを入力し、必要に応じて URL や画像を添付し、実行を開始します。
8. 必要に応じて UI からアクティブな実行を停止します。

生成されたプリセットおよび会話の JSON ファイルは、意図的に Git で無視されます。

## エージェント API および CLI

agent-room には、ブラウザ指向の SSE ストリームではなく完全な JSON 結果を必要とする自律型呼び出し元向けの非ストリーミングインターフェースが含まれています。

### HTTP

機械可読な機能を確認:

```bash
curl http://127.0.0.1:8000/api/agents/manifest
```

保存済みプリセットを完了まで実行:

```bash
curl -X POST http://127.0.0.1:8000/api/agents/run \
  -H 'Content-Type: application/json' \
  -d '{"preset_id":"YOUR_PRESET_ID","prompt":"このタスクについて議論してください。","max_turns":3}'
```

実行エンドポイントは、`preset_id` の代わりにインラインの `preset` オブジェクト、オプションの `attachments`、および既存のトランスクリプトを継続するためのオプションの `conversation_id` も受け付けます。

主な API ルート:

| メソッド | パス | 用途 |
| --- | --- | --- |
| `GET` | `/api/agents/manifest` | エージェント向けの機能とストレージの場所を返します。 |
| `POST` | `/api/agents/run` | プリセットを完了まで実行し、JSON を返します。 |
| `GET` | `/api/presets/` | 保存済みプリセットを一覧表示します。 |
| `GET` | `/api/conversations/` | 保存済み会話を一覧表示します。 |
| `GET` | `/api/conversations/{conversation_id}` | 完全なトランスクリプトを読み取ります。 |
| `POST` | `/api/chat/run` | Server-Sent Events 経由で UI 指向の会話をストリーミングします。 |

### CLI

CLI は API と同じローカルストレージおよびオーケストレーションコードを使用します:

```bash
uv run python -m backend.app.cli manifest
uv run python -m backend.app.cli presets
uv run python -m backend.app.cli conversations
uv run python -m backend.app.cli show-conversation CONVERSATION_ID --format text
uv run python -m backend.app.cli run --preset-id YOUR_PRESET_ID --prompt "このタスクについて議論してください。"
```

プリセットファイルから実行したり、標準入力でプロンプトテキストをパイプすることもできます:

```bash
printf 'これらの実装オプションを比較してください。' | \
  uv run python -m backend.app.cli run --preset-file ./data/presets/example.json
```

CLI の出力はデフォルトで JSON 形式です。`run` および `show-conversation` は、コンパクトなトランスクリプト出力のために `--format text` をサポートしています。

## 開発

依存関係をインストール:

```bash
uv sync
cd frontend
npm install
```

フロントエンドをビルド:

```bash
cd frontend
npm run build
```

リポジトリのルートからバックエンドを実行:

```bash
uv run python -m backend.app.main
```

フロントエンドのみの開発では、Vite が `127.0.0.1:8000` のバックエンドに `/api` をプロキシします:

```bash
cd frontend
npm run dev
```

## テスト

バックエンドのユニットテストを実行:

```bash
uv run python -m unittest discover -s backend/tests
```

Ruff を実行:

```bash
uv run ruff check .
```

フロントエンドのビルドを検証:

```bash
cd frontend
npm run build
```

## プロジェクト構成

```text
backend/app/
  api/             FastAPI ルートモジュール。
  orchestration/   エージェントプロンプティング、ターン選択、ストリーミング、JSON 実行完了。
  storage/         プリセットおよび会話の JSON 永続化。
  tools/           URL および画像添付ヘルパー。
frontend/src/
  components/      再利用可能な React UI コンポーネント。
  lib/             API クライアント、型、エクスポートヘルパー、Zustand ストア。
  routes/          シミュレーションおよびオーケストレーション画面。
data/
  presets/         ランタイムプリセット JSON ファイル。
  conversations/   ランタイム会話 JSON ファイル。
```

## トラブルシューティング

- 起動時にポートが使用中と表示される場合は、既存のリスナーを停止するか、別のポートで実行してください（例: `APP_PORT=8001 ./start.sh`）。
- UI がモデルを読み込めない場合は、ローカルチャットサーバーが起動していること、モデルが読み込まれていること、および `OPENAI_BASE_URL` が正しい `/v1` エンドポイントを指していることを確認してください。
- 選択したモデルが画像を処理できない場合でも、agent-room は画像が添付されたことをテキストノートとして含めます。
- URL 添付が失敗する場合は、URL が `http` または `https` であり、バックエンドのサイズ制限内のテキストまたは HTML コンテンツを返すことを確認してください。

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
