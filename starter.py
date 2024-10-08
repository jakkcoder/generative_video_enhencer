from fastapi import FastAPI, HTTPException
import os
import subprocess
import requests

app = FastAPI()

# Directory paths
BASE_DIR = "/app/Documents"
AUDIO_DIR = os.path.join(BASE_DIR, "temp/Audio")
VIDEO_DIR = os.path.join(BASE_DIR, "temp/Video")
TEMP_AUDIO_DIR = os.path.join(BASE_DIR, "temp/Audio/input")
TEMP_VIDEO_DIR = os.path.join(BASE_DIR, "temp/Video/input")
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Audio and Video specific directories
DIRECTORIES = [
    os.path.join(AUDIO_DIR, "input"),
    os.path.join(AUDIO_DIR, "output"),
    os.path.join(AUDIO_DIR, "temp_input"),
    os.path.join(AUDIO_DIR, "temp_output"),
    os.path.join(AUDIO_DIR, "final_output"),
    os.path.join(VIDEO_DIR, "input"),
    os.path.join(VIDEO_DIR, "output"),
    os.path.join(VIDEO_DIR, "temp_input"),
    os.path.join(VIDEO_DIR, "temp_output"),
    os.path.join(VIDEO_DIR, "final_output"),
    INPUT_DIR,
    OUTPUT_DIR
]

def create_directories():
    """Create the directory structure if it doesn't exist."""
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        else:
            print(f"Directory already exists: {directory}")

def split_audio_video(file_path):
    """Separate video from audio and save them in the temp directory."""
    filename = os.path.basename(file_path).split('.')[0]

    video_output_path = os.path.join(TEMP_VIDEO_DIR, f"{filename}_plain.mp4")
    audio_output_path = os.path.join(TEMP_AUDIO_DIR, f"{filename}.wav")

    # Logging the FFmpeg commands
    print(f"Splitting video and audio for file: {file_path}")
    print(f"Video output path: {video_output_path}")
    print(f"Audio output path: {audio_output_path}")

    # Commands to extract video and audio with the -y flag to overwrite existing files
    video_command = ["ffmpeg", "-y", "-i", file_path, "-an", video_output_path]
    audio_command = ["ffmpeg", "-y", "-i", file_path, "-q:a", "0", "-map", "a", audio_output_path]

    subprocess.run(video_command)
    subprocess.run(audio_command)

    return video_output_path, audio_output_path

def call_video_processing_api(video_file):
    """Call the external video processing API."""
    print(f"Calling video processing API for file: {video_file}")
    
    url = "http://video-processing-service:8080/process_video"  # Correct endpoint for video processing
    
    # Instead of sending the file, send a JSON payload
    data = {
        "file_path": video_file  # Send the file path or any other necessary data in the JSON payload
    }
    
    response = requests.post(url, json=data)  # Send JSON data

    if response.status_code != 200:
        print(f"Video processing failed with status code: {response.status_code}")
        raise HTTPException(status_code=response.status_code, detail="Video processing failed.")
    
    print("Video processing successful")
    return os.path.join(VIDEO_DIR, "final_output", os.path.basename(video_file))


def call_audio_processing_api(audio_file):
    """Call the external audio processing API."""
    print(f"Calling audio processing API for file: {audio_file}")
    
    url = "http://audio-processing-service:5000/process"  # Correct endpoint for audio processing
    
    # Send a POST request without any data (as per the curl request)
    response = requests.post(url)

    if response.status_code != 200:
        print(f"Audio processing failed with status code: {response.status_code}")
        raise HTTPException(status_code=response.status_code, detail="Audio processing failed.")
    
    print("Audio processing successful")
    return os.path.join(AUDIO_DIR, "final_output", os.path.basename(audio_file))


def combine_audio_video(video_file, audio_file, output_file):
    """Combine audio and video and save the final output."""
    print(f"Combining video file: {video_file} with audio file: {audio_file}")
    print(f"Final output file: {output_file}")
    
    combine_command = [
        "ffmpeg", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", output_file
    ]
    subprocess.run(combine_command)

@app.get("/process_file")
def process_file():
    # Ensure directory structure exists
    create_directories()

    # Check for files in the input directory
    input_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".mp4")]

    if not input_files:
        print("No .mp4 file found in input directory.")
        raise HTTPException(status_code=404, detail="No .mp4 file found in input directory.")

    print(f"Found {len(input_files)} files in {INPUT_DIR}")

    # Process each .mp4 file in the input directory
    for input_file in input_files:
        input_file_path = os.path.join(INPUT_DIR, input_file)

        # Step 1: Split audio and video
        print(f"Processing file: {input_file_path}")
        video_file, audio_file = split_audio_video(input_file_path)

        # Step 2: Call audio processing API
        processed_audio_file = call_audio_processing_api(audio_file)
 
        # Step 3: Call video processing API
        processed_video_file = call_video_processing_api(video_file)

        # Step 4: Combine the processed audio and video
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.basename(input_file).split('.')[0]}_final.mp4")
        combine_audio_video(processed_video_file, processed_audio_file, output_file)

    print(f"Processing complete. All files saved to: {OUTPUT_DIR}")
    return {"message": "Processing complete", "output_directory": OUTPUT_DIR}
