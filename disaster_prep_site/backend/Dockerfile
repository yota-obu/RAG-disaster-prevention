# 公式のPythonランタイムを親イメージとして使用
FROM python:3.9-slim

# コンテナ内の作業ディレクトリを設定
WORKDIR /app

# requirementsファイルをコンテナの /app にコピー
COPY requirements.txt .

# requirements.txt で指定された必要なパッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# .env ファイルをコピー。ビルド時に存在するか、適切に処理されることを確認
COPY .env .

# バックエンドディレクトリから残りのアプリケーションコードを /app ディレクトリにコピー
COPY ./app ./app
COPY ./documents ./documents # RAGがランタイムに必要とする場合は documents フォルダもコピー
COPY ./vectorstore_faiss ./vectorstore_faiss # 事前にビルドされた場合は既存のベクターストアをコピー

# このコンテナの外部にポート5001を公開
EXPOSE 5001

# 環境変数を定義 ( .env を使用しない場合や上書きしたい場合)
# ENV GOOGLE_API_KEY your_api_key_here 

# コンテナ起動時に main.py を実行
# main.py 内のコマンドは app.run(host='0.0.0.0', port=5001)
# main.py が app/main.py にあり、app がパッケージの場合:
CMD ["python", "-m", "app.main"]
