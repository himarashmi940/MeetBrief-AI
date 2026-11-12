# MeetBrief AI – Intelligent Meeting Preparation Assistant

MeetBrief AI is an AI-powered meeting preparation assistant that helps users prepare for important meetings by researching companies or individuals and generating structured meeting briefs.

Instead of manually searching multiple websites, users can enter a company or person's name and meeting context to receive a research-backed briefing.

## Features

- **Web Research:** Collects recent information using Tavily.
- **AI-Powered Analysis:** Uses Gemini through the Bifrost gateway to analyse research.
- **Meeting Brief Generation:** Creates a structured report with:
  - Company or Person Overview
  - Recent Developments
  - Important Opportunities
  - Potential Risks and Challenges
  - Important Discussion Questions
  - Suggested Meeting Strategy
  - Key Takeaways
- **PDF Export:** Generates a downloadable meeting briefing PDF.
- **Research Sources:** Includes links to supporting research sources.

## Technology Stack

- Python
- Streamlit
- Tavily API
- Gemini
- Bifrost LLM Gateway
- OpenAI Python SDK
- ReportLab
- python-dotenv

## How It Works

1. The user enters a company/person name and meeting context.
2. Tavily searches the web for relevant information.
3. Bifrost routes the request to the configured Gemini model.
4. Gemini analyses the collected research and generates a meeting brief.
5. ReportLab converts the briefing into a downloadable PDF.

## Project Structure

```text
MeetBrief-AI/
│
├── app.py
├── research.py
├── ai_analysis.py
├── pdf_generator.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/himarashmi940/MeetBrief-AI.git
cd MeetBrief-AI
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project directory and add your own API credentials:

```env
TAVILY_API_KEY=your_tavily_api_key
BIFROST_API_KEY=your_bifrost_api_key
BIFROST_BASE_URL=http://localhost:8080
BIFROST_MODEL_NAME=your_configured_model
```

Do not upload your `.env` file or expose API keys publicly.

Make sure Bifrost is running and configured with the required Gemini provider and model.

### 6. Run the application

```bash
streamlit run app.py
```

## Future Scope

- Public cloud deployment
- Calendar integration
- More research sources
- Improved meeting recommendations
- Personalised meeting preparation

## Project Goal

To make meeting preparation faster, easier and more effective through AI-powered research and intelligent analysis.
