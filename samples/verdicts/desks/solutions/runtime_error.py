# Reads three numbers from one line, but they come on three lines: ValueError.
a, b, c = map(int, input().split())
print((a + 1) // 2 + (b + 1) // 2 + (c + 1) // 2)
