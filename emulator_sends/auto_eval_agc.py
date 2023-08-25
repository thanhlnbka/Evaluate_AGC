import os
import shutil
import configparser
import random
from glob import glob
import time
import subprocess
import datetime
import json


class CaseSensitiveConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.optionxform = str  # Preserve case sensitivity

def update_config(target_file, section="input", key="camera_list", value=""):
    config = CaseSensitiveConfigParser(comment_prefixes='/', allow_no_value=True, interpolation=configparser.ExtendedInterpolation(), default_section='DEFAULT')
    config.read(target_file, encoding='utf-8')
    config.set(section, key, value)
    with open(target_file, "w") as config_file:
        config.write(config_file, space_around_delimiters=True)


# def wait_agc_to_run_success(keyword, interval=10):  
#     log_file = ""
#     while(True):
#         log_files = os.listdir("/workspace/build/logs/agc")
#         print("Log files:",  log_files )
#         if len(log_files) > 0:
#             log_file = log_files[0]
#         if log_file == "":
#             continue
#         log_path = os.path.join("/workspace/build/logs/agc", log_file)
#         if os.path.exists(log_path):
#             with open(log_path, "r") as file:
#                 for line in file:
#                     # print(line)
#                     if keyword in line:
#                         return log_path
#         time.sleep(interval)



def wait_agc_to_run_success(keyword, interval=10):  
    while(True):
        log_path = "/workspace/build/logs/tools/agc_app.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as file:
                for line in file:
                    # print(line)
                    if keyword in line:
                        return log_path
        print("wait agc system run success ... ")
        time.sleep(interval)



def wait_evaluation_to_finish(file_path, duration, interval=4):
    # get modification time
    while(True):
        if time.time() - os.path.getmtime(file_path) > duration:
            return
        time.sleep(interval)



def main():
    # name_datasets_eval = [ "MBDA_case", "WIN_HH", "Exhibition"]
    # name_datasets_eval = ["test1","test2"]
    # name_datasets_eval = ["Exhibition"]
    # name_datasets_eval = [ "MBDA_case"]
    name_datasets_eval = ["WIN_HH"]
    
    for dataset_eval in name_datasets_eval:
        print(f"Processing dataset {dataset_eval}")

        output_folder = f"/workspace/src/benchmark_AGC/{dataset_eval}_output"
        os.makedirs(output_folder, exist_ok=True)

        path_csv_sdk_send = "/workspace/src/benchmark_AGC/send_sdk"
        path_log_filters = "/workspace/build/logfilter"
        path_agc_outputs = "/workspace/build/data/agc_outputs"
        path_data_preds = "/workspace/src/benchmark_AGC/data_preds"

        #CLEAN DATA ALL
        os.system(f"rm -rf {path_csv_sdk_send}")
        os.system(f"rm -rf {path_log_filters}")
        os.system(f"rm -rf {path_agc_outputs}")
        os.system(f"rm -rf {path_data_preds}")

        source_root_dir = f"/workspace/src/eval_datasets/{dataset_eval}"
        images_dir  = os.path.join(source_root_dir, "images")
        target_root_dir = "/workspace/build"
        
        list_cameras = os.listdir(images_dir)


        not_running_cameras = [cam for cam in list_cameras]


        path_log_auto_eval = "/workspace/src/benchmark_AGC/logs_auto_eval"
        os.makedirs(path_log_auto_eval, exist_ok=True)
        
        
        while not_running_cameras:
            os.system(f"rm -rf {path_log_auto_eval}/*")
            n = 10 
            #Run with 10cam for one step eval
            cameras_to_process = [not_running_cameras.pop(0) for _ in range(n) if len(not_running_cameras)>0]
            camlist_str = ",".join(cameras_to_process).replace("cam","")

            print("COPY FOLDER ....")
            os.system(f"rm -rf {target_root_dir}/logs/images/*")
            os.system(f"rm -rf {target_root_dir}/data/csvs/*")
            os.system(f"rm -rf {target_root_dir}/configs/cameras/*")
            
            
            for camera in cameras_to_process:
                print(f"copy file,folder for {camera}")
                # Copy folders
                try:
                    shutil.copytree(os.path.join(source_root_dir, "images", camera), f"{target_root_dir}/logs/images/{camera}")
                    shutil.copytree(os.path.join(source_root_dir, "csvs", camera), f"{target_root_dir}/data/csvs/{camera}")
                    shutil.copyfile(os.path.join(source_root_dir, "cameras", f"{camera}.ini"), f"{target_root_dir}/configs/cameras/{camera}.ini")
                except FileNotFoundError as e:
                    numbers = camlist_str.split(',')  
                    numbers = [num for num in numbers if f"cam{num}" != camera]
                    camlist_str = ','.join(numbers) 
                    print(f"Error copying files for {camera}: {e}")

            print("UPDATE CONFIG.ini ....")
            update_config(os.path.join("/workspace/build/configs", "config.ini"), "input", "camera_list", camlist_str)
            
            print("RUN AGC ...")
            os.system("cd /workspace/build && asdk make_config")
            time.sleep(2)
            os.system("cd /workspace/build && asdk make_config")
            time.sleep(2)

            #clean logs agc
            os.system("rm -rf /workspace/build/logs/tools/agc_app.log")

            # Run sub main.py for AGC
            os.system("cd /workspace/build && nohup python3 service/agc/AGC_SingleImage/main.py  &")
            time.sleep(2)
            
            #check status sub agc start done
            log_path_ = wait_agc_to_run_success("All AGC model worker are loaded!!!!", 10)
            # log_path_ = wait_agc_to_run_success("Started all cameras successfully!!!", 10)
            time.sleep(2)
            
            print("Sending data ...")
            #send data to agc
            os.system(f"cd /workspace/src/benchmark_AGC && nohup python3 send_agc.py {camlist_str}> {path_log_auto_eval}/send_agc.log 2>&1 &")

            time.sleep(2)
            print("Aggregate vote agc ...")
        
            os.system(f"cd /workspace/build && nohup python3 shell.py final_vote_agc > {path_log_auto_eval}/final_vote_agc.log 2>&1 &")

            # Wait for evaluation to finish, check interval time = 10s
            wait_evaluation_to_finish(log_path_, 30)
            print("Aggregate done ! => stop all and get data ...")
            #Run cleanup commands and get data from db
            os.system("asdk stop all")
            os.system(f"cd /workspace/src/benchmark_AGC && python3 get_vote_agc_from_db.py {camlist_str}")
            time.sleep(2)

        #GET DATA ALL
        dst_csv_sdk_send = os.path.join(output_folder, "send_sdk")
        dst_log_filtes = os.path.join(output_folder,"logfilter")
        dst_agc_outputs = os.path.join(output_folder, "agc_outputs")
        dst_data_preds = os.path.join(output_folder, "data_preds")

        shutil.copytree(path_csv_sdk_send, dst_csv_sdk_send)
        shutil.copytree(path_log_filters, dst_log_filtes)
        shutil.copytree(path_agc_outputs, dst_agc_outputs)
        shutil.copytree(path_data_preds, dst_data_preds)

        

        print(f"eval with dataset {dataset_eval} done !")

if __name__ == "__main__":
    main()