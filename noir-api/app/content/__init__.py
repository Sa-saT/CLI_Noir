"""ゲームコンテンツ（Mission 定義など静的データ）。

Mission 定義は DB に持たず（スキーマは User / MissionState のみ）、ここに
静的カタログとして持つ。API はこのカタログを読む。
初期 filesystem / expected_script_patterns は evaluator・判定ロジック実装時に
MissionDef へ追加していく（現時点は id / title / description / allowed_commands）。
"""
