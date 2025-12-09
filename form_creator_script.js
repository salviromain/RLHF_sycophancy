function loadQuestionDataFromSheet() 
{
	// Using getActiveSpreadsheet() works when script is container-bound to a spreadsheet
	// The "Questions" sheet should have columns: prompt, original, improved
	const ss = SpreadsheetApp.getActiveSpreadsheet();
	let dataSheet = ss.getSheetByName('Questions');
	
	if (!dataSheet) 
	{
		// If the sheet doesn't exist, throw an error
		throw new Error('Could not find "Questions" sheet. Please create it with columns: prompt, original, improved.');
	}
	
	const data = dataSheet.getDataRange().getValues();
	const questionData = [];
	
	// Skip header row (index 0)
	for (let i = 1; i < data.length; i++) 
	{
		const [prompt, original, improved] = data[i];
		
		// Skip empty rows
		if (!prompt || !original || !improved) 
			continue;
		
		questionData.push({
			prompt:   prompt.toString(),
			original: original.toString(),
			improved: improved.toString()
		});
	}
	
	return questionData;
} // loadQuestionDataFromSheet


// Hardcoded fallback question data (used for testing or if sheet is not used)
const QUESTION_DATA = [
	{
		"prompt": "Write a haiku about coding",
		"original": "Code flows like water\nBugs hide in dark corners deep\nCoffee fuels the night",
		"improved": "Fingers dance on keys\nAlgorithms come alive\nCreation takes form"
	},
	{
		"prompt": "Explain quantum computing to a 10-year-old",
		"original": "Quantum computing uses quantum mechanics principles to process information differently than classical computers.",
		"improved": "Imagine a coin spinning in the air - it's both heads and tails at the same time until it lands! Quantum computers work like that spinning coin, trying many answers at once before picking the best one."
	},
	{
		"prompt": "What's the best way to learn a new language?",
		"original": "Practice daily, use language learning apps, watch movies in that language, and speak with native speakers.",
		"improved": "Start with 15 minutes daily of focused practice. Use apps like Duolingo for basics, then watch shows with subtitles in your target language. Most importantly, find a language partner to practice speaking - even mistakes help you learn!"
	},
	{
		"prompt": "How do I make perfect scrambled eggs?",
		"original": "Beat eggs, add butter to pan, cook on medium heat while stirring until done.",
		"improved": "Whisk 2-3 eggs with a splash of milk and a pinch of salt. Melt butter in a non-stick pan over medium-low heat. Pour in eggs and let them sit for 20 seconds, then gently push them with a spatula to form soft curds. Remove from heat while still slightly wet - they'll finish cooking from residual heat. The key is low heat and patience!"
	},
	{
		"prompt": "Why is the sky blue?",
		"original": "The sky is blue because of Rayleigh scattering, where shorter wavelengths of light (blue) scatter more than longer wavelengths.",
		"improved": "When sunlight enters Earth's atmosphere, it collides with air molecules. Blue light has shorter, choppier waves that bounce off these molecules more than other colors, scattering in all directions. That's why we see blue everywhere when we look up!"
	},
	{
		"prompt": "Give me tips for a job interview",
		"original": "Research the company, dress professionally, arrive early, prepare answers to common questions, and ask good questions.",
		"improved": "Prepare like a pro: (1) Research the company's recent news and values, (2) Practice the STAR method for behavioral questions, (3) Dress one level above the company dress code, (4) Arrive 10-15 minutes early, (5) Prepare 3-4 thoughtful questions about the role, and (6) Send a thank-you email within 24 hours. Remember: they want you to succeed!"
	},
	{
		"prompt": "What causes hiccups?",
		"original": "Hiccups are caused by involuntary contractions of the diaphragm muscle.",
		"improved": "Hiccups happen when your diaphragm (the muscle below your lungs) suddenly contracts involuntarily. This pulls air into your lungs quickly, and your vocal cords snap shut, making that 'hic' sound! Common triggers include eating too fast, drinking carbonated beverages, or sudden temperature changes."
	},
	{
		"prompt": "How can I be more productive?",
		"original": "Use time management techniques, eliminate distractions, take breaks, and prioritize important tasks.",
		"improved": "Try the Pomodoro Technique: work for 25 minutes, then take a 5-minute break. Start each day by identifying your top 3 priorities. Turn off notifications during focus time. And here's the secret: productivity isn't about doing more—it's about doing what matters most."
	}
];

const REQUIRED_COUNT = 3;
const OPTIONAL_COUNT = 2;
const TOTAL_QUESTIONS = REQUIRED_COUNT + OPTIONAL_COUNT;

// Serve the HTML form
function doGet() 
{
	return HtmlService.createHtmlOutputFromFile('FormPage')
		.setTitle('RLHF: Model Comparison')
		.setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
} // doGet


// Get randomized questions for the form
function getRandomQuestions() 
{
	// Load data from sheet instead of hardcoded constant
	let questionData = loadQuestionDataFromSheet() || QUESTION_DATA;
	
	if (questionData.length < TOTAL_QUESTIONS) 
	{
		throw new Error('Not enough questions available. Please add more to the "Questions" sheet.');
	}
	
	// Shuffle and select questions
	const shuffled = questionData.sort(() => 0.5 - Math.random());
	const selected = shuffled.slice(0, TOTAL_QUESTIONS);
	
	// Randomize which response is shown first (blind the comparison)
	const blindedQuestions = selected.map((q, index) => {
		const showOriginalFirst = Math.random() > 0.5;
		return {
			questionIndex: index,
			prompt: q.prompt,
			response_1: showOriginalFirst ? q.original : q.improved,
			response_2: showOriginalFirst ? q.improved : q.original,
			response_1_type: showOriginalFirst ? 'original' : 'improved',
			response_2_type: showOriginalFirst ? 'improved' : 'original'
		};
	});
	
	return {
		questions: blindedQuestions,
		requiredCount: REQUIRED_COUNT,
		totalCount: TOTAL_QUESTIONS
	};
} // getRandomQuestions

// Save user responses to the "Responses" sheet
function saveResponse(responses) 
{
	try 
	{
		Logger.log('Saving ' + responses.length + ' responses...');
		
		// Using getActiveSpreadsheet() works when script is container-bound to a spreadsheet
		const ss = SpreadsheetApp.getActiveSpreadsheet();
		if (!ss) 
		{
			throw new Error('Could not access spreadsheet. Make sure this script is container-bound to a spreadsheet' + 
				'(Extensions > Apps Script from within a Google Sheet)');
		}
		
		Logger.log('Spreadsheet found: ' + ss.getName());
		let sheet = ss.getSheetByName('Responses');
		
		// Create sheet if it doesn't exist
		if (!sheet) 
		{
		sheet = ss.insertSheet('Responses');
		const headers = [
			'Timestamp', 
			'Session ID', 
			'Question Index', 
			// 'Prompt', 
			// 'Response 1 (shown first)',
			// 'Response 2 (shown second)',
			'Response 1 Type',
			'Response 2 Type',
			'User Rating (1-5)', 
			'Winner',
			'Completed All'
		];
		sheet.appendRow(headers);
		
		// Format header row
		const headerRange = sheet.getRange(1, 1, 1, headers.length);
			headerRange.setFontWeight('bold');
			headerRange.setBackground('#1a73e8');
			headerRange.setFontColor('#ffffff');
		}
		
		const timestamp = new Date();
		const sessionId = Utilities.getUuid();
		
		// Save each response
		responses.forEach(response => {
			// Determine winner based on rating
			let winner = 'tie';
			if (response.rating === 1 || response.rating === 2) 
			{
				winner = response.response_1_type; // Response 1 is better
			} 
			else if (response.rating === 4 || response.rating === 5) 
			{
				winner = response.response_2_type; // Response 2 is better
			}
			
			sheet.appendRow([
				timestamp,
				sessionId,
				response.questionIndex,
				// response.prompt,
				// response.response_1,
				// response.response_2,
				response.response_1_type,
				response.response_2_type,
				response.rating,
				winner,
				response.completedAll
			]);
		});
		
		Logger.log('Successfully saved ' + responses.length + ' responses');
		return { success: true, message: 'Responses saved successfully!' };
		
	} 
	catch (error) 
	{
		Logger.log('Error saving responses: ' + error.toString());
		return { success: false, message: 'Error: ' + error.toString() };
	}
} // saveResponse

// Aggregate results and output to "Aggregated Results" sheet
function aggregateResults() 
{
	// Using getActiveSpreadsheet() works when script is container-bound to a spreadsheet
	const ss = SpreadsheetApp.getActiveSpreadsheet();
	const responseSheet = ss.getSheetByName('Responses');
	
	if (!responseSheet) 
	{
		Browser.msgBox('Error', 'No Responses sheet found. Complete some surveys first.', Browser.Buttons.OK);
		return;
	}
	
	const data = responseSheet.getDataRange().getValues();
	
	if (data.length <= 1) 
	{
		Browser.msgBox('Error', 'No response data found. Complete some surveys first.', Browser.Buttons.OK);
		return;
	}

	const aggregation = {
		overall: {
		original_wins: 0,
		improved_wins: 0,
		ties: 0,
		total_comparisons: 0
		},
		by_prompt: {}
	};

	// Skip header row
	for (let i = 1; i < data.length; i++) 
	{
		const [
			timestamp, 
			sessionId, 
			questionIndex, 
			// prompt, 
			// response1, 
			// response2, 
			response1Type, 
			response2Type, 
			rating, 
			winner, 
			completedAll
		] = data[i];
		
		if (!rating) 
			continue;
		
		// Overall statistics
		aggregation.overall.total_comparisons++;
		if (winner === 'original')
			aggregation.overall.original_wins++;
		else if (winner === 'improved') 
			aggregation.overall.improved_wins++;
		else
			aggregation.overall.ties++;
		
		// Per-prompt statistics
		if (!aggregation.by_prompt[questionIndex]) 
		{
			aggregation.by_prompt[questionIndex] = {
				original_wins: 0,
				improved_wins: 0,
				ties: 0,
				count: 0
			};
		}
		
		aggregation.by_prompt[questionIndex].count++;
		if (winner === 'original')
			aggregation.by_prompt[questionIndex].original_wins++;
		else if (winner === 'improved')
			aggregation.by_prompt[questionIndex].improved_wins++;
		else
			aggregation.by_prompt[questionIndex].ties++;
	}

	// Create or clear aggregation sheet
	let outputSheet = ss.getSheetByName('Aggregated Results');
	if (!outputSheet)
		outputSheet = ss.insertSheet('Aggregated Results');
	else
		outputSheet.clear();
	

	// Write overall statistics
	outputSheet.appendRow(['OVERALL STATISTICS']);
	outputSheet.appendRow(['Metric', 'Value', 'Percentage']);
	
	const totalComparisons = aggregation.overall.total_comparisons;
	outputSheet.appendRow([
		'Total Comparisons', 
		totalComparisons, 
		'100%'
	]);
	outputSheet.appendRow([
		'Original Model Wins', 
		aggregation.overall.original_wins,
		((aggregation.overall.original_wins / totalComparisons) * 100).toFixed(1) + '%'
	]);
	outputSheet.appendRow([
		'Improved Model Wins', 
		aggregation.overall.improved_wins,
		((aggregation.overall.improved_wins / totalComparisons) * 100).toFixed(1) + '%'
	]);
	outputSheet.appendRow([
		'Ties', 
		aggregation.overall.ties,
		((aggregation.overall.ties / totalComparisons) * 100).toFixed(1) + '%'
	]);
	
	outputSheet.appendRow([]);
	outputSheet.appendRow(['BY PROMPT STATISTICS']);
	outputSheet.appendRow([
		'Prompt', 
		'Original Wins', 
		'Improved Wins', 
		'Ties', 
		'Total', 
		'Original Win Rate', 
		'Improved Win Rate'
	]);

	for (const prompt in aggregation.by_prompt) 
	{
		const data = aggregation.by_prompt[prompt];
		const originalRate = ((data.original_wins / data.count) * 100).toFixed(1) + '%';
		const improvedRate = ((data.improved_wins / data.count) * 100).toFixed(1) + '%';
		
		outputSheet.appendRow([
		prompt,
		data.original_wins,
		data.improved_wins,
		data.ties,
		data.count,
		originalRate,
		improvedRate
		]);
	}

	// Format the sheet
	const headerRange1 = outputSheet.getRange(1, 1, 1, 3);
	headerRange1.setFontWeight('bold');
	headerRange1.setBackground('#1a73e8');
	headerRange1.setFontColor('#ffffff');
	
	const headerRange2 = outputSheet.getRange('A7:G7');
	headerRange2.setFontWeight('bold');
	headerRange2.setBackground('#1a73e8');
	headerRange2.setFontColor('#ffffff');
	
	outputSheet.autoResizeColumns(1, 7);

	Browser.msgBox('Success', 'Aggregation complete! Check the "Aggregated Results" sheet.', Browser.Buttons.OK);
} // aggregateResults