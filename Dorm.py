import random
import math

dorms = ['Zeus', 'Athena', 'Hercules', 'Bacchus', 'Pluto']

prefs = [('Toby', ('Bacchus', 'Hercules')),
		('Steve', ('Zeus', 'Pluto')),
		('Andrea', ('Athena', 'Zeus')),
		('Sarah', ('Zeus', 'Pluto')),
		('Dave', ('Athena', 'Bacchus')),
		('Jeff', ('Hercules', 'Pluto')),
		('Fred', ('Pluto', 'Athena')),
		('Suzie', ('Bacchus', 'Hercules')),
		('Laura', ('Bacchus', 'Hercules')),
		('Neil', ('Hercules', 'Athena'))]

# [(0, 9), (0, 8), (0, 7), ...... (0, 1), (0, 0)]
domain = [(0, (len(dorms) * 2) - i - 1) for i in range(0, len(dorms) * 2)]

def printSolution(vec):
	slots = []

	for i in range(len(dorms)):
		slots += [i , i]

	for i in range(len(vec)):
		x = int(vec[i])
		dorm = dorms[slots[x]]

		print prefs[i][0], dorm
		del slots[x]

def dormCost(vec):
	cost = 0
	slots = [0 , 0 , 1 , 1 , 2 , 2 , 3 , 3 , 4 , 4]

	for i in range(len(vec)):
		x = int(vec[i])
		dorm = dorms[slots[x]]
		pref = prefs[i][1]
		if pref[0] == dorm:
			cost += 0
		elif pref[1] == dorm:
			cost += 1
		else:
			cost += 3

		del slots[x]

	return cost