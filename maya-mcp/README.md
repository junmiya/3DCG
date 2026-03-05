# Maya MCP Server

テキスト・写真・イラストから 3D モデルを生成し、Autodesk Maya に直接インポートする MCP (Model Context Protocol) サーバー。

## 特徴

- **テキスト → 3D**: 自然言語の説明から 3D モデルを生成
- **画像 → 3D**: 写真やイラストから高精度な 3D モデルを生成（最も高品質）
- **複数画像 → 3D**: 複数アングルの画像からさらに精度の高いモデルを生成
- **Maya 完全操作**: シーン管理、オブジェクト操作、マテリアル、アニメーション、レンダリング
- **3 つの AI プロバイダー**: Rodin (Hyper3D), Meshy, Tripo3D

## アーキテクチャ

```
AI Client (Claude等) ←MCP→ MCP Server ←TCP→ Maya (commandPort)
                                ↕
                        3D Generation AI
                      (Rodin/Meshy/Tripo)
```

## セットアップ

### 1. インストール

```bash
cd maya-mcp
pip install -e .
```

### 2. Maya 側の準備

Maya の Script Editor で以下を実行して commandPort を開く:

```python
import maya.cmds as cmds
cmds.commandPort(name=":7001", sourceType="python", echoOutput=True)
```

または、プラグインとしてロード:

```python
cmds.loadPlugin("/path/to/maya-mcp/maya_plugin/maya_mcp_bridge.py")
```

### 3. API キーの設定

環境変数で 3D 生成 AI の API キーを設定:

```bash
export RODIN_API_KEY="your-rodin-key"     # Rodin (Hyper3D) - 推奨
export MESHY_API_KEY="your-meshy-key"     # Meshy
export TRIPO_API_KEY="your-tripo-key"     # Tripo3D
```

### 4. Claude Desktop 設定

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "maya": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/maya-mcp", "maya-mcp-server"],
      "env": {
        "RODIN_API_KEY": "your-rodin-key",
        "MESHY_API_KEY": "your-meshy-key",
        "TRIPO_API_KEY": "your-tripo-key"
      }
    }
  }
}
```

## MCP ツール一覧

### 3D モデル生成
| ツール | 説明 |
|---|---|
| `generate_from_text` | テキストから 3D モデルを生成 |
| `generate_from_image` | 画像から 3D モデルを生成 |
| `generate_from_images` | 複数画像から 3D モデルを生成 |
| `check_generation_status` | 生成タスクの進捗確認 |
| `import_generated_model` | 生成モデルを Maya にインポート |

### シーン管理
| ツール | 説明 |
|---|---|
| `scene_info` / `scene_new` / `scene_open` / `scene_save` | シーンの情報取得・作成・開く・保存 |

### オブジェクト・トランスフォーム
| ツール | 説明 |
|---|---|
| `create_object` / `delete_object` / `list_objects` / `get_object_info` | オブジェクト CRUD |
| `set_transform` / `get_transform` | 位置・回転・スケール操作 |

### マテリアル
| ツール | 説明 |
|---|---|
| `create_material` / `assign_material` / `set_material_attr` | マテリアル作成・割当・属性設定 |

### アニメーション・レンダリング
| ツール | 説明 |
|---|---|
| `set_keyframe` / `set_playback_range` / `play_animation` | アニメーション操作 |
| `render_frame` / `set_render_settings` / `capture_viewport` | レンダリング・ビューポートキャプチャ |

### 汎用
| ツール | 説明 |
|---|---|
| `execute_python` / `execute_mel` | 任意の Python/MEL コマンド実行 |

## 使用例

### 写真から椅子を生成

```
ユーザー: 「この椅子の写真から 3D モデルを作って」

→ generate_from_image で Rodin に送信
→ FBX を受信して import_generated_model で Maya にインポート
→ capture_viewport で確認画像を取得
```

### テキストからキャラクター生成

```
ユーザー: 「鎧を着た女性戦士を作って」

→ generate_from_text で Meshy に送信
→ PBR テクスチャ付き FBX を受信
→ Maya にインポートしてスケール調整
```

## 設定項目

| 環境変数 | デフォルト | 説明 |
|---|---|---|
| `MAYA_HOST` | `localhost` | Maya ホスト |
| `MAYA_PORT` | `7001` | Maya commandPort ポート |
| `COMMAND_TIMEOUT` | `30` | コマンドタイムアウト (秒) |
| `DEFAULT_PROVIDER` | `rodin` | デフォルト 3D 生成プロバイダー |
| `ASSET_DIR` | `~/maya_mcp_assets` | 生成アセット保存先 |

## 開発

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## ライセンス

MIT
