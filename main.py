import requests
import re
import os
import subprocess
import shutil

ROOT = os.path.dirname(__file__)

def get_season_episode(html):
    season = re.findall(r"\"seasonNumber\":([0-9]+)", html)[0]
    episode = re.findall(r"\"episodeNumber\":([0-9]+)", html)[0]
    return season, episode

def combine_parts(folder_path, destination_path):
    if not os.path.exists(os.path.dirname(destination_path)):
        os.makedirs(os.path.dirname(destination_path))
    files = os.listdir(folder_path)
    files.sort()
    combine_textfile_path = os.path.join(folder_path, "list.txt")
    with open(combine_textfile_path,"w") as f:
        f.writelines([f"file '{file}'\n" for file in files if ".mp4" in file])
    subprocess.run(f"ffmpeg -f concat -i {combine_textfile_path} -c copy -scodec copy {destination_path}", shell=True)

def cleanup_files(folder_path):
    files = os.listdir(folder_path)
    for file in files:
        if file == "final.mp4":
            continue
        os.remove(os.path.join(folder_path, file))


def merge_video_with_subtitles(path_video, path_subtitles, path_destination):
    subprocess.run(f"ffmpeg -i {path_video} -i {path_subtitles} -c copy -c:s mov_text {path_destination}", shell=True)
    os.remove(path_subtitles)
    if path_video != path_destination:
        os.remove(path_video)

def create_temp_folder(episode):
    folder_path = os.path.join(ROOT,"temp", episode)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def get_website_html(url):
    return requests.get(url).text

def get_episode_uuid(html):
    reg = r""""uri":"mgid:arc:episode:southpark\.intl:([0-9a-z\-]+)"""
    return re.findall(reg, html)[0]

def get_episode_parts(episode_url, uuid):
    ref_url = f"https://media.mtvnservices.com/pmt/e1/access/index.html\
        ?uri=mgid:arc:episode:southpark.intl:{uuid}\
        &configtype=edge\
        &ref={episode_url}\
        ".replace(" ","")
    js = requests.get(ref_url).json()
    episode_parts = [x["group"]["content"].replace("{device}", "iphone") for x in js["feed"]["items"]]
    return episode_parts

def download_episode_part(xml_url, folder_path, index):
    #get xml content as str
    xml = requests.get(xml_url).text
    #retrieve .m3u8 path
    vid_m3u8 = re.findall(r"<src>(.*)<\/src>", xml)[0]
    #retrieve path to subtitles
    sub = re.findall(r"<typographic format=\"vtt\" src=\"(.*)\"\/>", xml)[0].replace("amp;","")
    #set pathes
    subtitle_path = os.path.join(folder_path,f"sub{index}.vtt")
    vid_path = os.path.join(folder_path, f"vid{index}.mp4")
    #retrieve subtitles & save to file
    with open(subtitle_path, "w") as f:
        f.write(requests.get(sub).text)
    #download video
    subprocess.run(f"ffmpeg -i \"{vid_m3u8}\" -vcodec copy -acodec copy {vid_path}", shell=True)
    #merge vide with subtitles
    merge_video_with_subtitles(vid_path, subtitle_path, vid_path.replace(".mp4","_merged.mp4"))


def download_episode(episode_url, destination_path = ROOT, languages = ["de"]):

    #Create temp folder
    if not os.path.exists(os.path.join(ROOT, "temp")):
        os.makedirs(os.path.join(ROOT, "temp"))

    #get episde html for retrieving episode uuid
    html = get_website_html(episode_url)

    #Get season & episode
    season, episode = get_season_episode(html)
    destination_path = os.path.join(destination_path,"downloads", season, f"Southpark_S{season:0>2}E{episode:0>2}.mp4")
    print(destination_path)
    #get array of all episode parts. Array contains urls to xml with link to .m3u8 file
    parts = get_episode_parts(episode_url, get_episode_uuid(html))
    #Path where episode files are temporarily stored
    temp_path = create_temp_folder(season.zfill(2)+episode.zfill(2))
    #Download all episode parts
    for i, part in enumerate(parts):
        download_episode_part(part, temp_path, i)
    #Combine Parts into single file
    combine_parts(temp_path, os.path.join(temp_path, destination_path))
    cleanup_files(temp_path)
    

def main():
    download_episode("https://www.southpark.de/folgen/hrno4n/south-park-urlaub-mit-kenny-butters-staffel-16-ep-11")
if __name__ == "__main__":
    main()