import re
num=input()
result=re.match(r"[0-9-]+", num)
if result:
   print(result.group())
print(re.sub(r"\D","", num))