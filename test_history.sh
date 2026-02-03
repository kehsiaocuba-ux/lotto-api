#!/bin/bash
URL="https://lotto-api-weld.vercel.app/api/florida"

function test_game() {
    game=$1
    date=$2
    echo "------------------------------------------------"
    echo "📅 TESTING: $game ($date)"
    echo "------------------------------------------------"
    # Fetch data
    curl -s "$URL/$game?date=$date"
    echo "" # New line
    echo "" # Spacing
}

echo "==========================================="
echo "   STARTING HISTORIC DATE TEST (2023)"
echo "==========================================="

test_game "mega-millions" "2023-10-24"
test_game "florida-lotto" "2023-10-21"
test_game "cash4life" "2023-11-01"
test_game "jackpot-triple-play" "2023-10-20"
test_game "fantasy-5" "2023-09-15"
test_game "pick-5" "2023-08-10"
test_game "pick-4" "2023-07-04"
test_game "pick-3" "2023-12-25"
test_game "pick-2" "2023-01-01"

echo "==========================================="
echo "   TEST COMPLETE"
echo "==========================================="
