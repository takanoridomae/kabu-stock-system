# 株式検索システム

株価に関連する指標やデータを効率的に検索し、登録・管理するWebアプリケーションです。

## 🎯 概要

このシステムは、PBR、PER、自己資本比率などの財務指標と株価の統計情報を一元管理し、効率的な株式データ検索・分析を提供します。

### 主な機能

- 📊 **高度な検索機能**: 企業名、株式コード、業種による複数条件検索
- 💾 **データ管理**: 検索結果の登録・更新機能
- 📈 **財務指標管理**: PBR、PER、自己資本比率、ROE、ROAの管理
- 📉 **価格統計**: 月間・年間・過去最高値の自動計算
- 🔄 **データエクスポート/インポート**: JSON形式でのデータ移行
- 🎨 **シンプルUI**: レスポンシブデザインで使いやすいインターフェース

## 🛠 技術スタック

- **フロントエンド**: HTML5, CSS3, JavaScript, Bootstrap 5
- **バックエンド**: Python 3.8+, Flask
- **データベース**: SQLite3
- **デプロイ**: Render対応

## 📁 プロジェクト構造

```
kabu/
├── app.py                      # Flaskエントリポイント
├── requirements.txt            # Python依存関係
├── README.md                  # プロジェクト概要
├── pronput.md                 # システム仕様書
├── frontend/                  # フロントエンド
│   ├── static/               # 静的ファイル
│   │   ├── css/
│   │   │   └── style.css     # カスタムスタイル
│   │   └── js/
│   │       └── common.js     # 共通JavaScript
│   └── templates/            # HTMLテンプレート
│       ├── base.html         # ベーステンプレート
│       ├── index.html        # ホームページ
│       └── search.html       # 検索ページ
├── backend/                   # バックエンド
│   ├── models/               # データベースモデル
│   │   ├── __init__.py
│   │   └── database.py       # DB管理クラス
│   └── routes/               # APIルーティング
│       ├── __init__.py
│       └── api.py           # APIエンドポイント
├── database/                 # データベース関連
│   ├── schema.sql           # 初期スキーマ
│   ├── migrations/          # マイグレーション
│   └── backup/              # バックアップ
├── jsonfile/                # エクスポートファイル
├── docs/                    # ドキュメント
└── grah/                    # グラフ図のスクリーンショット
```

## 🚀 セットアップ・実行方法

### 1. 必要な環境

- Python 3.8以上
- pip (Pythonパッケージマネージャー)

### 2. インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd kabu

# 仮想環境を作成（推奨）
python -m venv venv

# 仮想環境を有効化
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 実行

```bash
# 開発サーバーを起動
python app.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

### 4. 初期設定

初回起動時に自動的にデータベースが初期化され、サンプルデータが投入されます。

## 📊 データベース設計

### 主要テーブル

1. **companies** - 企業情報
   - 企業コード、企業名、業種、市場

2. **stock_prices** - 株価履歴
   - 株価、取得日、出来高

3. **financial_metrics** - 財務指標
   - PBR、PER、自己資本比率、ROE、ROA

4. **price_statistics** - 価格統計
   - 月間・年間・過去最高値/最低値

5. **technical_indicators** - テクニカル指標
   - RSI、MACD、移動平均、ボリンジャーバンド

### データベースの特徴

- **正規化設計**: データの整合性と効率性を重視
- **拡張性**: 新しい指標やテーブルの追加が容易
- **インデックス**: 検索性能の最適化
- **トリガー**: 自動的なタイムスタンプ更新

## 🔧 API仕様

### エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|---------------|-----|
| GET | `/api/companies` | 企業一覧取得 |
| POST | `/api/companies/search` | 企業検索 |
| GET | `/api/companies/{id}` | 企業詳細取得 |
| POST | `/api/companies/register` | 企業データ登録 |
| GET | `/api/export` | データエクスポート |
| POST | `/api/import` | データインポート |

### リクエスト例

```javascript
// 企業検索
POST /api/companies/search
{
  "symbol": "7203",
  "company_name": "トヨタ",
  "sector": "輸送用機器"
}

// 企業登録
POST /api/companies/register
{
  "symbol": "7203",
  "name": "トヨタ自動車",
  "sector": "輸送用機器",
  "market": "東証プライム",
  "price": 2500.0,
  "pbr": 1.2,
  "per": 8.5,
  "equity_ratio": 0.45
}
```

## 🌐 デプロイ

### Renderへのデプロイ

1. **Renderアカウント作成**: [render.com](https://render.com)でアカウントを作成

2. **新しいWebサービス作成**:
   - リポジトリを接続
   - ビルドコマンド: `pip install -r requirements.txt`
   - 起動コマンド: `gunicorn app:app`

3. **環境変数設定**:
   ```
   FLASK_ENV=production
   SECRET_KEY=your-secret-key-here
   ```

### 本番環境の設定

```python
# app.py の本番環境設定例
import os

if os.getenv('FLASK_ENV') == 'production':
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['DEBUG'] = False
```

## 📝 使用方法

### 1. 企業検索

1. 「検索」ページにアクセス
2. 企業コード、企業名、業種のいずれかを入力
3. 「検索」ボタンをクリック
4. 結果一覧から詳細を確認

### 2. データ登録

1. 検索結果から「+」ボタンをクリック
2. 必要な情報を入力
3. 「登録」ボタンでデータベースに保存

### 3. データエクスポート

1. ヘッダーの「エクスポート」をクリック
2. JSON形式でダウンロード開始

### 4. データインポート

1. ホームページの「データインポート」をクリック
2. エクスポートしたJSONファイルを選択
3. 「インポート」でデータを復元

## 🔒 セキュリティ

- SQLインジェクション対策（パラメータ化クエリ）
- XSS対策（適切なエスケープ処理）
- CSRF対策（Flaskの組み込み保護）
- 本番環境でのデバッグモード無効化

## 🚧 今後の拡張予定

- [ ] 外部API連携（Yahoo Finance、Alpha Vantage等）
- [ ] グラフ表示機能（Chart.js）
- [ ] ユーザー認証システム
- [ ] リアルタイム株価更新
- [ ] モバイルアプリ対応
- [ ] 機械学習による予測機能

## 🤝 貢献

プロジェクトへの貢献を歓迎します：

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 📞 サポート

質問や問題がある場合は、GitHubのIssuesページで報告してください。

---

**開発者**: 株式検索システム開発チーム  
**最終更新**: 2024年
