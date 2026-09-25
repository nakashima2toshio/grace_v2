#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""qa_qdrant - Q/A 生成 → Qdrant 登録の CLI パッケージ。

データ準備 3 工程の ③ にあたる。各 CLI はこのパッケージ配下のモジュールが持つ。

    make_qa.py                  Q/A 生成のみ
    make_qa_register_qdrant.py  Q/A 生成 → Qdrant 登録の統合
    register_to_qdrant.py       既存 CSV → Qdrant 登録

環境構築と実行手順は `qa_qdrant/docs/01_install.md`。

⚠️ **本ファイルには処理を書かないこと。**

2026-09-25 まで、ここには `make_qa.py` の古い写し（236 行・`main()` まで含む）が入っていた。
`backend/app/core/data_jobs.py` の Qdrant 登録ジョブが
`from qa_qdrant.register_to_qdrant import ...` を実行するたび、パッケージ import の
副作用として `config` と `qa_generation.pipeline` が読み込まれ、
登録ジョブが使わないモジュールを余計に引き込んでいた。
`main` / `PROJECT_ROOT` / `logger` を `qa_qdrant` から参照するコードは無かった（grep 実測）。

`__init__.py` に import や実行コードを置くと、パッケージ内の**どのモジュールを
読むときでも**その代償を払うことになる。`sys.path` へのプロジェクトルート挿入も
各モジュールが自前で行っているので、ここでは不要。
経緯は `qa_generation/docs/__init__.md` §4（姉妹リポジトリ grace_v2_local は 2026-09-21 に同じ整理を実施）。
"""
