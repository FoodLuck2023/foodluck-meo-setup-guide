# FoodLuck MEO操作説明書サイト Xserver公開手順

## 推奨公開URL

既存の自社サイトを壊さないため、次のどちらかで公開してください。

### 推奨1: サブドメイン

例:

`https://manual.example.com/`

Xserver側でサブドメインを作成し、その公開フォルダーにこのZIPの中身をアップロードします。

### 推奨2: サブディレクトリ

例:

`https://example.com/meo-manual/`

既存ドメインの `public_html` 配下に `meo-manual` フォルダーを作成し、その中にこのZIPの中身をアップロードします。

## アップロードするもの

ZIPを解凍し、解凍後フォルダーの中身をアップロードしてください。

アップロードする主な中身:

- `index.html`
- `manuals`
- `assets`
- `README.md`
- `WEB担当者向け_公開手順.md`
- `WEB担当者向け_パスワード設定手順.md`

`index.html` が公開URLの入口になります。

## Xserverでの配置例

### サブドメインで公開する場合

サブドメイン:

`manual.example.com`

アップロード先の例:

`/example.com/public_html/manual/`

この中に `index.html`、`assets`、`manuals` が入るようにしてください。

### サブディレクトリで公開する場合

公開URL:

`https://example.com/meo-manual/`

アップロード先の例:

`/example.com/public_html/meo-manual/`

この中に `index.html`、`assets`、`manuals` が入るようにしてください。

## パスワード制限

Xserverのサーバーパネルで「アクセス制限」を使うのが簡単です。

設定対象は、公開フォルダー全体にしてください。

例:

- サブドメイン公開: `manual` の公開フォルダー全体
- サブディレクトリ公開: `meo-manual` フォルダー全体

確認ポイント:

1. 公開URLを開くとID・パスワード入力画面が出る
2. 正しいID・パスワードで閲覧できる
3. PDFのURLを直接開いてもID・パスワードを求められる

## 公開後の確認

次の検索ワードで動作確認してください。

- クチコミ
- 投稿
- 順位
- GBP
- 写真

確認すること:

1. トップページが表示される
2. ロゴが見える
3. 説明書カードから詳細ページへ移動できる
4. 検索結果から該当箇所へ移動できる
5. 本文中の画像が表示される
6. PDFリンクが開く

## 注意

- `http://127.0.0.1:4173/` は制作確認用URLです。公開URLではありません。
- 既存サイトの `index.html` を上書きしないでください。
- 既存のWordPressサイト直下に置く場合は、既存の `.htaccess` との干渉に注意してください。
- 不安がある場合は、サブドメイン公開を推奨します。
