"""疑似 Git のブランチ・マージ（バックエンド_コマンド機能仕様 § 5b。git-team 編
Mission23〜25 想定。2026-09-13 確定、実装中）。

`git_ops.py` から import される git のサブコマンド実装群。疑似 Git の原則
（commit=セーブ / push=クリア判定）は据え置きで、ブランチは「作業ディレクトリ
（リポジトリ、`git_state.repo.root`）配下だけ」を管理する（実 git と同じ。世界
全体ではない）。

注意（スナップショット/resume の既知の欠落）: `git_state.repo` は `git commit` の
世界スナップショット（セーブ）には含めず、resume 時にも復元しない。ブランチ・
マージ・PR の状態はセーブ/ロードの対象外というのが現状の割り切り（今回のスコープ
外。将来 Mission23〜25 のコンテンツ実装時に必要になれば別途対応する）。
"""

import copy

from app.evaluator import fs
from app.evaluator.commands import _classic_diff
from app.evaluator.errors import CommandError

MERGE_UNRESOLVED_ERROR = "Error: you have unmerged files; resolve them and commit first"


def _next_commit_id(repo: dict) -> str:
    """7桁 hex 風の連番 id を払い出す（`f"{n:07x}"`）。"""
    seq = repo.setdefault("commit_seq", 1)
    repo["commit_seq"] = seq + 1
    return f"{seq:07x}"


def _working_children(state: dict, repo: dict) -> dict:
    node = fs.get_node(state, repo["root"])
    if node is None or node.get("type") != "dir":
        raise CommandError("Error: path not found")
    return node.get("children", {})


def _require_repo(state: dict) -> dict:
    repo = state.get("git_state", {}).get("repo")
    if repo is None:
        raise CommandError("Error: not a git repository")
    return repo


# --- 解放時フック（progress.release_missions が呼ぶ。テストからも直接呼べる） ---
def init_repo(state: dict, root: str, branch: str, message: str) -> None:
    """`root` ディレクトリの現在の children から `git_state.repo` を新規作成する。

    `MissionDef.initial_repo` の解放フック本体。root は呼び出し時点で既に
    ワールドに存在するディレクトリでなければならない。
    """
    node = fs.get_node(state, root)
    if node is None or node.get("type") != "dir":
        raise ValueError(f"initial_repo root {root} not found")

    repo: dict = {
        "root": root,
        "current_branch": branch,
        "branches": {},
        "merging": None,
        "prs": [],
        "commit_seq": 1,
    }
    commit_id = _next_commit_id(repo)
    repo["branches"][branch] = {
        "tree": copy.deepcopy(node.get("children", {})),
        "base": None,
        "log": [{"id": commit_id, "message": message}],
    }
    state.setdefault("git_state", {})["repo"] = repo


def add_branch(state: dict, name: str, base_from: str, tree: dict, message: str) -> None:
    """`MissionDef.initial_branches` の解放フック本体。

    `base`（三方マージの共通祖先）は `base_from` ブランチの、この時点の tree の
    deepcopy。`tree` は呼び出し側が与えた children をそのまま使う（base_from の
    現在の tree の deepcopy ではない＝最初から差分入りの枝を作れる）。
    """
    repo = state["git_state"]["repo"]
    base_branch = repo["branches"][base_from]
    commit_id = _next_commit_id(repo)
    repo["branches"][name] = {
        "tree": copy.deepcopy(tree),
        "base": copy.deepcopy(base_branch["tree"]),
        "log": [{"id": commit_id, "message": message}],
    }


# --- `git branch` / `git checkout` / `git log` / `git diff` ---
def branch_list(state: dict) -> list[str]:
    repo = _require_repo(state)
    lines = []
    for name in sorted(repo["branches"]):
        marker = "* " if name == repo["current_branch"] else "  "
        lines.append(f"{marker}{name}")
    return lines


def checkout_new(state: dict, name: str) -> list[str]:
    repo = _require_repo(state)
    if name in repo["branches"]:
        raise CommandError(f"Error: a branch named '{name}' already exists")
    current = repo["branches"][repo["current_branch"]]
    repo["branches"][name] = {
        "tree": copy.deepcopy(current["tree"]),
        "base": copy.deepcopy(current["tree"]),
        "log": copy.deepcopy(current["log"]),
    }
    repo["current_branch"] = name
    return [f"Switched to a new branch '{name}'"]


def checkout_switch(state: dict, name: str) -> list[str]:
    repo = _require_repo(state)
    if repo.get("merging"):
        raise CommandError(MERGE_UNRESOLVED_ERROR)
    if name not in repo["branches"]:
        raise CommandError(f"Error: pathspec '{name}' did not match any branch")

    current_children = _working_children(state, repo)
    current_tree = repo["branches"][repo["current_branch"]]["tree"]
    if current_children != current_tree:
        raise CommandError("Error: commit your changes before switching branches")

    node = fs.get_node(state, repo["root"])
    node["children"] = copy.deepcopy(repo["branches"][name]["tree"])
    repo["current_branch"] = name
    return [f"Switched to branch '{name}'"]


def log(state: dict) -> list[str]:
    repo = _require_repo(state)
    branch = repo["branches"][repo["current_branch"]]
    return [f"{entry['id']} {entry['message']}" for entry in reversed(branch["log"])]


def _flatten_nodes(tree: dict, prefix: str = "") -> dict[str, dict]:
    """tree（children map）を「相対パス → file ノード」へ再帰的に平坦化する。"""
    out: dict[str, dict] = {}
    for name, node in tree.items():
        path = f"{prefix}{name}"
        if node.get("type") == "dir":
            out.update(_flatten_nodes(node.get("children", {}), f"{path}/"))
        elif node.get("type") == "file":
            out[path] = node
    return out


def _unflatten_nodes(flat: dict[str, dict]) -> dict:
    """「相対パス → file ノード」から children map（ネスト構造）を組み立てる。"""
    root: dict = {}
    for path, node in flat.items():
        parts = path.split("/")
        cur = root
        for part in parts[:-1]:
            cur = cur.setdefault(part, {"type": "dir", "children": {}})["children"]
        cur[parts[-1]] = node
    return root


def diff_branches(state: dict, a: str, b: str) -> list[str]:
    repo = _require_repo(state)
    if a not in repo["branches"] or b not in repo["branches"]:
        raise CommandError("Error: branch not found")

    a_flat = _flatten_nodes(repo["branches"][a]["tree"])
    b_flat = _flatten_nodes(repo["branches"][b]["tree"])

    out: list[str] = []
    for path in sorted(set(a_flat) | set(b_flat)):
        a_node = a_flat.get(path)
        b_node = b_flat.get(path)
        if a_node is None:
            out.append(f"Only in {b}: {path}")
            continue
        if b_node is None:
            out.append(f"Only in {a}: {path}")
            continue
        a_content = a_node.get("content", "")
        b_content = b_node.get("content", "")
        if a_content == b_content:
            continue
        out.append(f"diff {a} {b} -- {path}")
        out.extend(_classic_diff(a_content.split("\n"), b_content.split("\n")))
    return out


# --- `git merge` ---
def _conflict_content(ours: str, theirs: str, branch_name: str) -> str:
    """行単位/ファイル単位の競合マーカーを組み立てる（行数が同じなら行単位、
    違えばファイル全体を1つのマーカーで囲む。§ 5b）。
    """
    ours_lines = ours.split("\n")
    theirs_lines = theirs.split("\n")
    if len(ours_lines) != len(theirs_lines):
        return "\n".join(
            [
                "<<<<<<< HEAD",
                *ours_lines,
                "=======",
                *theirs_lines,
                f">>>>>>> {branch_name}",
            ]
        )

    out: list[str] = []
    for ours_line, theirs_line in zip(ours_lines, theirs_lines):
        if ours_line == theirs_line:
            out.append(ours_line)
        else:
            out.extend(
                ["<<<<<<< HEAD", ours_line, "=======", theirs_line, f">>>>>>> {branch_name}"]
            )
    return "\n".join(out)


def merge_branch(state: dict, name: str) -> list[str]:
    repo = _require_repo(state)
    current_name = repo["current_branch"]
    if repo.get("merging"):
        raise CommandError(MERGE_UNRESOLVED_ERROR)
    if name not in repo["branches"]:
        # 実 git の文言（`git merge nosuch` → "merge: nosuch - not something we can merge"）
        raise CommandError(f"merge: {name} - not something we can merge")
    if name == current_name:
        return ["Already up to date."]

    ours_branch = repo["branches"][current_name]
    theirs_branch = repo["branches"][name]
    ours_tree = ours_branch["tree"]
    theirs_tree = theirs_branch["tree"]
    base_tree = theirs_branch.get("base") or {}

    if ours_tree == base_tree:
        # 自分の tree が base のまま = Fast-forward。theirs の tree/log をそのまま採用する。
        node = fs.get_node(state, repo["root"])
        node["children"] = copy.deepcopy(theirs_tree)
        ours_branch["tree"] = copy.deepcopy(theirs_tree)
        ours_branch["log"] = copy.deepcopy(theirs_branch["log"])
        return ["Fast-forward"]

    ours_flat = _flatten_nodes(ours_tree)
    theirs_flat = _flatten_nodes(theirs_tree)
    base_flat = _flatten_nodes(base_tree)

    merged: dict[str, dict] = {}
    conflicts: list[str] = []
    for path in sorted(set(ours_flat) | set(theirs_flat) | set(base_flat)):
        ours_node = ours_flat.get(path)
        theirs_node = theirs_flat.get(path)
        base_node = base_flat.get(path)
        ours_content = ours_node.get("content") if ours_node else None
        theirs_content = theirs_node.get("content") if theirs_node else None
        base_content = base_node.get("content") if base_node else None

        if ours_content == theirs_content:
            # 両方同じ（変更なし、または偶然同じ内容に変更）→ 維持。
            if ours_node is not None:
                merged[path] = ours_node
            continue
        if ours_content == base_content:
            # 相手だけ変更 → 採用（相手が削除していれば merged からも落とす）。
            if theirs_node is not None:
                merged[path] = theirs_node
            continue
        if theirs_content == base_content:
            # 自分だけ変更 → 維持。
            if ours_node is not None:
                merged[path] = ours_node
            continue

        # 両方別々に変更 → 競合。
        conflicts.append(path)
        conflict_text = _conflict_content(ours_content or "", theirs_content or "", name)
        merged[path] = fs.new_file(content=conflict_text)

    node = fs.get_node(state, repo["root"])
    node["children"] = _unflatten_nodes(merged)

    if conflicts:
        repo["merging"] = {"from": name, "conflicts": conflicts}
        out = [f"CONFLICT (content): Merge conflict in {path}" for path in conflicts]
        out.append("Automatic merge failed; fix conflicts and then commit the result.")
        return out

    # 競合なしの三方マージは実 git と同じくその場でマージコミットを確定する。
    ours_branch["tree"] = copy.deepcopy(node["children"])
    ours_branch["log"].append(
        {"id": _next_commit_id(repo), "message": f"Merge branch '{name}'"}
    )
    return ["Merge made by the 'ort' strategy."]


# --- `git status` / `git commit` の拡張 ---
def status_prefix(state: dict) -> list[str]:
    """`git status` の先頭に足す行（repo があれば On branch、merging 中なら追加行）。"""
    repo = state.get("git_state", {}).get("repo")
    if repo is None:
        return []
    lines = [f"On branch {repo['current_branch']}"]
    if repo.get("merging"):
        lines.append("You have unmerged paths.")
    return lines


def finalize_commit(state: dict, message: str) -> None:
    """`git commit` の repo 拡張: 現在の枝の tree を作業ディレクトリの中身で更新し、
    log に積む。`merging` 中なら log メッセージを `Merge branch '<name>'` に差し替え、
    `merging` を消す（競合マーカーが残っていても実 git と同じく成功する。見抜くのは
    `case_file.sh`/レビューの判定側の仕事）。
    """
    repo = state.get("git_state", {}).get("repo")
    if repo is None:
        return

    branch = repo["branches"][repo["current_branch"]]
    branch["tree"] = copy.deepcopy(_working_children(state, repo))

    merging = repo.get("merging")
    if merging:
        log_message = f"Merge branch '{merging['from']}'"
        repo["merging"] = None
    else:
        log_message = message
    branch["log"].append({"id": _next_commit_id(repo), "message": log_message})
