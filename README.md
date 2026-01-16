# I Hate Video

Convert YouTube videos into clean, readable transcripts with AI-generated chapters and takeaways.

Tired of talks and podcasts being video-only? This tool takes any YouTube link and converts it to a grammatical transcript with chapters and top takeaways.

![Screenshot](i-hate-video-example.png)

## Features

- Extracts transcripts from YouTube videos
- Cleans up auto-generated captions using Gemini AI
- Adds chapter headers based on content themes
- Generates top 5 takeaways with direct quotes
- Includes video thumbnail
- MS Word 2003-inspired interface
- Export as Markdown (.md) or PDF
- Font selection (Times New Roman, Tahoma, Comic Sans, Arial, Wingdings)
- Zoom controls for adjusting text size
- Persistent cache saves results to disk

## Prerequisites

- Python 3.10+
- A Google AI API key (for Gemini)

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/jaswsunny/youtube-to-text.git
   cd youtube-to-text
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Get a Google AI API key**
   - Go to [Google AI Studio](https://aistudio.google.com/apikey)
   - Create an API key

5. **Create a `.env` file**
   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

6. **Run the app**
   ```bash
   python app.py
   ```

7. **Open in browser**
   - Go to http://127.0.0.1:8080

## Usage

1. Paste a YouTube URL into the input field
2. Click "Textify"
3. Wait for the transcript to be processed (30-60 seconds)
4. Read the transcript in the viewer
5. Use the font dropdown and zoom controls to customize the view
6. Click "Save" and choose Markdown or PDF to download

## Notes

- Requires videos to have captions (auto-generated or manual)
- Transcripts are cached to disk (`transcript_cache.json`) and persist across restarts

## Tech Stack

- Flask (Python web framework)
- yt-dlp (YouTube transcript extraction)
- Google Gemini AI (transcript cleaning)
- WeasyPrint (PDF generation)
- marked.js (Markdown rendering)

## License

MIT
