# FoodLuck MEO操作説明書サイト パスワード設定手順

## 推奨方針

閲覧前にパスワードを求める場合は、サーバー側のBasic認証で制限してください。

HTMLやJavaScriptだけでパスワードをかける方法もありますが、ファイルURLを直接知っている人には回避される可能性があります。説明書PDFや画像も含まれるため、公開前の入口制限はサーバー側で行うのが安全です。

## Apacheの場合

`basic-auth/apache/.htaccess.sample` を参考に、公開ディレクトリへ `.htaccess` を設置してください。

あわせて、サーバー上に `.htpasswd` を作成します。

例:

```bash
htpasswd -c /home/example/.htpasswd foodluck
```

その後、`.htaccess` 内の `AuthUserFile` を実際の `.htpasswd` の絶対パスに変更してください。

## Nginxの場合

`basic-auth/nginx/nginx-basic-auth.sample.conf` を参考に、対象ディレクトリまたは対象ドメインの `location` に `auth_basic` を設定してください。

`.htpasswd` はApacheと同じ形式を利用できます。

## ID・パスワードの決め方

推測されにくいものを設定してください。

例:

- ID: `foodluck`
- パスワード: 英大文字・英小文字・数字・記号を混ぜた12文字以上

パスワードをメールやチャットで共有する場合は、サイトURLとは別経路で送ることを推奨します。

## 公開後の確認

1. 公開URLを開く
2. 最初にID・パスワード入力画面が出る
3. 正しいID・パスワードでトップページが見られる
4. 間違ったID・パスワードでは見られない
5. PDFファイルのURLを直接開いてもID・パスワードを求められる

## 注意

Basic認証を設定する場所は、`index.html` だけではなく、`assets`、`manuals`、PDFを含む公開フォルダー全体にしてください。
