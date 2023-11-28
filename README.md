# tech0_Step3-1_demo_01

## 不動産データのスクレイピング・データ加工・グーグルスプレッドシートへの書き込みコード

・Step3_Scraping.ipynb  
不動産データのスクレイピング・データ加工・グーグルスプレッドシートの各コード機能確認用  
・Step3_Scraping_sample01.py  
上記の機能の関数化・統合化  

※ グーグルスプレッドシート認証手続き必要
※ grspread_key.json  取得必要  

参考サイト) https://www.youtube.com/watch?v=uBy7F4Wd9cE&t=948s

## ファイル構造
```
sample0/            # flask のsampleアプリフォルダ
├── templates/
│   └── index.html  # 'app' グループのテンプレートファイル
└── app.py          # sampleコード

sample1/            # flask の掲示板アプリフォルダ
├── bbs.py          # flask の掲示板アプリコード
└── bbs_log.json    # flask の掲示板アプリ書込・読込用jsonファイル

sample2/            # 発展編(省略): 掲示板アプリのテンプレートファイル活用
sample3/            # 発展編(省略)：ログデータのfirebase NosqlDB 活用
```
