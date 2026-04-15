#!/usr/bin/env python3
"""
Autograder for AI&KE Assignment #2 — Breakthrough (Minimax & Alpha-Beta)
========================================================================

Runs the student's solution via run_game.sh, parses stdout/stderr,
and validates against expected results. Exit code 0 = pass, 1 = fail.

Usage:
    python3 tests/autograder.py <TEST_ID>

Test IDs: T1_OUTPUT_FORMAT, T2_MINIMAX_GAME, T3_ALPHABETA_GAME,
          T4_PRUNING, T5_ENDGAME, T6_CAPTURE,
          T7_HEURISTIC_2, T8_HEURISTIC_3, T9_DEPTH_EFFECT
"""

import subprocess
import sys
import re
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 300  # seconds per test


# ── Board Definitions ────────────────────────────────────────

DEFAULT_8x8 = """\
B B B B B B B B
B B B B B B B B
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
W W W W W W W W
W W W W W W W W"""

SMALL_6x6 = """\
B B B B B B
B B B B B B
_ _ _ _ _ _
_ _ _ _ _ _
W W W W W W
W W W W W W"""

# B at row 7 (second-to-last), one move from winning.
# W is far away at row 2. B should win in round 1.
ENDGAME_B_WINS = """\
_ _ _ _ _ _ _ _
_ W _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ B _ _ _ _
_ _ _ _ _ _ _ _"""

# B at row 7, col 5. All three forward squares in row 8 are blocked by W.
# B can ONLY win by capturing diagonally. Tests the capture mechanic.
CAPTURE_FORCED = """\
_ _ _ _ _ _ _ _
_ _ W _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ _ _ _ _
_ _ _ _ B _ _ _
_ _ _ W W W _ _"""


VALID_CELLS = {'B', 'W', '_', 'o'}


# ── Output Parsing ───────────────────────────────────────────

def parse_stdout(stdout):
    """Parse stdout into board + summary.

    Returns dict with:
        board:   list of lists of tokens (B/W/_/o)
        summary: non-board text (round count, winner, etc.)
        raw:     original stdout
    """
    lines = stdout.strip().split('\n')
    board_lines = []
    summary_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        if len(tokens) >= 4 and all(t in VALID_CELLS for t in tokens):
            board_lines.append(tokens)
        else:
            summary_parts.append(stripped)

    return {
        'board': board_lines,
        'summary': '\n'.join(summary_parts),
        'raw': stdout,
    }


def parse_stderr(stderr):
    """Extract node count and computation time from stderr.

    Expected format:
        <node_count>      (integer, line 1)
        <time_seconds>    (float, line 2)
    """
    numbers = re.findall(r'[\d]+\.?\d*', stderr.strip())
    float_numbers = [float(n) for n in numbers]
    return {
        'raw': stderr,
        'numbers': float_numbers,
        'node_count': int(float_numbers[0]) if float_numbers else None,
        'time': float_numbers[1] if len(float_numbers) > 1 else None,
    }


# ── Solution Runner ──────────────────────────────────────────

def run_solution(algorithm, heuristic, depth, board_str):
    """Run the student's solution and return (stdout, stderr, returncode)."""
    script = os.path.join(REPO_ROOT, 'run_game.sh')
    if not os.path.isfile(script):
        print("FAIL: run_game.sh not found. Create it to tell the autograder how to run your solution.")
        sys.exit(1)

    try:
        result = subprocess.run(
            ['bash', script, str(algorithm), str(heuristic), str(depth)],
            input=board_str,
            capture_output=True, text=True, timeout=TIMEOUT,
            cwd=REPO_ROOT,
        )
    except subprocess.TimeoutExpired:
        print(f"FAIL: Solution timed out after {TIMEOUT}s")
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: Could not run solution: {e}")
        sys.exit(1)

    if result.returncode != 0 and not result.stdout.strip():
        print(f"FAIL: Solution exited with code {result.returncode}")
        if result.stderr.strip():
            print(f"stderr: {result.stderr[:500]}")
        sys.exit(1)

    return result.stdout, result.stderr, result.returncode


# ── Assertion Helpers ────────────────────────────────────────

class TestFailure(Exception):
    pass


def assert_valid_board(parsed, expected_rows=None, expected_cols=None):
    """Check that the output contains a valid board."""
    board = parsed['board']
    if not board:
        raise TestFailure(
            "No valid board found in stdout. Expected lines of space-separated B/W/_/o tokens.\n"
            f"Raw stdout:\n{parsed['raw'][:500]}"
        )
    if expected_rows and len(board) != expected_rows:
        raise TestFailure(
            f"Expected {expected_rows} board rows, got {len(board)}."
        )
    if expected_cols:
        for i, row in enumerate(board):
            if len(row) != expected_cols:
                raise TestFailure(
                    f"Row {i + 1} has {len(row)} columns, expected {expected_cols}."
                )


def assert_has_summary(parsed):
    """Check that a summary line exists after the board."""
    if not parsed['summary'].strip():
        raise TestFailure(
            "No summary line found after board output. "
            "Expected a line with round count and winner (e.g., 'Rounds: 15 Winner: B')."
        )


def assert_winner_declared(parsed):
    """Extract the declared winner from the summary. Returns 'B' or 'W'."""
    summary = parsed['summary']

    # Try "Winner: B", "won: W", "wygrywa B", etc.
    match = re.search(
        r'(?:winner|won|wygr\w*|wins?)[:\s]*([BW12])',
        summary, re.IGNORECASE,
    )
    if not match:
        # Try reverse: "B wins", "W won", "B wygrywa"
        match = re.search(r'([BW12])\s*(?:wins?|won|wygr)', summary, re.IGNORECASE)
    if not match:
        # Fallback: find any B or W in the summary
        match = re.search(r'\b([BW])\b', summary)
    if not match:
        raise TestFailure(
            f"Could not determine winner from summary: '{summary}'"
        )

    winner = match.group(1).upper()
    if winner == '1':
        winner = 'B'
    elif winner == '2':
        winner = 'W'
    return winner


def board_winner(board):
    """Determine the winner from the board state.

    B wins by reaching the last row. W wins by reaching the first row.
    If one side has no pieces, the other side wins.
    """
    if not board:
        return None

    last_row = board[-1]
    first_row = board[0]

    if 'B' in last_row:
        return 'B'
    if 'W' in first_row:
        return 'W'

    all_cells = [c for row in board for c in row]
    if 'B' not in all_cells:
        return 'W'
    if 'W' not in all_cells:
        return 'B'

    return None


def format_board(board):
    """Format board for display."""
    return '\n'.join(' '.join(row) for row in board)


def assert_winner_consistent(parsed):
    """Check that declared winner matches board state. Returns the winner."""
    declared = assert_winner_declared(parsed)
    bw = board_winner(parsed['board'])
    if bw and declared != bw:
        raise TestFailure(
            f"Declared winner is '{declared}', but board state suggests '{bw}'.\n"
            f"Board:\n{format_board(parsed['board'])}"
        )
    return declared


def assert_winner_is(parsed, expected):
    """Check that the winner is the expected player."""
    winner = assert_winner_declared(parsed)
    if winner != expected:
        raise TestFailure(
            f"Expected winner '{expected}', got '{winner}'."
        )


def assert_has_node_count(stderr_parsed):
    """Check that stderr contains a positive node count."""
    if stderr_parsed['node_count'] is None or stderr_parsed['node_count'] <= 0:
        raise TestFailure(
            "No valid node count found in stderr. Expected a positive integer on the first line.\n"
            f"Raw stderr:\n{stderr_parsed['raw'][:300]}"
        )


def assert_has_time(stderr_parsed):
    """Check that stderr contains a computation time."""
    if stderr_parsed['time'] is None:
        raise TestFailure(
            "No computation time found in stderr. "
            "Expected two numbers: node count (line 1) and time in seconds (line 2).\n"
            f"Raw stderr:\n{stderr_parsed['raw'][:300]}"
        )


def extract_round_count(parsed):
    """Try to extract the round count from the summary line."""
    summary = parsed['summary']
    match = re.search(r'(\d+)', summary)
    if match:
        return int(match.group(1))
    return None


# ── Test Definitions ─────────────────────────────────────────

def test_t1_output_format():
    """T1: Default 8x8, minimax, heuristic 1, depth 1.
    Verify: valid board output, summary line, stderr with node count and time."""
    stdout, stderr, _ = run_solution("minimax", 1, 1, DEFAULT_8x8)
    parsed = parse_stdout(stdout)
    stderr_p = parse_stderr(stderr)

    assert_valid_board(parsed, expected_rows=8, expected_cols=8)
    assert_has_summary(parsed)
    assert_winner_declared(parsed)
    assert_has_node_count(stderr_p)
    assert_has_time(stderr_p)
    print("PASS: Output format is valid (8x8 board, summary with winner, stderr with node count and time)")


def test_t2_minimax_game():
    """T2: Default 8x8, minimax, heuristic 1, depth 2.
    Verify: game completes with a valid winner, board state is consistent."""
    stdout, stderr, _ = run_solution("minimax", 1, 2, DEFAULT_8x8)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed, expected_rows=8, expected_cols=8)
    assert_has_summary(parsed)
    winner = assert_winner_consistent(parsed)
    print(f"PASS: Minimax game completed successfully. Winner: {winner}")


def test_t3_alphabeta_game():
    """T3: Default 8x8, alpha-beta, heuristic 1, depth 3.
    Verify: game completes with a valid winner."""
    stdout, stderr, _ = run_solution("alphabeta", 1, 3, DEFAULT_8x8)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed, expected_rows=8, expected_cols=8)
    assert_has_summary(parsed)
    winner = assert_winner_consistent(parsed)
    print(f"PASS: Alpha-beta game completed successfully. Winner: {winner}")


def test_t4_pruning():
    """T4: 6x6 board, depth 3, minimax vs alpha-beta.
    Verify: alpha-beta visits strictly fewer nodes than minimax."""
    stdout_mm, stderr_mm, _ = run_solution("minimax", 1, 3, SMALL_6x6)
    stdout_ab, stderr_ab, _ = run_solution("alphabeta", 1, 3, SMALL_6x6)

    parsed_mm = parse_stdout(stdout_mm)
    parsed_ab = parse_stdout(stdout_ab)
    stderr_mm_p = parse_stderr(stderr_mm)
    stderr_ab_p = parse_stderr(stderr_ab)

    assert_valid_board(parsed_mm, expected_rows=6, expected_cols=6)
    assert_valid_board(parsed_ab, expected_rows=6, expected_cols=6)
    assert_has_node_count(stderr_mm_p)
    assert_has_node_count(stderr_ab_p)

    mm_nodes = stderr_mm_p['node_count']
    ab_nodes = stderr_ab_p['node_count']

    if ab_nodes >= mm_nodes:
        raise TestFailure(
            f"Alpha-beta visited {ab_nodes} nodes, minimax visited {mm_nodes} nodes. "
            f"Expected alpha-beta to visit strictly fewer nodes (pruning should reduce the search space)."
        )

    reduction = 100 - 100 * ab_nodes / mm_nodes
    print(f"PASS: Alpha-beta pruning effective. "
          f"Minimax: {mm_nodes} nodes, Alpha-beta: {ab_nodes} nodes ({reduction:.0f}% reduction)")


def test_t5_endgame():
    """T5: Endgame board where B is one step from the last row. Minimax, depth 2.
    Verify: B wins (in round 1)."""
    stdout, stderr, _ = run_solution("minimax", 1, 2, ENDGAME_B_WINS)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed)
    assert_has_summary(parsed)
    assert_winner_is(parsed, 'B')

    rounds = extract_round_count(parsed)
    if rounds is not None and rounds > 1:
        raise TestFailure(
            f"Game took {rounds} rounds, but B should win in round 1 "
            f"(B is one step from the last row, with no blocking pieces)."
        )

    print("PASS: Endgame detected correctly — B wins immediately")


def test_t6_capture():
    """T6: Board where B's only legal moves are diagonal captures. Alpha-beta, depth 2.
    Verify: B wins (proving the capture mechanic works)."""
    stdout, stderr, _ = run_solution("alphabeta", 1, 2, CAPTURE_FORCED)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed)
    assert_has_summary(parsed)
    assert_winner_is(parsed, 'B')

    # Verify B actually reached the last row (winning via capture)
    board = parsed['board']
    if board and 'B' not in board[-1]:
        raise TestFailure(
            "B is declared winner but no B piece found on the last row. "
            "In this board, the only way to win is by capturing diagonally.\n"
            f"Board:\n{format_board(board)}"
        )

    print("PASS: Capture mechanic works — B captured diagonally to reach the last row")


def test_t7_heuristic_2():
    """T7: Default 8x8, alpha-beta, heuristic 2, depth 3.
    Verify: game completes with a valid winner (heuristic 2 is implemented)."""
    stdout, stderr, _ = run_solution("alphabeta", 2, 3, DEFAULT_8x8)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed, expected_rows=8, expected_cols=8)
    assert_has_summary(parsed)
    winner = assert_winner_consistent(parsed)
    print(f"PASS: Heuristic 2 produces a valid game. Winner: {winner}")


def test_t8_heuristic_3():
    """T8: Default 8x8, alpha-beta, heuristic 3, depth 3.
    Verify: game completes with a valid winner (heuristic 3 is implemented)."""
    stdout, stderr, _ = run_solution("alphabeta", 3, 3, DEFAULT_8x8)
    parsed = parse_stdout(stdout)

    assert_valid_board(parsed, expected_rows=8, expected_cols=8)
    assert_has_summary(parsed)
    winner = assert_winner_consistent(parsed)
    print(f"PASS: Heuristic 3 produces a valid game. Winner: {winner}")


def test_t9_depth_effect():
    """T9: 6x6 board, alpha-beta, depth 1 vs depth 3.
    Verify: depth 3 explores strictly more nodes than depth 1."""
    stdout1, stderr1, _ = run_solution("alphabeta", 1, 1, SMALL_6x6)
    stdout3, stderr3, _ = run_solution("alphabeta", 1, 3, SMALL_6x6)

    parsed1 = parse_stdout(stdout1)
    parsed3 = parse_stdout(stdout3)
    stderr1_p = parse_stderr(stderr1)
    stderr3_p = parse_stderr(stderr3)

    assert_valid_board(parsed1, expected_rows=6, expected_cols=6)
    assert_valid_board(parsed3, expected_rows=6, expected_cols=6)
    assert_has_node_count(stderr1_p)
    assert_has_node_count(stderr3_p)

    nodes_d1 = stderr1_p['node_count']
    nodes_d3 = stderr3_p['node_count']

    if nodes_d3 <= nodes_d1:
        raise TestFailure(
            f"Depth 3 visited {nodes_d3} nodes, depth 1 visited {nodes_d1} nodes. "
            f"Expected deeper search to visit strictly more nodes."
        )

    print(f"PASS: Depth parameter works correctly. "
          f"Depth 1: {nodes_d1} nodes, Depth 3: {nodes_d3} nodes ({nodes_d3 / nodes_d1:.1f}x increase)")


# ── Test Registry ────────────────────────────────────────────

TESTS = {
    'T1_OUTPUT_FORMAT':   test_t1_output_format,
    'T2_MINIMAX_GAME':    test_t2_minimax_game,
    'T3_ALPHABETA_GAME':  test_t3_alphabeta_game,
    'T4_PRUNING':         test_t4_pruning,
    'T5_ENDGAME':         test_t5_endgame,
    'T6_CAPTURE':         test_t6_capture,
    'T7_HEURISTIC_2':     test_t7_heuristic_2,
    'T8_HEURISTIC_3':     test_t8_heuristic_3,
    'T9_DEPTH_EFFECT':    test_t9_depth_effect,
}


# ── Main ─────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in TESTS:
        print(f"Usage: python3 tests/autograder.py <TEST_ID>")
        print(f"Available tests: {', '.join(TESTS.keys())}")
        sys.exit(1)

    test_id = sys.argv[1]
    test_fn = TESTS[test_id]

    try:
        test_fn()
        sys.exit(0)
    except TestFailure as e:
        print(f"FAIL [{test_id}]: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR [{test_id}]: Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
