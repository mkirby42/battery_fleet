from battery_fleet.comparison import generate_comparison


if __name__ == "__main__":
    result = generate_comparison()
    print(f"comparison: {result.comparison_id}")
    print(f"greedy: {result.greedy_dir}")
    print(f"lookahead: {result.lookahead_dir}")
