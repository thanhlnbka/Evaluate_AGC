import zmq
import time
import json
import numpy as np
import pandas as pd
import ast
import os 
import subprocess
import sys
import random


def merge_csvs_into_one(camid):
    path_csv_merge = f"/workspace/build/data/csvs/cam{camid}_result.csv"
    os.system(f"rm -rf {path_csv_merge}")
    path_csvs = sorted(os.listdir(f"/workspace/build/data/csvs/cam{camid}"))
    
    # print(path_csvs)
    cmd = " ".join([f"/workspace/build/data/csvs/cam{camid}/" + i for i in path_csvs])
    os.system(f"csvstack {cmd} > {path_csv_merge}")

    return path_csv_merge



def publish_data(socket, topic, df_data, camid, res):
    frameids = []
    frame_tracks = []
    frame_scores = []
    dict_pid_poses = {}
    dict_pid_scores = {}
    last_frame = -1

    d_pids = {}
    for index, data in df_data.iterrows():
        pose_numpy = np.array(ast.literal_eval(data["POSES"])).reshape((18, 2))
        frameid = data["FRAMEID"]
        score = ast.literal_eval(data["SCORE"])
        pid = data["PID"]
        if pid not in d_pids:
            d_pids[pid] = frameid
        if frameid == last_frame or last_frame == -1:
            dict_pid_poses[pid] = pose_numpy
            dict_pid_scores[pid] = score
        else:
            frameids.append(last_frame)
            frame_tracks.append(dict_pid_poses)
            frame_scores.append(dict_pid_scores)
            dict_pid_poses = {}
            dict_pid_scores = {}
            dict_pid_poses[pid] = pose_numpy
            dict_pid_scores[pid] = score
        last_frame = frameid
        
    # Save data to csv
    data_csv = [{"camid": f"cam{camid}", "frameid": v, "pid": k} for k,v in d_pids.items()]
    df_data_csv = pd.DataFrame(data_csv)
    os.makedirs("send_sdk", exist_ok=True)
    df_data_csv.to_csv(f"send_sdk/cam{camid}_sdk.csv", index=False)

    biggest_frame = max(frameids)
    print(biggest_frame)
    #Fake more than 50 frames with no data
    for j in range(1,50):
        frameids.append(biggest_frame+j)
    
    for i in range(0, len(frameids)):
        print(f"Cam{camid} Frame {frameids[i]}")
        if frameids[i] >= biggest_frame:
            track_pids = []
            track_pose = []
            track_score = []
        else: 
            track_pids = [i for i in frame_tracks[i].keys()]
            track_pose = [pose.tolist() for pose in frame_tracks[i].values()]
            track_score = [score for score in frame_scores[i].values()]
            

        data = {
            "frame_id": frameids[i],
            'processing_width': 640, # input shape model
            'processing_height': 360, # input shape model
            'stream_width': res[camid][0], # input shape rtsp
            'stream_height': res[camid][1], # input shape rtsp
            'track_pids': track_pids,
            'track_pose': track_pose,
            'track_score': track_score
        }
        print("Track ids: ", track_pids)
        
        message = json.dumps(data).encode()
        socket.send_multipart([topic, message])
        time.sleep(0.2)

def sender_zmq(camid, res):
    port_zmq = 1111 + camid
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port_zmq}")
    topic = f"cam{camid}/agc_data"

    # path_csv = os.listdir(f"/workspace/build/data/csvs/cam{camid}")
    # path_file_csv = f"/workspace/build/data/csvs/cam{camid}/" + path_csv[0]

    path_file_csv = merge_csvs_into_one(camid)
    df_data = pd.read_csv(path_file_csv)
    
    publish_data(socket, topic.encode(), df_data, camid, res)

if __name__ == "__main__":
    import threading 
    threads = []
    # res = {9: (1280,720), 12: (1280,720)}
    
    ### MDBA1
    res = {
        i: (1280, 720) for i in range(1,15) 
    }

    ### MDBA2
    res.update({
        i: (1280, 720) for i in range(15,37) 
    })

    ### WIN + HH 
    res.update({
        # 1000: (1280,720), 
        1001:(1280,720), 
        1002: (1280,720), 
        1003:(1280,720), 
        1004:(1280,720), 
        1005: (1920,1080),
        1006: (1920,1080),
        1007: (1920,1080)
    })

    ## Exhibition Dataset
    # res.update({
    #     2000 + i: (1280,720) for i in range(1,33)
    # })
    #lan1
    res.update({
        i: (1280,720) for i in range(2000,2030)
    })
    #lan2 
    res.update({
        i: (1280,720) for i in range(2030,2060)
    })
    #lan3
    res.update({
        i: (1280,720) for i in range(2060,2090)
    })
    #lan4
    res.update({
        i: (1280,720) for i in range(2090,2120) if i != 2112
    })

    # #lan5
    res.update({
        i: (1280,720) for i in range(2120,2158)
    })

    # MBDA case
    res.update({i:(1280,720) for i in range(3000,30000)})


    if len(sys.argv) < 2:
        print("Usage: python send_cam.py <comma-separated list of numbers>")
    
    numbers = sys.argv[1].split(',')
    
    numbers = [int(num) for num in numbers]
    for camid in numbers:
        threading.Thread(target=sender_zmq, args=(camid,res, )).start()
    