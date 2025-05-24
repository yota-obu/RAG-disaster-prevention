# 防災対策学習サイト (Disaster Preparedness Learning Site)

このプロジェクトは、ユーザーが防災について学ぶのを支援するために設計されたWebアプリケーションです。必要な非常用備蓄品を計算する「防災備蓄シミュレータ」と、提供されたドキュメントに基づいて防災と安全に関する質問に答えるAI搭載のチャットアシスタント「防災Chat」が含まれています。

## 特徴

### 1. 防災備蓄シミュレータ (Disaster Stockpile Simulator)
- **ユーザー入力:** 以下の年齢層で分類された家族の人数をユーザーが入力できます:
    - 成人 (Adult)
    - 子供(中学生以上) (Child - Junior high school and older)
    - 子供 (Child - Younger, elementary school and below)
    - 乳幼児 (Infant)
    - 高齢者 (Elderly)
- **システム出力:** 最低3日間分と推奨7日間分の必要な備蓄品（食料、衛生用品、必需品）を計算して表示します。結果は品目カテゴリ別にグループ化され、テーブル形式で表示されます。これらの計算データは、外部CSVファイル (`data/stockpile_items.csv`) から取得されます。

### 2. 防災Chat (Disaster Chat)
- **ユーザー入力:** ユーザーはチャットインターフェースで防災に関する質問をすることができます（例: 「地震の時はどうすればいいですか？」）。
- **システム出力:** Langchainを介してGoogleのGemini-Flashモデルを使用するRAG (Retrieval Augmented Generation) システムを搭載したAIアシスタントが質問に答えます。AIの知識は、ユーザー/管理者が `documents/` フォルダに提供したPDFドキュメントから抽出された情報に基づいています。回答を提供する際、チャットは回答に貢献したソースドキュメント（ファイル名とページ番号）もリスト表示します。

## 技術スタック

- **バックエンド:**
    - 言語/フレームワーク: Python (Flask)
    - 主要ライブラリ: Langchain (RAG用 v0.3.x), langchain_community, langchain_google_genai, pypdf, faiss-cpu, python-dotenv, pytest
- **フロントエンド:**
    - ライブラリ/フレームワーク: React (Create React App構成)
    - 主要ライブラリ: react-router-dom
- **AIモデル:** Google Gemini-Flash (`langchain_google_genai`経由でアクセス)
- **データストレージ:**
    - 備蓄品データ: CSVファイル (`disaster_prep_site/data/stockpile_items.csv`) で管理。
    - RAGベクターストア: FAISS (インデックスは `disaster_prep_site/backend/vectorstore_faiss/` に保存)。
- **コンテナ化:** Docker, Docker Compose
- **Webサーバー (フロントエンド):** Nginx (Dockerセットアップ内でReactビルドを提供し、APIリクエストをプロキシ)

## 前提条件

- **DockerとDocker Compose:** システムにインストールされている必要があります。インストール手順については、[Docker公式サイト](https://www.docker.com/get-started) を参照してください。
- **Google APIキー:** 「防災Chat」機能が動作するためには、Gemini API（具体的には "Generative Language API"）へのアクセス権を持つGoogle APIキーが必要です。[Google Cloud Console](https://console.cloud.google.com/) から取得できます。

## セットアップとアプリケーションの実行

1.  **リポジトリのクローン / ファイルの準備:**
    - このリポジトリをクローンした場合は、準備完了です。
    - そうでない場合は、すべてのプロジェクトファイルがルートディレクトリ（例: `disaster_prep_site/`）に存在することを確認してください。

2.  **環境変数の設定 (Google APIキー):**
    - `disaster_prep_site/backend/` ディレクトリに移動します。
    - `.env` という名前のファイルを作成します。存在すれば `backend/.env.example` をコピーするか、新しいファイルを作成します。
    - `.env` ファイルにGoogle APIキーを追加します。以下のようになるはずです:
      ```env
      GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY_HERE"
      ```
    - **重要:** `"YOUR_ACTUAL_GOOGLE_API_KEY_HERE"` を実際のGoogle APIキーに置き換えてください。有効なAPIキーがないと、「防災Chat」機能は正しく初期化されず、エラーメッセージが返されます。

3.  **備蓄データの準備 (任意カスタマイズ):**
    - 備蓄品目リストと推奨数量は `disaster_prep_site/data/stockpile_items.csv` で管理されています。
    - このCSVファイルを編集して、さまざまな地域のニーズや更新されたガイドラインに合わせて品目を追加、削除、または変更できます。バックエンドは起動時にこのデータを読み込みます。

4.  **RAGシステム用PDFドキュメントの追加:**
    - 「防災Chat」が知識ベースとして使用するPDFドキュメントを `disaster_prep_site/documents/` フォルダに配置します。これらは、公式の政府防災ガイド、地域の緊急時計画などです。
    - **初回実行時 / ドキュメント変更時の注意:**
        - アプリケーションを初めて起動したとき、または `disaster_prep_site/backend/vectorstore_faiss/` ディレクトリが空または削除されている場合、RAGシステムは `documents/` フォルダ内のすべてのPDFを処理してベクターストアを構築します。
        - この処理は、PDFドキュメントの数とサイズによって時間がかかることがあります。
        - 以降の起動は、`backend/vectorstore_faiss/` から事前に構築されたベクターストアを読み込むため、大幅に高速になります。
        - `documents/` フォルダ内のPDFドキュメントを追加、削除、または変更した場合は、`backend/vectorstore_faiss/` ディレクトリを削除して、次回実行時に更新されたコンテンツでベクターストアを再構築するようにしてください。

5.  **Docker Composeを使用したビルドと実行:**
    - ターミナルまたはコマンドプロンプトを開きます。
    - プロジェクトのルートディレクトリ（つまり `disaster_prep_site/` ディレクトリ）に移動します。
    - 次のコマンドを実行します:
      ```bash
      docker-compose up --build
      ```
    - このコマンドは次の処理を行います:
        - バックエンドおよびフロントエンドサービスのDockerイメージをビルドします（存在しない場合、またはDockerfileが変更された場合）。
        - 両方のサービスのコンテナを開始します。
    - ビルドプロセスとサービス起動が完了するまで待ちます。ターミナルに両方のサービスからのログが表示されます。

6.  **アプリケーションへのアクセス:**
    - **フロントエンドアプリケーション:** Webブラウザを開き、`http://localhost:3000` にアクセスします。
    - **バックエンドAPIエンドポイント (任意、Postmanやcurlなどのツールでの直接テスト用):**
        - 防災備蓄シミュレータ: `POST http://localhost:5001/api/stockpile_simulator`
          - ペイロード例: `{"family_members": {"adult": 2, "child": 1}}`
        - 防災Chat: `POST http://localhost:5001/api/chat`
          - ペイロード例: `{"question": "What to do in an earthquake?"}`

## 開発ノート

### テストの実行
バックエンドのユニットテストを実行するには、Dockerサービスが実行されていることを確認します（または、分離してテストする場合は少なくともバックエンドサービスが実行されていること）。次に、プロジェクトのルートディレクトリから新しいターミナルで次のコマンドを実行します:
```bash
docker-compose exec backend pytest -v
```
このコマンドは、`backend`サービスコンテナ内で`pytest`を実行します。`-v`フラグは詳細な出力を提供します。テストは`disaster_prep_site/backend/tests/`にあります。

### プロジェクト構成
主要ディレクトリの概要:
- `disaster_prep_site/`
    - `backend/`: Python Flaskバックエンドアプリケーションを格納します。
        - `app/`: `main.py` (APIエンドポイント) や `rag_logic.py` を含むコアアプリケーションロジック。
        - `tests/`: バックエンドのユニットテスト (例: `test_stockpile_simulator.py`, `test_rag_logic.py`)。
        - `vectorstore_faiss/`: RAGシステム用のFAISSベクターインデックスを格納します。これは、存在せず `documents/` が存在する場合に自動的に作成されます。
        - `.env`: `GOOGLE_API_KEY` を格納します（このファイルを作成する必要があります）。
        - `Dockerfile`: バックエンドDockerイメージをビルドするための指示。
        - `requirements.txt`: Pythonの依存関係。
    - `frontend/`: Reactフロントエンドアプリケーションを格納します。
        - `public/`: 静的アセットと`index.html`。
        - `src/`: Reactコンポーネント、ページ、CSS、およびアプリケーションロジック。
        - `nginx.conf`: フロントエンドDockerコンテナ内でReactアプリを提供し、APIリクエストをプロキシするために使用されるNginx設定。
        - `Dockerfile`: フロントエンドDockerイメージをビルドするための指示（マルチステージビルド）。
        - `package.json`: フロントエンドの依存関係とスクリプト。
    - `data/`: 外部データファイルを格納します。
        - `stockpile_items.csv`: 防災備蓄シミュレータ用の品目を定義するCSVファイル。
    - `documents/`: RAGシステムが知識ベースとして使用するPDFドキュメントを格納するディレクトリ。
    - `docker-compose.yml`: マルチコンテナアプリケーション（バックエンドとフロントエンド）を定義および実行するためのDocker Composeファイル。
    - `README.md`: このファイル、プロジェクトのドキュメントを提供します。

---
このREADMEは、「防災対策学習サイト」のセットアップ、実行、および理解のための包括的なガイドを提供します。
