import json
import os
import glob
import pandas as pd
from tqdm import tqdm
import cv2
import numpy as np
import sys
from PIL import Image
# Scale factor = 2 since org image is 1280*720

SCALE_FACTOR = 2
FONT_SIZE = 0.75





def get_status_msg(status):
    if status == -1:
        return "out of frame, zero pose"
    elif status == -2:
        return "wasn't walking"
    elif status == -3:
        return "wasn't not front view"
    elif status == -4:
        return "wasn't pass overlapped"
    elif status == -5:
        return "wasn't pass dark image"
    elif status == -6:
        return "wasn't pass face dircetion"
    elif status == -7:
        return "wasn't pass face blur"
    elif status == -8: 
        return "wasn't pass min body size"
    elif status == -9: 
        return "wasn't pass min head size"

def convert_pose_str_to_list(pose_str, scale_factor):
    pose_extract = pose_str.strip('[]').split(',')
    pose_list = []
    for i in range(0, len(pose_extract), 2):
        pose_list.append((int(pose_extract[i])*scale_factor, int(pose_extract[i+1])*scale_factor))
    return np.array(pose_list)

def draw_text_with_bg(overlay, text, x_mean, y_mean, color, bg, padding, font_size, thickness) :
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_PLAIN, font_size, thickness)
    text_org = (int(x_mean - text_size[0][0]/2), y_mean)

    cv2.rectangle(overlay, (text_org[0] - padding, text_org[1] -text_size[0][1] - padding), \
            (text_org[0] + text_size[0][0] + padding, text_org[1] + padding), bg, -1)
    cv2.putText(overlay, text, text_org, cv2.FONT_HERSHEY_PLAIN, font_size, color, thickness)
    return text_size[0][1] + 2*padding

def parse_log_file(log_file):
    df = pd.read_csv(log_file, names=['frameid', 'pid', 'status'])
    return df


def get_box_from_pose(pose_points, expansion_factor=1.2):
    min_x = min(pose_points[:, 0])
    max_x = max(pose_points[:, 0])
    min_y = min(pose_points[:, 1])
    max_y = max(pose_points[:, 1])
    
    width = max_x - min_x
    height = max_y - min_y
    
    expanded_width = width * expansion_factor
    expanded_height = height * expansion_factor
    
    center_x = (max_x + min_x) / 2
    center_y = (max_y + min_y) / 2
    
    expanded_min_x = max(center_x - expanded_width / 2, 0)
    expanded_max_x = min(center_x + expanded_width / 2,sys.maxsize)
    expanded_min_y = max(center_y - expanded_height / 2, 0)
    expanded_max_y = min(center_y + expanded_height / 2, sys.maxsize)
    
    return (int(expanded_min_x), int(expanded_min_y), int(expanded_max_x), int(expanded_max_y))

AGE_GROUPS = {
    0: [0, 9],
    1: [10, 19],
    2: [20, 39],
    3: [40, 64],
    4: [65, 100]
}

def get_age_group(age):
    for key, value in AGE_GROUPS.items():
        try:
            age_rd = round(float(age),2)
        except:
            age_rd = age
        if age_rd >= value[0] and age_rd <= value[1]:
            return key , value
    return None

def visualize_agc(org_path, dataset):
    base_path = os.path.join(org_path, dataset)
    agc_results_path = os.path.join("/media/safe_nas_storage/60_Dev/604_Product/609_BLM/EVAL_SDK_AGC_refactor_python/agc_results/ensemble_model_eval_25_8_2vote", f"{dataset}_output")
    
    base_image_path = os.path.join(base_path, 'images')
    base_csvs_path =  os.path.join(base_path, 'csvs')
    base_agc_path = os.path.join(agc_results_path, 'agc_outputs')
    base_log_path = os.path.join(agc_results_path, 'logfilter')

    preds_final_result_path = os.path.join(agc_results_path, "data_preds")

    cam_list = sorted(os.listdir(base_csvs_path))
    # path_save_video_visual = "debug_videos_visual"
    path_save_video_visual = f'/media/safe_nas_storage/60_Dev/604_Product/609_BLM/EVAL_SDK_AGC_refactor_python/agc_visulizes/result_ensemble_model_eval_25_8_2vote_forcustomer/{dataset}'
    os.makedirs(path_save_video_visual, exist_ok=True)
    for cam in tqdm(cam_list):
        if cam == "cam1000": 
            continue
        idx = int(cam.strip('cam'))

        path_img = os.path.join(base_image_path, cam)
        path_csv = os.path.join(base_csvs_path, cam)
        path_pred = os.path.join(preds_final_result_path, f"{cam}.csv")
        print(path_pred)
        if not os.path.exists(path_pred):
            continue
        try:
            df_results = pd.read_csv(path_pred)
        except:
            continue
        # pids_only_show = df_results["pid"].tolist()
        # print("hihi")
        # print(df_results)

        if os.path.exists(f'{path_save_video_visual}/{cam}.mp4'):
            print(f'THIS VIDEO HAS ALREADY BEEN DONE {cam}')
            continue

        if not os.path.exists(path_img):
            print(f'THIS VIDEO HAS NO IMAGES {cam}')
            continue
            
        if not os.path.exists(path_csv):
            print(f'THIS VIDEO HAS NO CSVS {cam}')
            continue
            
        if len(os.listdir(path_img)) < 5*2:
            print(f'THIS VIDEO HAS TOO FEW FRAMES {cam}')
            continue

        csvs_list = glob.glob(os.path.join(base_csvs_path, cam) + '/*.csv')
        images_list = glob.glob(os.path.join(base_image_path, cam) + '/*.jpeg')
        agc_list = glob.glob(os.path.join(base_agc_path, cam) + '/*_orgbody.jpg')
        log_path = os.path.join(base_log_path, cam + '.log')
        if  not os.path.exists(log_path):
            continue

        # print("hihi")
        df_log = parse_log_file(log_path)

        df_ls = []
        for csv_file in csvs_list:
            df_single = pd.read_csv(csv_file)
            df_ls.append(df_single)
        df_pose = pd.concat(df_ls).sort_values(by=['FRAMEID']).reset_index(drop=True)
        
        agc_pid_ls = []
        agc_fid_ls = []
        agc_gender_ls = []
        agc_age_ls = []
        agc_img_ls = []
        for agc_output in agc_list:
            agc_output_info = agc_output.split('/')[-1].split('_')
            agc_pid_ls.append(int(agc_output_info[0].strip('P')))
            agc_fid_ls.append(int(agc_output_info[1]))
            agc_gender_ls.append(agc_output_info[2])
            agc_age_ls.append(agc_output_info[3])
            agc_img_ls.append(agc_output)
        df_agc = pd.DataFrame.from_dict({'pid': agc_pid_ls, 'frameid': agc_fid_ls, 'gender': agc_gender_ls, 'age': agc_age_ls, 'img_path': agc_img_ls})

        
        output = cv2.VideoWriter(f'{path_save_video_visual}/{cam}.mp4' , cv2.VideoWriter_fourcc(*'MP4V'), 5, (1280,720))

        frame_list = df_pose['FRAMEID'].unique()
        

        frame_logs = df_log["frameid"].tolist()
        largest_frame = max(frame_logs)

        for frame in tqdm(frame_list):
            
            df_log_frame = df_log.loc[df_log['frameid'] == frame].reset_index(drop=True)
            df_frame = df_pose.loc[df_pose['FRAMEID'] == frame].reset_index(drop=True)
            df_agc_frame = df_agc.loc[df_agc['frameid'] == frame].reset_index(drop=True)
            full_img_path = os.path.join(base_image_path, cam) + f'/frame_{frame}.jpeg'
            if os.path.exists(full_img_path):
                image = cv2.imread(os.path.join(base_image_path, cam) + f'/frame_{frame}.jpeg')
                image_to_crop = image.copy()
            else:
                continue
            draw_text_with_bg(image, 'Num_frame: {}'.format(str(frame)), 65, 10, (255, 255, 255), (255,0,0), 1, 1, 1)

            pid_to_draw_box = df_agc_frame['pid'].unique()
            pid_not_to_draw_box = [pid_failed for pid_failed in df_frame['PID'].unique() if pid_failed not in pid_to_draw_box]

            all_poses = {}
            for _, row in df_frame.iterrows():
                pid = row['PID']
                pose = convert_pose_str_to_list(row['POSES'], SCALE_FACTOR)
                # print(pose)
                all_poses[pid] = pose

            # for pid in pid_not_to_draw_box:
            #     filtered_df = df_log_frame.loc[df_log_frame['pid'] == pid]
            #     if filtered_df.shape[0] > 0:
            #         row = df_log_frame.loc[df_log_frame['pid'] == pid].iloc[0]
            #         status = row['status']
            #     else:
            #         status = 0
            #     msg = get_status_msg(status)
            #     pose = all_poses[pid]
            #     pose = pose[np.all(pose != 0, axis=1)]
            #     pose_mean = np.mean(pose, axis=0).astype(np.int32)
            #     draw_text_with_bg(image, f'PID: {pid} | {msg}',\
            #                     pose_mean[0], pose_mean[1], (255, 255, 255), (0,0,255), 1, FONT_SIZE, 1)

            

            image_head_list = []
            for pid in pid_to_draw_box:
                
                row = df_frame.loc[df_frame['PID'] == pid].iloc[0]
                gender = df_agc_frame.loc[df_agc_frame['pid'] == pid].iloc[0]['gender']
                age = df_agc_frame.loc[df_agc_frame['pid'] == pid].iloc[0]['age']
                pose = convert_pose_str_to_list(row['POSES'], SCALE_FACTOR)

                bbox = get_box_from_pose(pose)

                head_im = cv2.imread(f"{base_agc_path}/{cam}/P{pid}_{frame}_{gender}_{age}_orghead.jpg")
                # print(head_im.shape)


                
                head_im = cv2.resize(head_im, (64, 64))

                draw_text_with_bg(head_im, f'PID: {pid}',\
                                20, 10, (255, 255, 255), (0,255,0), 1, 1, 1)
                image_head_list.append(head_im)

                cv2.rectangle(image, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255,0,0), 1)
                age_group__ , value__= get_age_group(age)
                draw_text_with_bg(image, f'PID: {pid} | GENDER: {gender} | AGE_GROUP: {value__[0]}-{value__[1]}',\
                                int((bbox[0] + bbox[2])/2), int((bbox[1] + bbox[3])/2), (0, 0, 0), (0,255,0), 1, FONT_SIZE, 1)

                
                age_final = df_results.loc[df_results["pid"] == pid, "age"]
                if not age_final.empty:
                    _,value_age_group_final = get_age_group(age_final.iloc[0])
                else:
                    value_age_group_final = None

                gender_final = df_results.loc[df_results["pid"] == pid, "gender"]
                if not gender_final.empty:
                    value_gender_final = gender_final.iloc[0]
                    str_get_gender_final = "M" if value_gender_final == 1 else "F"
                else:
                    value_gender_final = None
                    str_get_gender_final = None

                if value_age_group_final is not None and value_gender_final is not None:
                    draw_text_with_bg(image, f'FINAL: GENDER: {str_get_gender_final} | AGE_GROUP: {value_age_group_final[0]}-{value_age_group_final[1]}', \
                                    int((bbox[0] + bbox[2])/2), int((bbox[1] + bbox[3])/2+25), (255, 255, 255), (0,0,0), 1, FONT_SIZE, 1)

            if len(image_head_list) > 0:
                concated_head = cv2.hconcat(image_head_list)
                top_left_x = 15
                top_left_y = 15
                image[top_left_x: top_left_x + concated_head.shape[0], top_left_y:top_left_y + concated_head.shape[1]] = concated_head

            # if frame >= largest_frame - 10:
            #     y_visul = 90
            #     for idx, df_res in df_results.iterrows():
            #         pid_ = df_res["pid"]
            #         age_ = df_res["age"]
            #         gender_ = df_res["gender"]
            #         age_group_, value_ = get_age_group(age_)
            #         str_gender = "F"
            #         if gender_  == 1:
            #             str_gender = "M"
                    
            #         draw_text_with_bg(image, f'FINAL RESULT: PID {pid_} | GENDER: {str_gender} | AGE_GROUP: {value_[0]}-{value_[1]}',\
            #                         235, y_visul, (255, 255, 255), (0,0,0), 1, 1, 1)
            #         y_visul += 50

            output.write(image)
        output.release()
            

if __name__ == "__main__":
    # base_path = '/media/safe_nas_storage/80_Workspace/803_Product/2-2_AGC/rerun_02082023/'
    org_path = '/media/safe_nas_storage/60_Dev/604_Product/609_BLM/EVAL_SDK_AGC_refactor_python/sdk_results'
    # datasets = ['Exhibition', 'MBDA1', 'MBDA2', 'WIN_HH']
    # datasets = ['MBDA_case', 'Exhibition', 'WIN_HH']
    
    # datasets = ["Exhibition"]
    datasets = ["WIN_HH"]

    for dataset in datasets:
        print(f'DATASET: {dataset}')
        visualize_agc(org_path, dataset)