import csv
import json
from logging import config

def convert_csv_to_jsonl(input_csv, output_jsonl):
    """
    Convert CSV to JSONL format for Azure OpenAI GPT-4o fine-tuning.
    
    Args:
        input_csv: Path to input CSV file
        output_jsonl: Path to output JSONL file
        prompt_column: Name of the column containing prompts
        answer_column: Name of the column containing answers
        system_message: Optional system message to include in each example
    """
    with open(input_csv, 'r', encoding='utf-8') as csv_file, \
         open(output_jsonl, 'w', encoding='utf-8') as jsonl_file:
        
        # Cols: prompt,yG,c,yR,judge1,judge2,judge3,final_decision
        reader = csv.DictReader(csv_file)
        
        for _, row in enumerate(reader):
            prompt = row.get('prompt', '').strip()
            yG = row.get('yG', '').strip()
            c  = row.get('c', '').strip()
            yR = row.get('yR', '').strip()
            
            if not prompt or not yG or not c or not yR:
                print(f"WARNING: Skipping incomplete row { _ }")
                continue
            
            # Ensure all fields but prompt begin with a space
            if not yG.startswith(' '):
                yG = ' ' + yG
            if not c.startswith(' '):
                c = ' ' + c
            if not yR.startswith(' '):
                yR = ' ' + yR
            
            # Build messages array
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": yG},
                {"role": "assistant", "content": f"CRITIQUE: {c}"},
                {"role": "assistant", "content": f"REVISED: {yR}"}
            ]
            # Create training example
            training_example = {"messages": messages}
            
            # Write to JSONL file
            jsonl_file.write(json.dumps(training_example, ensure_ascii=False) + '\n')
    print(f"Conversion complete! Output saved to {output_jsonl}.")


if __name__ == "__main__":
    input_csv = 'judge_results_checkpoint_updated.csv'
    output_jsonl = 'sft.jsonl'
    prompt_column = 'prompt'
    answer_column = 'answer'
    system_message = None
    
    convert_csv_to_jsonl(
        input_csv,
        output_jsonl
    )