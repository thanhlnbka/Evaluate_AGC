from database.db_models import PersonInformation, MongoConnectionManager
import pandas as pd
import os
from tqdm import tqdm
import sys


connection_string = "mongodb://uagc:pagc@192.168.2.207:27018/agcdb"
MongoConnectionManager.connect_mongoengine(connection_string)

def save_csv(camid): 
    personinfo = PersonInformation.get_list_person_information(camid)
    data = []
    for person in tqdm(personinfo): 
        new_data = {"camid": camid, "pid": person["pid"], "age": person["age"], "gender": person["gender"]}
        data.append(new_data)

    df_data = pd.DataFrame(data)
    df_data.to_csv(f"data_preds/{camid}.csv", index=False)

os.makedirs("data_preds", exist_ok=True)



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
# #lan4
# res = {
#     i: (1280,720) for i in range(2090,2120) if i != 2112
# }

# #lan5
res.update({
    i: (1280,720) for i in range(2120,2158)
})


# MBDA case
res.update({i:(1280,720) for i in range(3000,30000)})


if __name__== "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_cam.py <comma-separated list of numbers>")

    numbers = sys.argv[1].split(',')

    numbers = [int(num) for num in numbers]
    for i in numbers:
        print(f"Get data for cam{i}")
        save_csv(f"cam{i}")
