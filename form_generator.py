import pandas as pd
import random
import json

# --- CONFIGURATION ---
INPUT_CSV       = 'evaluation_data.csv' 
OUTPUT_JS_FILE  = 'form_creator_script.js'

# --- FORM STRUCTURE CONFIGURATION ---
REQUIRED_QUESTIONS_COUNT = 3 # The number of questions mandatory for every user.

# The total number of questions to include in the form (Required + Optional)
MAX_TOTAL_QUESTIONS = 5
FORM_TITLE       = 'RLHF: Model Comparison'
FORM_DESCRIPTION = f"""You will start with {REQUIRED_QUESTIONS_COUNT} required comparisons. 
If you choose to continue, you can rate up to {MAX_TOTAL_QUESTIONS - REQUIRED_QUESTIONS_COUNT} additional comparisons.
Your feedback is crucial for model improvement!
"""

def main():
    try:
        df = pd.read_csv(INPUT_CSV)
    except FileNotFoundError:
        print(f"Error: Input file '{INPUT_CSV}' not found. Please create it.")
        return

    # Ensure columns exist and rename them for clarity
    df = df.rename(columns={'prompt': 'prompt', 'original': 'response_a', 'improved': 'response_b'})
    if not all(col in df.columns for col in ['prompt', 'response_a', 'response_b']):
        print("Error: CSV must contain 'prompt', 'original', and 'improved' columns.")
        return

    # Prepare questions with randomized response order
    questions = []  
    for index, row in df.iterrows():
        is_swapped = random.choice([True, False])
        
        questions.append({
            'prompt': row['prompt'],
            # Store the mapping (A=Original, B=Improved) and the displayed content (R1, R2)
            'R1_Model_ID': 'B' if is_swapped else 'A',
            'R2_Model_ID': 'A' if is_swapped else 'B',
            'response_R1': row['response_b'] if is_swapped else row['response_a'],
            'response_R2': row['response_a'] if is_swapped else row['response_b'],
        })

    # Apply limit and ensure randomization
    total_questions_to_use = min(MAX_TOTAL_QUESTIONS, len(questions))
    questions = random.sample(questions, total_questions_to_use)
    
    # Generate JS Data String
    js_content = "const QUESTION_DATA = [\n"
    for item in questions:
        # Use json.dumps to safely escape content for JavaScript
        json_string = json.dumps(item)
        js_content += f"  {json_string},\n"
    js_content += "];\n"
    
    # Template for the JavaScript functions (includes the UX and aggregation logic)
    js_template = f"""
const FORM_TITLE = "{FORM_TITLE.replace(r'"', r'\"').replace(r'\n', r'\\n')}";
const FORM_DESCRIPTION = "{FORM_DESCRIPTION.replace(r'"', r'\"').replace('\n', '\\n\"\n\t+ \"')}";
const REQUIRED_COUNT = {REQUIRED_QUESTIONS_COUNT}; // Used by the createLLMEvaluationForm function

// --- HELPER FUNCTION: Adds a single question block to the form ---
function addQuestionItems(form, question, qNum, totalCount) {{
    const R1_content = question.response_R1;
    const R2_content = question.response_R2;
    const R1_Model = question.R1_Model_ID; 
    const R2_Model = question.R2_Model_ID; 
    
    // 1. Display Prompt and Responses (Side-by-side UX)
    const displayTitle = `🤖 Comparison ${{qNum}} of ${{totalCount}}`;
    
    const displayHelpText = 
      `**Original Prompt:**\\n${{question.prompt}}\\n\\n` +
      `------------------------------------------------------------------------------------\\n` +
      `**👉 RESPONSE 1**\\n\\n${{R1_content}}\\n\\n` +
      `------------------------------------------------------------------------------------\\n` +
      `**👉 RESPONSE 2**\\n\\n${{R2_content}}\\n\\n` +
      `------------------------------------------------------------------------------------`;

    form.addSectionHeaderItem()
      .setTitle(displayTitle)
      .setHelpText(displayHelpText);
      
    // 2. Pairwise Comparison (5-Point Scale)
    const comparisonItem = form.addScaleItem();
    comparisonItem.setTitle('Which response is better overall?')
        .setBounds(1, 5)
        .setLabels('Response 1 Significantly Better', 'Response 2 Significantly Better')
        .setRequired(true);

    // 3. Store the Mapping (Hidden for analysis)
    // The model ID is hidden from the user but stored in the column header's comment for aggregation.
    comparisonItem.setHelpText(`__MAPPING__: R1=${{R1_Model}}, R2=${{R2_Model}}`);
}}

// ----------------------------------------------------------------------------------
// FORM CREATION FUNCTION (Handles conditional logic)
// ----------------------------------------------------------------------------------
function createLLMEvaluationForm() {{
  const form = FormApp.create(FORM_TITLE);
  form.setDescription(FORM_DESCRIPTION);
  form.setCollectEmail(false); // User request: No email collection

  const totalQuestions = QUESTION_DATA.length;
  const requiredQuestions = QUESTION_DATA.slice(0, REQUIRED_COUNT);
  const optionalQuestions = QUESTION_DATA.slice(REQUIRED_COUNT);

  let questionNumber = 1;
  
  // --- A. INTRO SECTION (Controls Flow) ---
  form.addPageBreakItem().setTitle("1. Instructions & Continuation");
  
  const continueItem = form.addMultipleChoiceItem();
  continueItem.setTitle('Do you want to continue after the mandatory questions?')
      .setChoices([
          continueItem.createChoice(
            `I will only complete the required ${REQUIRED_QUESTIONS_COUNT} questions.`, 
            FormApp.PageNavigationType.GO_TO_PAGE, 'Required Section' // Jumps to required, then exits
          ), 
          continueItem.createChoice(
            'Yes, I can rate all available questions.', 
            FormApp.PageNavigationType.GO_TO_PAGE, 'Optional Section' // Jumps to required, which then leads here
          )
      ])
      .setRequired(true);

  // --- B. REQUIRED SECTION (First 3 Questions) ---
  const requiredSection = form.addPageBreakItem()
      .setTitle(`2. Required Comparisons (${REQUIRED_QUESTIONS_COUNT} Questions)`);
  
  requiredQuestions.forEach(question => {{
      addQuestionItems(form, question, questionNumber++, totalQuestions);
  }});

  // Set the navigation of the last required question to point to the Optional Section
  // (We use the default continue setting, which is overwritten by the flow logic above)
  requiredSection.setGoToPage(form.getPages().find(p => p.getTitle() === "3. Optional Comparisons"));
  
  // --- C. OPTIONAL SECTION (Remaining Questions) ---
  const optionalSection = form.addPageBreakItem().setTitle("3. Optional Comparisons");
  
  optionalQuestions.forEach(question => {{
      addQuestionItems(form, question, questionNumber++, totalQuestions);
  }});
  
  Logger.log('Form URL: ' + form.getPublishedUrl());
}}

// ----------------------------------------------------------------------------------
// AGGREGATION FUNCTION (Unchanged from previous successful version)
// ----------------------------------------------------------------------------------
function aggregateResults() {{
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const formResponseSheet = ss.getSheets()[0];
  const data = formResponseSheet.getDataRange().getValues();
  
  if (data.length <= 1) {{
    Browser.msgBox('Error', 'No response data found. Please submit at least one form response.', Browser.Buttons.OK);
    return;
  }}

  const header = data[0];
  const qMap = {{}};
  header.forEach((title, index) => {{ qMap[title.trim()] = index; }});
  const scoreHeaders = header.filter(h => h.includes('Which response is better overall?'));

  const aggregation = {{}}; 

  for (let i = 1; i < data.length; i++) {{
    const row = data[i];
    
    scoreHeaders.forEach(scoreHeader => {{
      const colIndex = qMap[scoreHeader];
      const score = row[colIndex];
      
      // Skip if the user did not answer the question (due to conditional logic)
      if (score === "") return;
      
      const helpText = formResponseSheet.getRange(1, colIndex + 1).getComment();
      let R1_Model_ID, R2_Model_ID;
      
      if (helpText && helpText.includes('__MAPPING__')) {{
          const parts = helpText.split(': ')[1].split(', ');
          R1_Model_ID = parts[0].split('=')[1]; // e.g., 'A' (Original)
          R2_Model_ID = parts[1].split('=')[1]; // e.g., 'B' (Improved)
      }} else {{
         Logger.log('Error: Mapping not found for column: ' + scoreHeader);
         return; 
      }}
      
      const questionId = scoreHeader.replace('Which response is better overall?', '').trim();
      if (!aggregation[questionId]) {{
        aggregation[questionId] = {{ original_wins: 0, improved_wins: 0, ties: 0, original_score_sum: 0, improved_score_sum: 0, count: 0 }};
      }}

      // 5-point scale: 1 (R1 Sig Better) to 5 (R2 Sig Better)
      if (score === 1 || score === 2) {{
        const winner = R1_Model_ID === 'A' ? 'original' : 'improved';
        aggregation[questionId][`${{winner}}_wins`] = aggregation[questionId][`${{winner}}_wins`] + 1;
      }} else if (score === 4 || score === 5) {{
        const winner = R2_Model_ID === 'A' ? 'original' : 'improved';
        aggregation[questionId][`${{winner}}_wins`] = aggregation[questionId][`${{winner}}_wins`] + 1;
      }} else if (score === 3) {{
        aggregation[questionId].ties++;
      }}
      
      // Preference Score Mapping (0-4 points)
      const R1_Pref = 5 - score;
      const R2_Pref = score - 1; 
      
      if (R1_Model_ID === 'A') {{
          aggregation[questionId].original_score_sum = aggregation[questionId].original_score_sum + R1_Pref;
          aggregation[questionId].improved_score_sum = aggregation[questionId].improved_score_sum + R2_Pref;
      }} else {{
          aggregation[questionId].improved_score_sum = aggregation[questionId].improved_score_sum + R1_Pref;
          aggregation[questionId].original_score_sum = aggregation[questionId].original_score_sum + R2_Pref;
      }}
      
      aggregation[questionId].count++;
    }});
  }}

  // --- Output Results ---
  const outputSheet = ss.getSheetByName('Aggregated Results') || ss.insertSheet('Aggregated Results');
  outputSheet.clear();
  
  const outputHeaders = [
    'Question ID', 'Original Model Wins', 'Improved Model Wins', 'Ties', 
    'Original Win Rate (%)', 'Improved Win Rate (%)', 'Total Responses',
    'Avg. Original Preference Score (0-4)', 'Avg. Improved Preference Score (0-4)'
  ];
  outputSheet.appendRow(outputHeaders);

  for (const qId in aggregation) {{
    const data = aggregation[qId];
    const totalResponses = data.count;
    // Calculate win rate relative to total submissions (Wins + Ties + Losses)
    const winRatioBase = data.original_wins + data.improved_wins + data.ties;
    const originalWinRate = ((data.original_wins / winRatioBase) * 100).toFixed(1);
    const improvedWinRate = ((data.improved_wins / winRatioBase) * 100).toFixed(1);
    
    const avgOriginalScore = (data.original_score_sum / totalResponses).toFixed(2);
    const avgImprovedScore = (data.improved_score_sum / totalResponses).toFixed(2);
    
    outputSheet.appendRow([
      qId, data.original_wins, data.improved_wins, data.ties, 
      originalWinRate, improvedWinRate, totalResponses,
      avgOriginalScore, avgImprovedScore
    ]);
  }}
  
  Browser.msgBox('Success', 'Aggregation complete. Check the "Aggregated Results" sheet.', Browser.Buttons.OK);
}}

"""

    js_form_creator = js_content + js_template

    # Write the generated JS to a file
    with open(OUTPUT_JS_FILE, 'w', encoding='utf-8') as f:
        f.write(js_form_creator)

    print(f"\n✅ Successfully created {OUTPUT_JS_FILE}. Next steps:")
    print("1. Create a new Google Sheet/Apps Script project.")
    print("2. Paste the content of 'form_creator_script.js' into the script editor.")
    print(f"3. Run the 'createLLMEvaluationForm' function. It will create a form with {REQUIRED_QUESTIONS_COUNT} required questions and {total_questions_to_use - REQUIRED_QUESTIONS_COUNT} optional questions.")

if __name__ == "__main__":
    main()