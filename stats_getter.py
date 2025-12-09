import pandas as pd
import sys

def compute_statistics(csv_file):
    """Compute statistics from CSV with prompt judgment data."""
    
    # Read CSV file
    df = pd.read_csv(csv_file)
    
    # Basic statistics
    total_prompts = len(df)
    
    # Count empty yR values (NaN, None, or empty string)
    yr_empty = df['yR'].isna().sum() + (df['yR'] == '').sum()
    
    # Count final_decision matches
    fd_equals_yg = (df['final_decision'] == df['yG']).sum()
    fd_equals_yr = (df['final_decision'] == df['yR']).sum()
    
    # Additional useful statistics
    yr_non_empty = total_prompts - yr_empty
    
    # Judge agreement statistics
    judge_cols = ['judge1', 'judge2', 'judge3']
    if all(col in df.columns for col in judge_cols):
        all_judges_agree = ((df['judge1'] == df['judge2']) & 
                           (df['judge2'] == df['judge3'])).sum()
        two_judges_agree = (((df['judge1'] == df['judge2']) | 
                            (df['judge2'] == df['judge3']) | 
                            (df['judge1'] == df['judge3'])) & 
                           ~((df['judge1'] == df['judge2']) & 
                             (df['judge2'] == df['judge3']))).sum()
        no_agreement = (~((df['judge1'] == df['judge2']) | 
                         (df['judge2'] == df['judge3']) | 
                         (df['judge1'] == df['judge3']))).sum()
    
    # Print statistics
    print("=" * 60)
    print("CSV STATISTICS REPORT")
    print("=" * 60)
    print(f"\nTotal prompts: {total_prompts}")
    print(f"\nyR field:")
    print(f"  - Empty: {yr_empty} ({yr_empty/total_prompts*100:.1f}%)")
    print(f"  - Non-empty: {yr_non_empty} ({yr_non_empty/total_prompts*100:.1f}%)")
    
    print(f"\nFinal decision matches:")
    print(f"  - final_decision == yG: {fd_equals_yg} ({fd_equals_yg/total_prompts*100:.1f}%)")
    print(f"  - final_decision == yR: {fd_equals_yr} ({fd_equals_yr/total_prompts*100:.1f}%)")
    
    if all(col in df.columns for col in judge_cols):
        print(f"\nJudge agreement:")
        print(f"  - All 3 judges agree: {all_judges_agree} ({all_judges_agree/total_prompts*100:.1f}%)")
        print(f"  - 2 judges agree: {two_judges_agree} ({two_judges_agree/total_prompts*100:.1f}%)")
        print(f"  - No agreement: {no_agreement} ({no_agreement/total_prompts*100:.1f}%)")
    
    # Value distribution for final_decision
    print(f"\nFinal decision distribution:")
    for val, count in df['final_decision'].value_counts().items():
        print(f"  - {val}: {count} ({count/total_prompts*100:.1f}%)")
    
    print("=" * 60)
    
    return {
        'total_prompts': total_prompts,
        'yr_empty': yr_empty,
        'yr_non_empty': yr_non_empty,
        'fd_equals_yg': fd_equals_yg,
        'fd_equals_yr': fd_equals_yr
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <csv_file>")
        print("Example: python script.py data.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    stats = compute_statistics(csv_file)












