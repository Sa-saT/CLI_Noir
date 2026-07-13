"""擬似シェル evaluator（純粋 Python）。

重要: FastAPI に依存させないこと（テスト・再利用のため独立させる）。
公開 API は `evaluate(command_line, state) -> (output_lines, new_state)`。
コマンド定義は docs/バックエンド_コマンド機能仕様.md に対応。
"""

from app.evaluator.engine import evaluate

__all__ = ["evaluate"]
