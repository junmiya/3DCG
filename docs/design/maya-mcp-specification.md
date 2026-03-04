# Maya MCP Server 開発仕様書

## 1. 概要

テキスト説明・写真・イラストを入力として、Autodesk Maya 上で 3D モデルを生成・編集する MCP（Model Context Protocol）サーバーを開発する。

AI による入力解析と外部 3D 生成 AI を組み合わせ、あらゆるモデルタイプ（ハードサーフェス、キャラクター、環境）において、最もリアリティのある 3D モデリングを実現する。

### 1.1 ゴール

```
「椅子の写真」   → Maya 上にリアルな椅子の 3D モデルが生成される
「ドラゴンの絵」 → Maya 上にドラゴンの 3D モデルが生成される
「未来的な都市」 → Maya 上に都市環境のシーンが構築される
```

## 2. アーキテクチャ

```
                          ┌──────────────────────┐
                          │   3D Generation AI    │
                          │  (Meshy/Rodin/Tripo)  │
                          └──────────┬───────────┘
                                     │ REST API
                                     │ (OBJ/FBX/GLB)
┌─────────────┐  stdio   ┌──────────┴───────────┐  TCP Socket   ┌──────────────┐
│  AI Client   │◄────────►│    MCP Server         │◄────────────►│    Maya      │
│ (Claude等)   │   MCP    │    (Python)           │  commandPort  │              │
└─────────────┘          └──────────┬───────────┘               └──────────────┘
                                     │
                          ┌──────────┴───────────┐
                          │   Local File System   │
                          │  (入力画像/生成メッシュ) │
                          └──────────────────────┘
```

### コンポーネント構成

| コンポーネント | 技術 | 役割 |
|---|---|---|
| MCP Server | Python + `mcp` SDK | MCP プロトコルの処理、ツール定義、パイプライン制御 |
| Maya Bridge | Python socket | Maya commandPort との TCP 通信 |
| Maya Plugin | Maya Python (mel/cmds) | commandPort の起動・コマンド受信 |
| 3D Generation Client | REST API クライアント | 外部 3D 生成 AI との通信 |
| Asset Manager | Python | 生成されたメッシュファイルの管理・変換 |

## 3. 入力→3Dモデル 生成パイプライン

### 3.1 パイプライン全体像

```
入力（テキスト/写真/イラスト）
    │
    ▼
┌─────────────────────┐
│ 1. 入力解析          │  AI Client が入力を解析し、最適な生成戦略を決定
│    - 種別判定        │  （テキスト / 単一画像 / 複数画像）
│    - 対象物の分析    │  （ハードサーフェス / 有機物 / 環境）
│    - 複雑度の判定    │  （プリミティブ組み合わせ / AI生成が必要）
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 2. 3Dメッシュ生成    │  ← 入力種別と複雑度に応じて分岐
│    Route A: 外部AI   │  → 複雑な形状（キャラクター、有機物等）
│    Route B: Maya直接  │  → シンプルな形状（プリミティブ組み合わせ）
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 3. Maya インポート    │  FBX/OBJ 形式で Maya にインポート
│    - ファイルインポート│
│    - シーン配置       │
│    - スケール調整     │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 4. Maya 上でリファイン │  Maya コマンドで品質向上
│    - リトポロジー     │
│    - マテリアル調整   │
│    - UV 調整          │
│    - スムージング     │
└─────────────────────┘
```

### 3.2 生成ルート判定基準

| 条件 | Route A（外部 3D 生成 AI） | Route B（Maya 直接生成） |
|---|---|---|
| 入力が写真/イラスト | ○ Image-to-3D | △ リファレンス画像として利用 |
| 有機的形状（キャラクター、動物等） | ○ 必須 | × 不向き |
| ハードサーフェス（単純） | △ 使用可 | ○ polyCube/polyCylinder 等の組み合わせ |
| ハードサーフェス（複雑） | ○ 推奨 | △ 限定的 |
| 環境/背景 | ○ 個別アセット生成 | ○ レイアウト・配置 |
| テキストのみ（抽象的） | ○ Text-to-3D | ○ 単純形状なら |

## 4. 外部 3D 生成 AI 連携

### 4.1 対応サービス（推奨優先順）

| サービス | 強み | API | 出力形式 | 価格帯 |
|---|---|---|---|---|
| **Rodin Gen-2** (Hyper3D) | 最高テクスチャ品質、**クアッドメッシュ出力**（リトポ不要）、T/Aポーズ対応 | REST API | GLB, OBJ, FBX | ~$0.30-0.40/生成 |
| **Meshy** (v6) | 最も安定した品質、PBRテクスチャ、Maya プラグイン有 | REST API | FBX, OBJ, GLB, USDZ | クレジット制 |
| **Tripo3D** (v2.5) | 完全パイプライン（生成→リトポ→リグ）、既存MCP有 | REST API | FBX, OBJ, GLB, USDZ | ~$0.20-0.40/生成 |

### 4.2 オープンソース（セルフホスト）

| モデル | 特徴 | ライセンス | 備考 |
|---|---|---|---|
| **Hunyuan3D 2.5** (Tencent) | 商用品質に最も近い、PBR対応、リグ向けトポロジー | オープンソース | 12GB VRAM、8-20秒/A100 |
| **TripoSG** (VAST AI) | 最高幾何精度、1.5Bパラメータ | MIT | 10-15秒 |
| **TripoSR** (VAST AI + Stability) | 最速（0.5秒/A100）、ラピッドプロトタイプ向け | MIT | 品質はTripoSGに劣る |

### 4.3 3D 生成 AI 呼び出しフロー

```
1. MCP Server が生成リクエストを受信
2. 入力画像/テキストを API に送信（非同期タスク作成）
3. タスク ID を受け取り、ポーリング or Webhook で完了待ち
4. 完了後、メッシュファイル（FBX/OBJ）をダウンロード
5. Maya にインポートコマンドを送信
6. インポート結果を AI Client に返却
```

### 4.4 Image-to-3D vs Text-to-3D

| 観点 | Image-to-3D | Text-to-3D |
|---|---|---|
| 幾何精度 | **高い** — 視覚的リファレンスが形状を制約 | 低い — テキストは曖昧 |
| テクスチャ品質 | **高い** — 入力画像から導出可能 | 可変 — モデルの解釈依存 |
| 再現性 | **高い** — 予測可能 | 低い — 創造的バリエーション |
| 推奨用途 | **プロダクション** — コンセプトアート/写真を入力 | アイデア出し・プロトタイプ |

**結論**: 最もリアリティのあるモデルには **Image-to-3D を優先** し、複数アングル画像入力（Rodin, Tripo, Meshy 対応）でさらに精度を向上させる。

## 5. 通信方式

### 5.1 AI Client ↔ MCP Server
- **プロトコル**: MCP over stdio（標準入出力）
- **データ形式**: JSON-RPC 2.0

### 5.2 MCP Server ↔ Maya
- **プロトコル**: TCP ソケット（Maya commandPort）
- **デフォルトポート**: `7001`
- **通信方式**: Maya 側で `commandPort` を開き、MCP Server からソケット接続してコマンドを送信
- **コマンド形式**: Python コードを文字列として送信し、Maya 内部で `exec`/`eval` 実行

### 5.3 MCP Server ↔ 3D 生成 AI
- **プロトコル**: HTTPS REST API
- **認証**: Bearer Token（各サービスの API キー）
- **非同期パターン**: タスク作成 → ポーリング → ダウンロード

#### Maya 側の commandPort 起動コード（プラグインとして提供）
```python
import maya.cmds as cmds
cmds.commandPort(name=":7001", sourceType="python", echoOutput=True)
```

## 6. MCP ツール定義

### 6.1 3D モデル生成（Generation）— 新規

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `generate_from_text` | テキストから 3D モデルを生成 | `prompt`: str, `provider`: str, `options`: dict |
| `generate_from_image` | 画像から 3D モデルを生成 | `image_path`: str, `provider`: str, `options`: dict |
| `generate_from_images` | 複数画像から 3D モデルを生成 | `image_paths`: list[str], `provider`: str |
| `check_generation_status` | 生成タスクの進捗確認 | `task_id`: str |
| `import_generated_model` | 生成済みモデルを Maya にインポート | `file_path`: str, `options`: dict |

### 6.2 シーン管理（Scene）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `scene_info` | 現在のシーン情報を取得 | なし |
| `scene_new` | 新規シーンを作成 | `force`: bool |
| `scene_open` | シーンファイルを開く | `file_path`: str |
| `scene_save` | シーンを保存 | `file_path`: str (optional) |

### 6.3 オブジェクト操作（Object）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `create_object` | プリミティブ等のオブジェクト作成 | `type`: str, `name`: str, `options`: dict |
| `delete_object` | オブジェクトの削除 | `name`: str |
| `list_objects` | シーン内オブジェクトの一覧取得 | `type_filter`: str (optional) |
| `get_object_info` | オブジェクトの詳細情報取得 | `name`: str |

### 6.4 トランスフォーム（Transform）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `set_transform` | 位置・回転・スケールの設定 | `name`: str, `translate`: [x,y,z], `rotate`: [x,y,z], `scale`: [x,y,z] |
| `get_transform` | トランスフォーム値の取得 | `name`: str |

### 6.5 マテリアル（Material）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `create_material` | マテリアルの作成 | `name`: str, `type`: str (lambert/blinn/phong/arnold) |
| `assign_material` | オブジェクトにマテリアルを割り当て | `object_name`: str, `material_name`: str |
| `set_material_attr` | マテリアル属性の設定 | `material_name`: str, `attr`: str, `value`: any |

### 6.6 アニメーション（Animation）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `set_keyframe` | キーフレームの設定 | `name`: str, `attribute`: str, `time`: float, `value`: float |
| `set_playback_range` | 再生範囲の設定 | `start`: float, `end`: float |
| `play_animation` | アニメーション再生 | `forward`: bool |

### 6.7 レンダリング・ビューポート（Render / Viewport）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `render_frame` | 現在のフレームをレンダリング | `width`: int, `height`: int, `output_path`: str |
| `set_render_settings` | レンダー設定の変更 | `renderer`: str, `settings`: dict |
| `capture_viewport` | ビューポートのスクリーンキャプチャ | `output_path`: str, `width`: int, `height`: int |

### 6.8 汎用コマンド（General）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `execute_python` | 任意の Python コードを Maya で実行 | `code`: str |
| `execute_mel` | 任意の MEL コマンドを実行 | `command`: str |

## 7. MCP リソース定義

| リソース URI | 説明 |
|---|---|
| `maya://scene/info` | 現在のシーンのメタ情報 |
| `maya://scene/hierarchy` | シーンのノード階層構造 |
| `maya://object/{name}/attributes` | 指定オブジェクトの属性一覧 |
| `maya://viewport/capture` | ビューポートの現在の画像 |

## 8. プロジェクト構成

```
maya-mcp/
├── pyproject.toml                  # プロジェクト設定・依存関係
├── README.md                       # ドキュメント
├── src/
│   └── maya_mcp/
│       ├── __init__.py
│       ├── server.py               # MCP サーバー本体
│       ├── maya_client.py          # Maya との TCP 通信クライアント
│       ├── config.py               # 設定管理
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── generation.py       # 3D モデル生成ツール ★新規
│       │   ├── scene.py            # シーン管理ツール
│       │   ├── object.py           # オブジェクト操作ツール
│       │   ├── transform.py        # トランスフォームツール
│       │   ├── material.py         # マテリアルツール
│       │   ├── animation.py        # アニメーションツール
│       │   ├── render.py           # レンダリング・ビューポートツール
│       │   └── general.py          # 汎用コマンドツール
│       ├── providers/              # 3D 生成 AI プロバイダー ★新規
│       │   ├── __init__.py
│       │   ├── base.py             # プロバイダー共通インターフェース
│       │   ├── rodin.py            # Rodin (Hyper3D) クライアント
│       │   ├── meshy.py            # Meshy クライアント
│       │   └── tripo.py            # Tripo3D クライアント
│       └── resources/
│           ├── __init__.py
│           └── scene.py            # シーンリソース
├── maya_plugin/
│   └── maya_mcp_bridge.py          # Maya 側で読み込むプラグイン
└── tests/
    ├── __init__.py
    ├── test_server.py
    ├── test_maya_client.py
    └── test_providers.py           # プロバイダーテスト ★新規
```

## 9. 技術スタック

| 項目 | 選定 | 理由 |
|---|---|---|
| 言語 | Python 3.10+ | Maya Python API との親和性、MCP SDK の対応 |
| MCP SDK | `mcp` (Python SDK) | 公式 SDK、stdio トランスポート対応 |
| HTTP クライアント | `httpx` | 非同期対応、REST API 呼び出し用 |
| パッケージ管理 | `uv` / `pip` | pyproject.toml ベース |
| Maya 通信 | TCP ソケット (commandPort) | Maya 標準の外部通信機構、追加依存なし |
| テスト | pytest | Python 標準的テストフレームワーク |

## 10. Maya commandPort 通信仕様

### 10.1 接続フロー

```
1. Maya 起動 → commandPort をオープン（ポート 7001）
2. MCP Server 起動 → Maya への TCP 接続を確立
3. AI Client がツール呼び出し → MCP Server がコマンド生成
4. MCP Server → Maya へ Python コードを送信
5. Maya がコードを実行 → 結果を返却
6. MCP Server → AI Client へ結果を返却
```

### 10.2 デュアルコネクションパターン

Maya の commandPort では、複数行の Python コードを送信した際に戻り値を直接取得できない制約がある。
既存実装（PatrickPalmer/MayaMCP 等）で実績のある**デュアルコネクションパターン**を採用する。

```
接続1（コマンド送信用）: コードを実行し、結果をグローバル変数に格納
接続2（結果取得用）:     格納された結果を読み取り
```

```python
# 接続1: コマンド実行（結果をグローバル変数に格納）
code = '''
import maya.cmds as cmds
import json
_mcp_result = json.dumps(cmds.ls(type="mesh"))
'''
conn1.send(code.encode() + b'\n')

# 接続2: 結果取得
conn2.send(b'_mcp_result\n')
result = conn2.recv(4096).decode()
```

#### 名前空間の隔離

Maya のグローバル名前空間を汚染しないよう、MCP 関連の変数・関数はすべて `_mcp_` プレフィックスを付与する。

```python
# スコープ関数でラップして実行
def _mcp_exec():
    import maya.cmds as cmds
    return cmds.ls(type="mesh")
_mcp_result = _mcp_exec()
del _mcp_exec
```

### 10.3 コマンド送信形式

```python
# MCP Server から Maya への送信例（単純なコマンド）
socket.send(b'import maya.cmds as cmds; cmds.ls(type="mesh")\n')
```

- 末尾に `\n`（改行）を付与して送信完了を通知
- 戻り値は文字列として受信
- 複雑なコマンドはデュアルコネクションパターンを使用

### 10.4 エラーハンドリング

- 接続失敗時: リトライ（最大3回、指数バックオフ）
- コマンドエラー: Maya 側の例外をキャッチして構造化エラーとして返却
- タイムアウト: 30 秒（レンダリング等の長時間処理は個別設定可能）

## 11. セキュリティ考慮事項

| リスク | 対策 |
|---|---|
| 任意コード実行 | `execute_python` / `execute_mel` には注意喚起を付与。ローカル環境限定の使用を前提とする |
| ネットワーク露出 | commandPort は `localhost` のみでリッスン |
| ファイルアクセス | パス検証（トラバーサル防止）、ユーザー確認を推奨 |
| API キー管理 | 環境変数で管理、コードにハードコードしない |

## 12. 設定

### MCP Server 設定（環境変数 / 設定ファイル）

| 設定項目 | デフォルト値 | 説明 |
|---|---|---|
| `MAYA_HOST` | `localhost` | Maya のホスト |
| `MAYA_PORT` | `7001` | Maya commandPort のポート |
| `COMMAND_TIMEOUT` | `30` | コマンドタイムアウト（秒） |
| `GENERATION_TIMEOUT` | `300` | 3D 生成タイムアウト（秒） |
| `DEFAULT_PROVIDER` | `rodin` | デフォルトの 3D 生成プロバイダー |
| `RODIN_API_KEY` | — | Rodin (Hyper3D) API キー |
| `MESHY_API_KEY` | — | Meshy API キー |
| `TRIPO_API_KEY` | — | Tripo3D API キー |
| `ASSET_DIR` | `~/maya_mcp_assets` | 生成アセットの保存ディレクトリ |

### Claude Desktop 設定例（claude_desktop_config.json）

```json
{
  "mcpServers": {
    "maya": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/maya-mcp", "maya-mcp-server"],
      "env": {
        "RODIN_API_KEY": "your-rodin-api-key",
        "MESHY_API_KEY": "your-meshy-api-key",
        "TRIPO_API_KEY": "your-tripo-api-key"
      }
    }
  }
}
```

## 13. 開発フェーズ

### Phase 1: 基盤構築（MVP）
- MCP Server の骨格（stdio トランスポート）
- Maya commandPort 通信クライアント（デュアルコネクション）
- Maya プラグイン（commandPort 起動）
- 基本ツール: `execute_python`, `execute_mel`, `scene_info`, `list_objects`
- 3D 生成プロバイダーの共通インターフェース設計

### Phase 2: 3D 生成パイプライン
- Rodin プロバイダー実装（Image-to-3D / Text-to-3D）
- Meshy プロバイダー実装
- Tripo プロバイダー実装
- `generate_from_text`, `generate_from_image`, `generate_from_images` ツール
- 生成メッシュの Maya インポート機能
- 非同期タスク管理（ポーリング / 完了通知）

### Phase 3: Maya 操作ツール
- オブジェクト操作ツール群
- トランスフォームツール
- マテリアルツール
- ビューポートキャプチャ（`capture_viewport`）

### Phase 4: リファイン・品質向上
- アニメーションツール
- レンダリングツール
- インポート後の自動リファイン（リトポロジー、UV 調整）
- エラーハンドリングの強化
- テストの充実

## 14. 利用シナリオ例

### シナリオ 1: 写真からリアルな椅子を生成

```
ユーザー: 「この椅子の写真から 3D モデルを作って」（写真を添付）

AI の処理フロー:
1. 画像を解析 → 椅子（ハードサーフェス）と判定
2. generate_from_image(image_path="chair.jpg", provider="rodin") を呼び出し
3. Rodin API に画像を送信 → クアッドメッシュ FBX を取得
4. import_generated_model() で Maya にインポート
5. capture_viewport() でビューポート画像を取得し、ユーザーに確認
6. ユーザーのフィードバックに基づき Maya コマンドで調整
```

### シナリオ 2: テキストからファンタジーキャラクター生成

```
ユーザー: 「鎧を着た女性戦士のキャラクターを作って」

AI の処理フロー:
1. テキストを解析 → キャラクター（有機物+ハードサーフェス）と判定
2. generate_from_text(prompt="Female warrior in armor, T-pose", provider="meshy") を呼び出し
3. Meshy API で 3D モデル生成 → PBR テクスチャ付き FBX
4. import_generated_model() で Maya にインポート
5. set_transform() でスケール調整
6. capture_viewport() で確認 → ユーザーにフィードバック依頼
```

### シナリオ 3: イラストから環境シーン構築

```
ユーザー: 「このイラストの風景を 3D シーンにしたい」（イラストを添付）

AI の処理フロー:
1. イラストを解析 → 環境（複数オブジェクト）と判定
2. シーン内の要素を分解（建物、木、道路等）
3. 各要素を個別に generate_from_image() / create_object() で生成
4. set_transform() で配置・スケール調整
5. create_material() + assign_material() で質感設定
6. capture_viewport() で全体確認
```

## 15. 既存実装の参考プロジェクト

| プロジェクト | 特徴 |
|---|---|
| [PatrickPalmer/MayaMCP](https://github.com/PatrickPalmer/MayaMCP) | デュアルコネクション方式、Maya プラグイン不要、名前空間隔離 |
| [Jeffreytsai1004/maya-mcp](https://github.com/Jeffreytsai1004/maya-mcp) | 29 ツール、ポート 7022 使用、ホットリロード対応 |
| [AYDJI/Autodesk-Maya-MCP](https://github.com/AYDJI/Autodesk-Maya-MCP) | 30+ ツール、プロダクション向け |
| [lightfastai/lightfast-mcp](https://github.com/lightfastai/lightfast-mcp) | Blender/Maya/TouchDesigner 統合アーキテクチャ |

## 16. 今後の拡張候補

- **ノードエディタ操作**: シェーディングネットワーク等のノード操作
- **リグ操作**: キャラクターリグのコントロール（Tripo/Meshy の自動リグと連携）
- **USD 対応**: Universal Scene Description との連携
- **バッチ処理**: 複数アセットの一括生成・インポート
- **セルフホスト AI**: Hunyuan3D 2.5 / TripoSG をローカル GPU で実行するプロバイダー
- **AI フィードバックループ**: ビューポートキャプチャ → AI 評価 → 自動修正の反復
