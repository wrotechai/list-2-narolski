#!/bin/bash
# ============================================================================
# Breakthrough game runner — edit this file to invoke YOUR solution.
#
# The autograder calls this script with these positional arguments:
#   $1 = algorithm            ("minimax" or "alphabeta")
#   $2 = heuristic ID         (e.g., "1", "2", "3")
#   $3 = depth                (e.g., "3")
#
# The starting board is provided via STDIN (m lines of n space-separated
# tokens: B = Player 1, W = Player 2, _ = empty, o = last move origin).
#
# Board convention:
#   - Line 1 = top of the board
#   - B (Player 1) starts at the top two rows, moves DOWNWARD
#   - W (Player 2) starts at the bottom two rows, moves UPWARD
#   - B wins by reaching the last row; W wins by reaching the first row
#   - Player 1 (B) moves first
#
# Your solution MUST output:
#   stdout: The final board state (m lines of space-separated B/W/_/o),
#           followed by a summary line with the round count and winner.
#           Example summary: "Rounds: 15 Winner: B"
#   stderr: Number of visited decision tree nodes (line 1),
#           then computation time in seconds (line 2).
#
# Examples (uncomment and adapt ONE line):
#   python3 solution.py --algorithm "$1" --heuristic "$2" --depth "$3"
#   python3 solution.py "$1" "$2" "$3"
#   python3 main.py "$1" "$2" "$3"
#   java -jar solution.jar "$1" "$2" "$3"
# ============================================================================

python3 main.py --algorithm $1
python3 solution.py "$1" "$2" "$3"
