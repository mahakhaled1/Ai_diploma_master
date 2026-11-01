import os
import random

def thanos_project():

    folder = "MyFolder"

    os.makedirs(folder, exist_ok=True)

    for i in range(10):
        open(os.path.join(folder, f"file{i}.txt"), "w").close()

    files = os.listdir(folder)
    print("Number of files:", len(files))

    delete_files = random.sample(files, len(files) // 2)

    for file in delete_files:
        os.remove(os.path.join(folder, file))

    files = os.listdir(folder)
    print("Number of files after delete:", len(files))
    print(files)

thanos_project()