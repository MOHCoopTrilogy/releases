"""finish_media.py - after the q7.json re-shoot: contact sheets (720/1080/1440/3440/219/43), defect crops, the 1080 MP4 and its
720 copy, into ../media and H:\\hzm_work\\attic_polish."""
import os, subprocess, sys

H = os.path.dirname(os.path.abspath(__file__))
RUNS = r"H:\hzm_work\attic_polish\runs"
MEDIA = os.path.join(H, "..", "media")
subprocess.check_call([sys.executable, os.path.join(H, "make_contacts.py"), RUNS, MEDIA])
subprocess.check_call([sys.executable, os.path.join(H, "make_crops.py"), RUNS, os.path.join(MEDIA, "defect_crops.jpg")])
vid = os.path.join(RUNS, "vid_after_1080")
full = r"H:\hzm_work\attic_polish\attic_polish_1080.mp4"
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "20", "-i", os.path.join(vid, "v%05d.jpg"), "-c:v", "libx264", "-preset", "slow",
                       "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", full])
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", full, "-vf", "scale=1280:-2", "-c:v", "libx264", "-preset", "slow", "-crf", "26",
                       "-pix_fmt", "yuv420p", "-movflags", "+faststart", os.path.join(MEDIA, "attic_polish_720.mp4")])
print("media done:", sorted(os.listdir(MEDIA)), os.path.getsize(full))
