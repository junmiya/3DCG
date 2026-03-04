# Maya MCP Server 開発仕様書

## 1. 概要

Autodesk Maya と AI アシスタント（Claude 等）を接続する MCP（Model Context Protocol）サーバーを開発する。
これにより、自然言語での指示を通じて Maya のシーン操作、モデリング、アニメーション等の 3DCG 作業を自動化・支援できるようにする。

## 2. アーキテクチャ

```
┌─────────────┐     stdio      ┌─────────────────┐    TCP Socket    ┌──────────────┐
│  AI Client   │ ◄────────────► │  MCP Server      │ ◄──────────────► │  Maya        │
│ (Claude等)   │    MCP Protocol│  (Python)        │   commandPort    │  (mayapy)    │
└─────────────┘                └─────────────────┘                   └──────────────┘
```

### コンポーネント構成

| コンポーネント | 技術 | 役割 |
|---|---|---|
| MCP Server | Python + `mcp` SDK | MCP プロトコルの処理、ツール定義 |
| Maya Bridge | Python socket | Maya commandPort との TCP 通信 |
| Maya Plugin | Maya Python (mel/cmds) | commandPort の起動・コマンド受信 |

## 3. 通信方式

### 3.1 AI Client ↔ MCP Server
- **プロトコル**: MCP over stdio（標準入出力）
- **データ形式**: JSON-RPC 2.0

### 3.2 MCP Server ↔ Maya
- **プロトコル**: TCP ソケット（Maya commandPort）
- **デフォルトポート**: `7001`
- **通信方式**: Maya 側で `commandPort` を開き、MCP Server からソケット接続してコマンドを送信
- **コマンド形式**: Python コードを文字列として送信し、Maya 内部で `exec`/`eval` 実行

#### Maya 側の commandPort 起動コード（プラグインとして提供）
```python
import maya.cmds as cmds
cmds.commandPort(name=":7001", sourceType="python", echoOutput=True)
```

## 4. MCP ツール定義

### 4.1 シーン管理（Scene）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `scene_info` | 現在のシーン情報を取得 | なし |
| `scene_new` | 新規シーンを作成 | `force`: bool |
| `scene_open` | シーンファイルを開く | `file_path`: str |
| `scene_save` | シーンを保存 | `file_path`: str (optional) |

### 4.2 オブジェクト操作（Object）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `create_object` | プリミティブ等のオブジェクト作成 | `type`: str, `name`: str, `options`: dict |
| `delete_object` | オブジェクトの削除 | `name`: str |
| `list_objects` | シーン内オブジェクトの一覧取得 | `type_filter`: str (optional) |
| `get_object_info` | オブジェクトの詳細情報取得 | `name`: str |

### 4.3 トランスフォーム（Transform）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `set_transform` | 位置・回転・スケールの設定 | `name`: str, `translate`: [x,y,z], `rotate`: [x,y,z], `scale`: [x,y,z] |
| `get_transform` | トランスフォーム値の取得 | `name`: str |

### 4.4 マテリアル（Material）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `create_material` | マテリアルの作成 | `name`: str, `type`: str (lambert/blinn/phong/arnold) |
| `assign_material` | オブジェクトにマテリアルを割り当て | `object_name`: str, `material_name`: str |
| `set_material_attr` | マテリアル属性の設定 | `material_name`: str, `attr`: str, `value`: any |

### 4.5 アニメーション（Animation）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `set_keyframe` | キーフレームの設定 | `name`: str, `attribute`: str, `time`: float, `value`: float |
| `set_playback_range` | 再生範囲の設定 | `start`: float, `end`: float |
| `play_animation` | アニメーション再生 | `forward`: bool |

### 4.6 レンダリング（Render）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `render_frame` | 現在のフレームをレンダリング | `width`: int, `height`: int, `output_path`: str |
| `set_render_settings` | レンダー設定の変更 | `renderer`: str, `settings`: dict |

### 4.7 汎用コマンド（General）

| ツール名 | 説明 | 主要パラメータ |
|---|---|---|
| `execute_python` | 任意の Python コードを Maya で実行 | `code`: str |
| `execute_mel` | 任意の MEL コマンドを実行 | `command`: str |

## 5. MCP リソース定義

| リソース URI | 説明 |
|---|---|
| `maya://scene/info` | 現在のシーンのメタ情報 |
| `maya://scene/hierarchy` | シーンのノード階層構造 |
| `maya://object/{name}/attributes` | 指定オブジェクトの属性一覧 |

## 6. プロジェクト構成

```
maya-mcp/
├── pyproject.toml              # プロジェクト設定・依存関係
├── README.md                   # ドキュメント
├── src/
│   └── maya_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP サーバー本体
│       ├── maya_client.py      # Maya との TCP 通信クライアント
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── scene.py        # シーン管理ツール
│       │   ├── object.py       # オブジェクト操作ツール
│       │   ├── transform.py    # トランスフォームツール
│       │   ├── material.py     # マテリアルツール
│       │   ├── animation.py    # アニメーションツール
│       │   ├── render.py       # レンダリングツール
│       │   └── general.py      # 汎用コマンドツール
│       └── resources/
│           ├── __init__.py
│           └── scene.py        # シーンリソース
├── maya_plugin/
│   └── maya_mcp_bridge.py      # Maya 側で読み込むプラグイン
└── tests/
    ├── __init__.py
    ├── test_server.py
    └── test_maya_client.py
```

## 7. 技術スタック

| 項目 | 選定 | 理由 |
|---|---|---|
| 言語 | Python 3.10+ | Maya Python API との親和性、MCP SDK の対応 |
| MCP SDK | `mcp` (Python SDK) | 公式 SDK、stdio トランスポート対応 |
| パッケージ管理 | `uv` / `pip` | pyproject.toml ベース |
| Maya 通信 | TCP ソケット (commandPort) | Maya 標準の外部通信機構、追加依存なし |
| テスト | pytest | Python 標準的テストフレームワーク |

## 8. Maya commandPort 通信仕様

### 8.1 接続フロー

```
1. Maya 起動 → commandPort をオープン（ポート 7001）
2. MCP Server 起動 → Maya への TCP 接続を確立
3. AI Client がツール呼び出し → MCP Server がコマンド生成
4. MCP Server → Maya へ Python コードを送信
5. Maya がコードを実行 → 結果を返却
6. MCP Server → AI Client へ結果を返却
```

### 8.2 コマンド送信形式

```python
# MCP Server から Maya への送信例
socket.send(b'import maya.cmds as cmds; cmds.ls(type="mesh")\n')
```

- 末尾に `\n`（改行）を付与して送信完了を通知
- 戻り値は文字列として受信

### 8.3 エラーハンドリング

- 接続失敗時: リトライ（最大3回、指数バックオフ）
- コマンドエラー: Maya 側の例外をキャッチして構造化エラーとして返却
- タイムアウト: 30 秒（レンダリング等の長時間処理は個別設定可能）

## 9. セキュリティ考慮事項

| リスク | 対策 |
|---|---|
| 任意コード実行 | `execute_python` / `execute_mel` には注意喚起を付与。ローカル環境限定の使用を前提とする |
| ネットワーク露出 | commandPort は `localhost` のみでリッスン |
| ファイルアクセス | パス検証（トラバーサル防止）、ユーザー確認を推奨 |

## 10. 設定

### MCP Server 設定（環境変数 / 設定ファイル）

| 設定項目 | デフォルト値 | 説明 |
|---|---|---|
| `MAYA_HOST` | `localhost` | Maya のホスト |
| `MAYA_PORT` | `7001` | Maya commandPort のポート |
| `COMMAND_TIMEOUT` | `30` | コマンドタイムアウト（秒） |

### Claude Desktop 設定例（claude_desktop_config.json）

```json
{
  "mcpServers": {
    "maya": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/maya-mcp", "maya-mcp-server"]
    }
  }
}
```

## 11. 開発フェーズ

### Phase 1: 基盤構築（MVP）
- MCP Server の骨格（stdio トランスポート）
- Maya commandPort 通信クライアント
- Maya プラグイン（commandPort 起動）
- 基本ツール: `execute_python`, `execute_mel`, `scene_info`, `list_objects`

### Phase 2: コア機能
- オブジェクト操作ツール群
- トランスフォームツール
- マテリアルツール
- リソース定義

### Phase 3: 拡張機能
- アニメーションツール
- レンダリングツール
- エラーハンドリングの強化
- テストの充実

## 12. 今後の拡張候補

- **Viewport キャプチャ**: Maya のビューポート画像を取得し AI に視覚的フィードバック
- **ノードエディタ操作**: シェーディングネットワーク等のノード操作
- **リグ操作**: キャラクターリグのコントロール
- **USD 対応**: Universal Scene Description との連携
- **バッチ処理**: 複数コマンドの一括実行
