fromip = "103.94.231.1"
count = 755

fromips = fromip.split('.')

for loop1 in range(int(fromips[3]), 248):
    print(f"$iplist[{count}] = \"{fromips[0]}.{fromips[1]}.{fromips[2]}.{loop1}\";")
    count += 1
