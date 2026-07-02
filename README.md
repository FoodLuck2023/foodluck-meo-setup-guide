# FoodLuck MEO操作説明書サイト

このフォルダーは、Wordファイルを正本として自動生成した静的Webサイトです。

## 開き方

`index.html` をブラウザで開くと、トップページから各説明書へ移動できます。

## 更新方法

1. 元フォルダー内のWord説明書を修正します。
2. 下記のコマンドを、このプロジェクトフォルダーで実行します。

```powershell
C:\Users\n0ria\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\build_meo_manual_site.py
```

## 生成内容

- 生成元: `C:\Users\n0ria\Dropbox\007_ツール・DX\MEO\FoodLuckMEO操作説明書`
- 生成資料数: 26
- PDFは `assets/pdfs` にコピーされています。
- Word内画像は `assets/manual-images` に抽出されています。
- 検索データは `assets/search-index.js` に生成されています。
