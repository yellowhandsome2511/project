str_1=sorted(input().split())
dict_1={}
for i in str_1:
    if i in dict_1:
        dict_1[i]+=1
    else:
        dict_1[i]=1
for i in dict_1:
    print(i, dict_1[i])


        