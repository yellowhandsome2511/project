words=input().split()
word=input()
a=words.count(word)
print(a)
for i in range(a):
    words.remove(word)
print(" ".join(words))