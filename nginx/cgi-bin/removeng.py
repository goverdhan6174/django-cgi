import os
import time

# Get the current date
sec, min, hour, mday, mon, year, wday, yday, isdst = time.localtime(time.time())
year += 1900
mon += 1
curdate = f"{year:04d}{mon:02d}{mday:02d}"

# Directory to search for files
dir = '__data/Result'
dh = os.listdir(dir)

for file in dh:
    # Check if the file name contains 'ng'
    if 'ng' in file.lower():
        # Check if the file name contains the current date
        if curdate in file:
            # print(f"CUR : {file}")
            pass
        else:
            unlink = f"__data/Result/{file}"
            print(unlink, end=' ')
            if os.path.isfile(unlink):
                os.remove(unlink)
                print(" -- deleted")
            else:
                print(" -- file error")
    else:
        # print(f"OK -- {file}")
        pass
