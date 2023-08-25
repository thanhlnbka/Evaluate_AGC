import os
import pandas as pd

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
            age_rd = round(age)
        except:
            age_rd = age
        if age_rd >= value[0] and age_rd <= value[1]:
            return key
    return None

def load_data(file_path):
    try:    
        data = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        # read lines
        # lines = None
        # with open(file_path, 'r') as f:
        #     lines = f.readlines()
        # print(f"File {file_path}: {lines} is empty.")
        data = None
    return data

def calculate_accuracy(pred_data, gt_data):
    merged_data = pd.merge(pred_data, gt_data, on=['camid', 'pid'], suffixes=('_pred', '_gt'))
    common_columns = set(merged_data.columns).intersection(['age_pred', 'gender_pred', 'age_gt', 'gender_gt'])
    total_count = len(merged_data)
    merged_data.to_csv("debug.csv", index=False)
    # accuracy by each sample per camid, declare dataframe to store detail accuracy with colunms: camid, age_group, correct_samples, total_samples
    detail_accuracy = [] #pd.DataFrame(columns=['camid', 'age_group', 'correct_samples', 'total_samples'])
    for _, row in merged_data.iterrows():    
        correct_count = 0
        correct_age = 0
        correct_gender = 0
        #if row['age_pred'] == row['age_gt'] and row['gender_pred'] == row['gender_gt']:        
        gt_age_group = get_age_group(row['age_gt'])
        pred_age_group = get_age_group(row['age_pred'])
        pred_gender = 'M'
        if (row['gender_pred'] == 0):
            pred_gender = 'F'
        if (gt_age_group == pred_age_group):
            correct_age = 1
        if (pred_gender == row['gender_gt']):
            correct_gender = 1
        if (gt_age_group == pred_age_group) and (pred_gender == row['gender_gt']): # and gt_age_group is not None:
            correct_count = 1

        # update detail accuracy
        # detail_accuracy = detail_accuracy.append({'camid': row['camid'], 'age_group': gt_age_group, 'correct_samples': correct_count, 'total_samples': total_count}, ignore_index=True)
        detail_accuracy.append([row['camid'], row['pid'], row['gender_gt'], pred_gender, row['age_gt'], row['age_pred'], gt_age_group, pred_age_group, correct_age, correct_gender, correct_count])
        # print(gt_age_group, row['age_gt'], pred_age_group, row['age_pred'], pred_gender, row['gender_gt'],  correct_count, total_count)
    
    # accuracy = correct_count / total_count * 100
    return 0, detail_accuracy


def main():    
    root_path = os.getcwd()
    subfolders = ["WIN_HH", "Exhibition"]
    # print(subfolders)
    for folder in subfolders:
        print("Processing folder ", folder)
        pwd = os.path.join(root_path, folder)
        result_path = os.path.join(root_path , 'results', folder)
        if not os.path.exists(result_path):
            os.makedirs(result_path)
        # result_path = os.path.join(os.path.dirname(pwd), 'results')
        # dataset_name = os.path.basename(pwd)
        pred_path = os.path.join(pwd, 'data_preds')
        gt_path = os.path.join(pwd, 'gt_sdk')    
        _pred_files = [f for f in os.listdir(pred_path) if os.path.isfile(os.path.join(pred_path, f))]
        _gt_files = [f for f in os.listdir(gt_path) if os.path.isfile(os.path.join(gt_path, f))]
        print(_gt_files[0])
        gt_files = [f for f in _gt_files if f.split("_")[0] +".csv" in _pred_files]
        pred_files = [f for f in _pred_files if f.split(".")[0] +"_sdk.csv" in gt_files]
        print(gt_files[0])
        print(pred_files[0])
        print(len(gt_files))
        print(len(pred_files))
        assert len(pred_files) == len(gt_files), "Number of files in pred_path and gt_path must be equal."
        samples = len(pred_files)

        # export accuracy to csv in format: camid, accuracy, age_group, correct_samples, total_samples
        accuracy_list = []
        detail_accuracy_list = [] #pd.DataFrame(columns=['camid', 'age_group', 'correct_samples', 'total_samples'])
        for file in pred_files:
            # get file name
            file_name = file.split('.')[0]
            i = file_name.split('.')[0].split('cam')[1]
            camid = f'cam{i}'
            pred_file_path = os.path.join(pred_path, f'cam{i}.csv')
            gt_file_path = os.path.join(gt_path, f'cam{i}_sdk.csv')
            # print(pred_file_path)
            # print(gt_file_path)
            assert os.path.isfile(pred_file_path), f"File {pred_file_path} does not exist."
            assert os.path.isfile(gt_file_path), f"File {gt_file_path} does not exist."
            pred_data = load_data(pred_file_path)
            gt_data = load_data(gt_file_path)
            

            detail_acc = [[camid, -1, -1, -1, -1, -1, -1, -1, -1,-1,-1]]
            print(file_name)
            if pred_data is not None:
                _, detail_acc = calculate_accuracy(pred_data, gt_data)
            detail_accuracy_list += detail_acc
        df_detail = pd.DataFrame(detail_accuracy_list, columns=['camid', 'pid', 'gender_gt', 'gender_pred', 'age_gt', 'age_pred', 'age_group_gt', 'age_group_pred', 'correct_age', 'correct_gender', 'correct']).sort_values(by=['camid']).reset_index(drop=True)
        df_detail.to_csv(os.path.join(result_path, 'raw_result.csv'), index=False)

if __name__ == "__main__":
    main()