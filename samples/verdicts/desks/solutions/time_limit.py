# Counts desks one by one, but forgets to decrease the pupils: never ends.
pupils = int(input()) + int(input()) + int(input())
desks = 0
while pupils > 0:
    desks += 1
print(desks)
