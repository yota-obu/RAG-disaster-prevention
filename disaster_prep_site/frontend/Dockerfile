# ステージ1: Reactアプリケーションのビルド
FROM node:18-alpine AS builder

WORKDIR /app

# package.json と package-lock.json (利用可能な場合) をコピー
# package-lock.json が一貫して存在しない場合は、package.json のみをコピー
# ただし、ロックファイルをコミットして使用するのがベストプラクティス
COPY package.json package-lock.json* ./
# yarn を使用する場合は、package-lock.json* の代わりに yarn.lock をコピー

# 依存関係のインストール
RUN npm install
# yarn を使用する場合: RUN yarn install

# 残りのアプリケーションコードをコピー
COPY . .

# Reactアプリケーションをビルド
RUN npm run build
# yarn を使用する場合: RUN yarn build

# ステージ2: Nginxでアプリケーションを提供
FROM nginx:alpine

# カスタムNginx設定をコピー
# これにより、デフォルトのNginx設定が置き換えられる
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルダー段階からのビルド出力をNginxのウェブルートディレクトリにコピー
COPY --from=builder /app/build /usr/share/nginx/html

# ポート80を公開 (Nginxのデフォルトポート)
EXPOSE 80

# Nginxをフォアグラウンドで起動
CMD ["nginx", "-g", "daemon off;"]
