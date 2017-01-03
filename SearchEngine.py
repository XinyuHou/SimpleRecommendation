import re
import urllib2
import sqlite3 as sqlite
from bs4 import BeautifulSoup
from urlparse import urljoin

# A list of words to ignore
ignoreWords = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it'])

# Clawering part
class Crawler:
	def __init__(self, dbName):
		self.db = sqlite.connect(dbName)

	def __del__(self):
		self.db.close()

	def dbCommit(self):
		self.db.commit()

	#Auxilliary function for getting an entry id and adding it if ti's not present
	def getEntryId(self, table, field, value, createNew = True):
		cur = self.db.execute("select rowid from %s where %s = '%s'" % (table, field, value))

		res = cur.fetchone()

		if res == None:
			cur = self.db.execute("insert into %s (%s) values ('%s')" % (table, field, value))
			return cur.lastrowid
		else:
			return res[0]

	# Index an individual page
	def addToIndex(self, url, soup):
		if self.isIndexed(url):
			return

		print 'Indexing ' + url

		# Get the individual words
		text = self.getTextOnly(soup)
		words = self.separateWords(text)

		# Get the URL id
		urlId = self.getEntryId('UrlList', 'url', url)

		# Link each word to this url
		for i in range(len(words)):
			word = words[i]
			
			if word in ignoreWords: continue

			wordId = self.getEntryId('WordList', 'word', word)
			self.db.execute("insert into WordLocation(urlId, wordId, location) values (%d,%d,%d)" % (urlId, wordId, i))

	# Extract the text from an HTML page (no tags)
	def getTextOnly(self, soup):
		str = soup.string

		if str == None:
			c = soup.contents
			resultText = ''

			for t in c:
				subText = self.getTextOnly(t)
				resultText += subText + '\n'

			return resultText

		else:
			return str.strip()

	# Separate the words by any non-whitespace character
	def separateWords(self, text):
		splitter = re.compile('\\W*')
		return [s.lower() for s in splitter.split(text) if s != '']

	# Return true if this url is already indexed
	def isIndexed(self, url):
		u = self.db.execute("select rowid from UrlList where url = '%s'" % url).fetchone()

		if u != None:
			# Check if it has actually been crawled
			v = self.db.execute("select * from WordLocation where urlId = %d" % u[0]).fetchone()
			if v != None:
				return True


		return False

	# Add a link between two pages
	def addLinkRef(self, urlFrom, urlTo, linkText):
		words = self.separateWords(linkText)
		fromId = self.getEntryId('UrlList', 'url', urlFrom)
		toId = self.getEntryId('UrlList', 'url', urlTo)

		if fromId == toId: return

		cur = self.db.execute("insert into Link(fromId, toId) values (%d, %d)" % (fromId, toId))

		linkId = cur.lastrowid

		for word in words:
			if word in ignoreWords: continue

			wordId = self.getEntryId('WordList', 'word', word)

			self.db.execute("insert into LinkWords(linkId, wordId) values (%d, %d)" % (linkId, wordId))

	# Starting with a list of pages, do a breadth first search to the given depth, indexing pages as we go
	def crawl(self, pages, depth = 2):
		# breadth first search
		for i in range(depth):
			newPages = set()
			for page in pages:
				try:
					c = urllib2.urlopen(page)
				except:
					print "Could not open %s" % page
					continue
				soup = BeautifulSoup(c.read())
				self.addToIndex(page, soup)

				links = soup('a')
				for link in links:
					if ('href' in dict(link.attrs)):
						print 'link hrep: ' + link['href']
						url = urljoin(page, link['href'])
						print 'url: ' + url

						if url.find("'") != -1: continue

						# Remove location part
						url = url.split('#')[0]
						print 'url without location: ' + url

						if url[0:4] == 'http' and not self.isIndexed(url):
							newPages.add(url)

						linkText = self.getTextOnly(link)
						#print 'link text: ' + linkText

						self.addLinkRef(page, url, linkText)
						print '=========='

				self.dbCommit()

			pages = newPages


	# Create the database tables
	def createIndexTables(self):
		self.db.execute('create table UrlList(url)')
		self.db.execute('create table WordList(word)')
		self.db.execute('create table WordLocation(urlId, wordId, location)')
		self.db.execute('create table Link(fromId integer, toId integer)')
		self.db.execute('create table LinkWords(wordId, linkId)')

		self.db.execute('create index WordIndex on WordList(word)')
		self.db.execute('create index UrlIndex on UrlList(url)')
		self.db.execute('create index WordUrlIndex on WordLocation(wordId)')
		self.db.execute('create index UrlToIndex on link(toId)')
		self.db.execute('create index UrlFromIndex on link(fromId)')

		self.dbCommit()

# Querying part
class Searcher:
	def __init__(self, dbName):
		self.db = sqlite.connect(dbName)

	def __del__(self):
		self.db.close()

	def getMatchRows(self, query):
		# Strings to build the query
		fieldList = 'w0.urlId'
		tableList = ''
		clauseList = ''
		wordIds = []

		# Split the words by spaces
		words = query.split(' ')
		tableNumber = 0

		for word in words:
			# Get the word ID
			wordRow = self.db.execute("select rowid from WordList where word = '%s'" % word).fetchone()
			if wordRow != None:
				wordId = wordRow[0]
				wordIds.append(wordId)
				if tableNumber > 0:
					tableList += ','
					clauseList += ' and '
					clauseList += 'w%d.urlId = w%d.urlId and ' % (tableNumber - 1, tableNumber)

				fieldList += ', w%d.location' % tableNumber
				tableList += 'WordLocation w%d' % tableNumber
				clauseList += 'w%d.wordId = %d' % (tableNumber, wordId)
				tableNumber += 1

		# Create the query from the separate parts
		fullQuery = 'select %s from %s where %s' % (fieldList, tableList, clauseList)

		cur = self.db.execute(fullQuery)
		rows = [row for row in cur]

		return rows, wordIds

	def getScoreList(self, rows, wordIds):
		totalScores = dict([(row[0], 0) for row in rows])

		weights = [(1.0, self.frequencyScore(rows)),
				   	(1.0, self.locationScore(rows)),
				   	(1.0, self.distanceScore(rows)),]

		for (weight, scores) in weights:
			for url in totalScores:
				totalScores[url] += weight * scores[url]

		return totalScores

	def getUrlName(self, id):
		return self.db.execute("select url from UrlList where rowid = %d" % id).fetchone()[0]

	def query(self, q):
		rows, wordIds = self.getMatchRows(q)
		scores = self.getScoreList(rows, wordIds)
		rankedScores = sorted([(score, url) for (url, score) in scores.items()], reverse = 1)
		for (score, urlId) in rankedScores[0:10]:
			print '%f\t%s' % (score, self.getUrlName(urlId))

	def normalizeScores(self, scores, smallIsBetter = 0):
		# Avoid division by zero errors
		vSmall = 0.00001

		if smallIsBetter:
			minScore = min(scores.values())
			# 2, 3, 5
			# 1, 0.66, 0.4
			return dict([(u, float(minScore) / max(vSmall, l)) for (u, l) in scores.items()])

		else:
			maxScore = max(scores.values())
			if maxScore == 0:
				maxScore = vSmall
			# 2, 3, 5
			#0.4, 0.6, 1
			return dict([(u, float(c) / maxScore) for (u, c) in scores.items()])

	def frequencyScore(self, rows):
		counts = dict([(row[0], 0) for row in rows])
		for row in rows:
			counts[row[0]] += 1
		return self.normalizeScores(counts)

	def locationScore(self, rows):
		locations = dict([(row[0], 1000000) for row in rows])

		for row in rows:
			locSum = sum(row[1:])
			if locSum < locations[row[0]]:
				locations[row[0]] = locSum

		return self.normalizeScores(locations, smallIsBetter = 1)

	def distanceScore(self, rows):
		# If there is only 1 word, everyone wins
		if len(rows[0]) <= 2:
			return dict([(row[0], 1.0) for row in rows])

		# Initialize the dictionary with large values
		minDistance = dict([(row[0], 1000000) for row in rows])

		for row in rows:
			dist = sum([abs(row[i] - row[i - 1]) for i in range(2, len(row))])
			if dist < minDistance[row[0]]:
				minDistance[row[0]] = dist

		return self.normalizeScores(minDistance, smallIsBetter = 1)

	def inboundLinkScore(self, rows):
		uniqueUrls = set([row[0] for row in rows])
		inboundCount = dict([(u, self.db.execute('select count(*) from Link where toId = %d' % u).fetchone()[0]) for u in uniqueUrls])
		return self.normalizeScores(inboundCount)
