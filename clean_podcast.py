#!/usr/bin/env python3
"""
Podcast Transcript Cleaner
Extracts YouTube transcripts and cleans them using Gemini Pro.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import json
from pathlib import Path

from google import genai
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise Exception(f"Could not extract video ID from URL: {url}")


def get_video_info(url: str) -> dict:
    """Extract video title and ID from YouTube URL using oembed API."""
    video_id = extract_video_id(url)

    # Use YouTube's oembed API to get video title (no auth required)
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with urllib.request.urlopen(oembed_url) as response:
            data = json.loads(response.read().decode())
            return {"title": data.get("title", "Unknown Title"), "id": video_id}
    except Exception as e:
        raise Exception(f"Failed to get video info: {e}")


def extract_transcript(url: str) -> str:
    """Extract transcript from YouTube video using yt-dlp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download subtitles using yt-dlp
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", "en",
                "--skip-download",
                "--sub-format", "vtt",
                "-o", f"{tmpdir}/%(id)s.%(ext)s",
                url,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise Exception(f"Failed to extract transcript: {result.stderr}")

        # Find the subtitle file
        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if not vtt_files:
            raise Exception("No transcript found for this video")

        vtt_file = vtt_files[0]

        # Parse VTT and extract text
        with open(vtt_file, "r", encoding="utf-8") as f:
            content = f.read()

        return parse_vtt(content)


def parse_vtt(vtt_content: str) -> str:
    """Parse VTT file and extract clean text."""
    lines = vtt_content.split("\n")
    text_lines = []
    seen_lines = set()

    for line in lines:
        # Skip headers, timestamps, and empty lines
        line = line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}", line):  # Timestamp line
            continue
        if re.match(r"^[\d\-:.\s>]+$", line):  # Cue identifier
            continue

        # Remove VTT formatting tags
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"&nbsp;", " ", line)

        # Skip duplicates (auto-subs often repeat)
        if line not in seen_lines:
            seen_lines.add(line)
            text_lines.append(line)

    return " ".join(text_lines)


def generate_takeaways(transcript: str, video_title: str, api_key: str) -> str:
    """Generate top 5 takeaways from the transcript using Gemini."""
    client = genai.Client(api_key=api_key)

    prompt = f"""Read this transcript for "{video_title}" and extract the top 5 takeaways.

Each takeaway should be:
- One sentence
- Include a direct quote from the transcript (use quotation marks)
- Capture a key insight, announcement, or important point

Format as a bullet list with exactly 5 items.

TRANSCRIPT:
{transcript}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def clean_transcript_with_gemini(transcript: str, video_title: str, api_key: str) -> str:
    """Use Gemini Pro to clean up the transcript."""
    client = genai.Client(api_key=api_key)

    prompt = f"""Clean up this podcast transcript for "{video_title}".

Combine paragraphs from the same speaker, fix capitalization and punctuation, remove filler words like unnecessary "like"s "you know"s and "um"s, and remove repeated words. If there are names, use context clues to figure out who it is. Make sure all sentences are grammatical, but do not add new phrases/clauses/ideas of your own.

Split the transcript into natural paragraphs, where each paragraph is maximum 200 words. For podcasts with multiple speakers, there should always be a line break between each speaker's section and the next (even if this results in short paragraphs).

After cleaning the transcript, add chapters to split up sections/themes. Give each chapter a bolded title and insert them into the transcript as subheaders (use ### markdown formatting). The title should be a single short sentence expressing the key takeaway of that chapter.

Otherwise, modify the original substance the minimum amount. Make sure the transcript is complete and not missing chunks. Be very meticulous.

TRANSCRIPT:
{transcript}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def sanitize_filename(title: str) -> str:
    """Convert video title to a safe filename."""
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', "", title)
    safe = re.sub(r"\s+", "_", safe)
    return safe[:100]  # Limit length


def process_video(url: str, api_key: str, progress_callback=None) -> dict:
    """
    Process a YouTube video and return the cleaned transcript with takeaways.

    Args:
        url: YouTube video URL
        api_key: Google AI API key
        progress_callback: Optional callback function for progress updates

    Returns:
        dict with keys: title, url, takeaways, transcript, markdown, filename
    """
    def update_progress(message):
        if progress_callback:
            progress_callback(message)

    update_progress("Getting video info...")
    info = get_video_info(url)

    update_progress("Extracting transcript...")
    raw_transcript = extract_transcript(url)

    update_progress("Cleaning transcript with Gemini...")
    transcript = clean_transcript_with_gemini(raw_transcript, info["title"], api_key)

    update_progress("Generating takeaways...")
    takeaways = generate_takeaways(transcript, info["title"], api_key)

    # Build markdown content with thumbnail
    thumbnail_url = f"https://img.youtube.com/vi/{info['id']}/maxresdefault.jpg"
    markdown = f"![Thumbnail]({thumbnail_url})\n\n"
    markdown += f"# {info['title']}\n\n"
    markdown += f"Source: {url}\n\n"
    markdown += "## Top Takeaways\n\n"
    markdown += takeaways
    markdown += "\n\n---\n\n"
    markdown += "## Full Transcript\n\n"
    markdown += transcript

    filename = f"{sanitize_filename(info['title'])}.md"

    return {
        "title": info["title"],
        "url": url,
        "takeaways": takeaways,
        "transcript": transcript,
        "markdown": markdown,
        "filename": filename,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract and clean podcast transcripts from YouTube"
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto-generated from video title)",
    )
    parser.add_argument(
        "--api-key",
        help="Google AI API key (or set GOOGLE_API_KEY env var)",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Only extract raw transcript, don't clean with Gemini",
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key and not args.raw_only:
        print("Error: Google AI API key required. Set GOOGLE_API_KEY or use --api-key")
        print("Get your API key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    try:
        # Get video info
        print("Getting video info...")
        info = get_video_info(args.url)
        print(f"Video: {info['title']}")

        # Extract transcript
        print("Extracting transcript...")
        transcript = extract_transcript(args.url)
        print(f"Extracted {len(transcript)} characters")

        if args.raw_only:
            final_transcript = transcript
            takeaways = ""
            suffix = "_raw"
        else:
            # Clean with Gemini
            print("Cleaning transcript with Gemini...")
            final_transcript = clean_transcript_with_gemini(
                transcript, info["title"], api_key
            )
            # Generate takeaways
            print("Generating takeaways...")
            takeaways = generate_takeaways(final_transcript, info["title"], api_key)
            suffix = ""

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            filename = f"{sanitize_filename(info['title'])}{suffix}.md"
            output_path = Path.home() / "podcast-cleaner" / "transcripts" / filename

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {info['title']}\n\n")
            f.write(f"Source: {args.url}\n\n")
            if takeaways:
                f.write("## Top Takeaways\n\n")
                f.write(takeaways)
                f.write("\n\n")
            f.write("---\n\n")
            f.write("## Full Transcript\n\n")
            f.write(final_transcript)

        print(f"\nSaved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
