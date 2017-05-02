from random import random, randint
import math

def winePrice(rating, age):
	peak_age = rating - 50
	price = rating / 2
	if age > peak_age:
		price = price * (5 - (age - peak_age))
	else:
		price = price * (5 * ((age + 1) / peak_age))

	if price < 0:
		price = 0

	return price

def wineSet1():
	rows = []

	for i in range(300):
		rating = random() * 50 + 50
		age = random() * 50

		price = winePrice(rating, age)

		price *= (random() * 0.4 + 0.8)

		rows.append({'input':(rating, age),
			'result': price})

	return rows

def euclidean(v1, v2):
	d = 0.0
	for i in range(len(v1)):
		d += (v1[i] - v2[i]) ** 2

	return math.sqrt(d)

def getDistances(data, vec1):
	distanceList = []

	for i in range(len(data)):
		vec2 = data[i]['input']
		distanceList.append((euclidean(vec1, vec2), i))

	distanceList.sort()
	return distanceList

def KNN(data, vec1, k = 5):
	dList = getDistances(data, vec1)
	avg = 0.0

	for i in range(k):
		idx = dList[i][1]
		avg += data[idx]['result']

	avg = avg / k
	return avg