fromip = "212.237.152.1"  # 2048
totalnum = 2046

fromips = fromip.split('.')

for loop1 in range(1, totalnum + 1):
    print(f"$iplist[{loop1}] = \"{fromips[0]}.{fromips[1]}.{fromips[2]}.{fromips[3]}\";")
    fromips[3] = int(fromips[3]) + 1
    if fromips[3] > 255:
        fromips[3] = 0
        fromips[2] = int(fromips[2]) + 1
