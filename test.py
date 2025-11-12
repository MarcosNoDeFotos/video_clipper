import os
CURRENT_PATH = os.path.dirname(__file__).replace("\\", "/") + "/"
CLIPS_FOLDER = 'static/clips'
VIDEOS_DIR = "f:\\Documentos"


videos = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))]
videosData = []

for video in videos:
    extension = video.split(".")[-1]
    clipCount = [f for f in os.listdir(CLIPS_FOLDER) if (f.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) and f.lower().startswith(video.replace(f".{extension}", "")))]
    for f in os.listdir(CLIPS_FOLDER):
        if (f.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) and f.lower().startswith(video.lower().replace(f".{extension}", ""))):
            print("aaaa")
    videosData.append({"video": video, "clips" : clipCount.__len__()})
print(videosData)