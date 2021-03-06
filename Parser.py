import threading


class Parser(threading.Thread):

	NOTHING = 0
	SEMICOLON = 1

	ADD = ['', ';']

	def __init__(self, lines, ordering, callback):
		self.lines = lines
		self.ordering = ordering
		self.result = None
		self.callback = callback
		super().__init__()

	def run(self):
		parsed = self.parse()
		formatted = None
		try:
			formatted = self.format(parsed)
		except:
			pass
		self.callback(formatted)

	def addResult(self, result, lineLengths, lastLine, end, key, value=None, originalValue=None):
		'''
		Format the result with the line and content.
		'''
		value = Parser.NOTHING if value is None else value
		valueLength = 0 if type(value) is not str else len(value)
		originalValueLength = 0 if originalValue is None else len(originalValue)

		start = end - len(key) - valueLength - originalValueLength + 1

		lastIndex = len(lineLengths) - 1
		lineNumber = lastLine
		endLineNumber = lastLine

		# Get the original lineNumber (index starting from 0)
		while lastIndex > endLineNumber and lineLengths[endLineNumber] <= end:
			if lineLengths[lineNumber] <= start:
				lineNumber += 1
				endLineNumber += 1
			else:
				endLineNumber += 1

		result[key] = [lineNumber, endLineNumber, value]
		return (result, lineNumber,)

	def parse(self, style=None):
		'''
		Convert an SCSS string to a dict.
		'''
		if style is None:
			style = self.lines

		result = {}
		part = ''
		previousPart = ''

		# Keep track whether the current string in the loop is considered a value or a key in the dict
		isKey = True
		# Whether to reset the current part/string
		reset = False
		# A depth is set when opening braces occurred, it will then get the string between those braces and parse recursively parse those
		depth = 0
		# The line the previous part was originally
		lastLine = 0

		# A single line comment is being parsed
		lineComment = False
		# A multi line comment line is being parsed
		multilineComment = False
		# This indicates the end of a multi line comment
		endlineComment = False

		# A nesting with a double colon is being parsed
		doubleColon = False
		# A nesting with a colon is being parsed
		isNesting = False

		lineLengths = []
		lines = style.split('\n')

		for key, line in enumerate(lines):
			lineLengths.append(len(line) + 1 if key == 0 else len(line) + lineLengths[key - 1] + 1)

		# Don't count the last \n
		lineLengths[len(lineLengths) - 1] -= 1
		length = lineLengths[len(lineLengths) - 1]

		for index, char in enumerate(style):
			if depth == 0:
				# Some kind of comment is being parsed
				if lineComment or multilineComment or endlineComment:
					# It's the end of a single line comment
					if lineComment and char == '\n':
						(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, part)
						lineComment = False
						reset = True
					elif endlineComment:
						endlineComment = False
						part += char
						(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, part)
						reset = True
					# A multi line comment is being parsed and the current char might indicate it'll end
					elif multilineComment and char == '*' and style[index + 1] == '/':
						endlineComment = True
						multilineComment = False
				elif char == '/':
					if length > index + 1:
						nextChar = style[index + 1]
						# If the next char is '/' it means a single line comment is starting (//)
						if nextChar == '/':
							lineComment = True
						# If the next char is '*' it means a multi line comment is starting (/*)
						elif nextChar == '*':
							multilineComment = True
				# If an attribute is being set (e.g: 'height:') it must be considered as so
				# if in SCSS &:hover is being used, it must be considered as one key
				elif char == ':' and index > 0 and style[index - 1] != '&' and not doubleColon:
					if style[index + 1] == ':' or style[index - 1] == ':':
						doubleColon = True
					else:
						tempChar = ''
						for t in range(index, len(style), 1):
							tempChar = style[t]
							if tempChar == '{':
								isNesting = True
								break
							if tempChar in [';', '\'', '"']:
								break

						if not isNesting:
							if isKey:
								isKey = False
								(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, part)
							reset = True
				elif char == ';':
					# @imports, @extends, etc. are keys while attribute values are dict values
					if isKey:
						(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, part, Parser.SEMICOLON)
					else:
						(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, previousPart, part)
						isKey = True
					reset = True
				elif char == '{':
					isNesting = False
					doubleColon = False
					depth += 1
					part = part.strip()
					(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, part)
					reset = True
			# It's already adding the string for a recursive result, but we need to keep track where the current nesting ends
			elif char == '{':
				depth += 1
			elif char == '}':
				depth -= 1
				# If the depth reaches 0 again, then it means that this closing brace ends this nesting and we want to parse the string between the braces
				if depth == 0:
					nestedStyle = self.parse(part)
					(result, lastLine,) = self.addResult(result, lineLengths, lastLine, index, previousPart, nestedStyle, part)
					reset = True

			if reset:
				reset = False
				previousPart = part
				part = ''
			# Strip whitespace if it should not be preserved (comments and nestings need to be preserved)
			elif (multilineComment or (depth > 0 and style[index - 1] != '{') or char != '\n')\
				and (part != '' or char != ' ')\
				and (part != '' or char != '\t'):
				part += char

		return result

	def format(self, parsed, depth=0):
		'''
		Format the completely parsed list to a string.
		'''
		# self.order() orders recursively so if the depth > 0, the parsed data is already ordered
		ordered = self.order(parsed) if depth == 0 else parsed

		result = ''
		indent = ''

		for d in range(depth):
			indent += '\t'
		newLine = '\n' + indent

		for i, line in enumerate(ordered):
			attributeValue = line[1]
			length = len(line)
			lastValue = line[length - 1]
			hasComment = type(lastValue) is list and len(lastValue) > 2
			if i > 0:
				previousLine = ordered[i - 1]
				previousLength = len(previousLine)
				lastPreviousValue = previousLine[previousLength - 1]

				previousHadComment = type(lastPreviousValue) is list and len(lastPreviousValue) > 2
				previousIsSass = previousLength <= (5 if previousHadComment else 4)

				previousIsAttribute = previousLength > 4 and len(previousLine[4]) == 2
				currentIsAttribute = length > 4 and len(line[4]) == 2

				currentIsNesting = type(line[1]) is list
				previousIsNesting = type(previousLine[1]) is list

				# '\n' after @' or '$'
				# '\n' before beginning a new attribute type
				# '\n' before first nesting
				if previousIsSass and currentIsAttribute\
					or previousIsAttribute and currentIsAttribute and currentIsAttribute and previousLine[4][0] < line[4][0]\
					or currentIsNesting and not previousIsNesting:
					result += '\n'
			if hasComment:
				comment = lastValue
				result += newLine + (newLine.join(comment[0]) if type(comment[0]) is list else comment[0])
			result += newLine + line[0]
			if attributeValue is not None:
				if type(attributeValue) is str:
					result += ': ' + attributeValue + ';'
				elif type(attributeValue) is list:
					result += ' {\n' + self.format(attributeValue, depth + 1) + newLine + '}'
					result += '\n' if i != len(ordered) - 1 else ''
				else:
					result += Parser.ADD[attributeValue]
		return result[1:]  # Strip the first '\n'

	def order(self, parsed):
		'''
		Order the dictionary:
			- Deeper nestings are kept in the same order
			- The current attributes are moved towards the top
		'''
		nestings = []
		sass = []
		attributes = []
		comments = []

		for key, value in parsed.items():
			lineNumber = value[0]
			endLineNumber = value[1]
			content = self.order(value[2]) if type(value[2]) is dict else value[2]
			line = [key, content, lineNumber, endLineNumber]
			# If the content is a string, it's an attribute
			if type(content) is str:
				# We want to get the importance of attributes and later sort them based on those
				if line[0][0] == '$':
					sass.append(line)
				else:
					for orderNumber, order in enumerate(self.ordering):
						try:
							index = order.index(key)
							line.append([orderNumber, index])
							break
						except:
							pass
					else:
						line.append([len(self.ordering), 0])
					attributes.append(line)
			else:
				if len(line[0]) > 1 and line[0][0] == '/' and (line[0][1] == '/' or line[0][1] == '*'):
					# It's a comment, we want to link it to another comment, attribute, nesting or sass
					comments.append(line)
				else:
					# It's not an attribute, we want to keep the original order -> order on line number.
					selectedList = sass if line[0][0] == '@' else nestings
					for i, l in enumerate(selectedList):
						if l[2] >= lineNumber:
							selectedList.insert(i, line)
							break
					else:
						selectedList.append(line)

		# sorted() sorts the attributes based on their importance (index and orderNumber)
		ordered = sass + sorted(sorted(attributes, key=lambda x: x[2]), key=lambda x: x[4]) + nestings
		self.linkComments(comments, ordered)

		return ordered

	def linkComments(self, comments, ordered):
		'''
		Link comments to their respective attribute, other comment or other (s)css object.
		'''
		comments = sorted(comments, key=lambda x: x[2])

		for c in range(len(comments) - 1, -1, -1):
			comment = comments[c]
			if c > 0:
				previousComment = comments[c - 1]

				previousEnd = previousComment[3]
				currentStart = comment[2]

				# The current comment is linked to the next one
				if currentStart - 1 <= previousEnd <= currentStart:
					addComment = comments.pop(c)
					previousComment[0] = [previousComment[0]] if type(previousComment[0]) is str else previousComment[0]
					if currentStart - 1 == previousEnd:
						previousComment[0].append(addComment[0])
					else:
						previousComment[0].append(previousComment[0].pop() + addComment[0])
					previousComment[3] = addComment[3]
					continue
			comments[c] = comment

		for o in range(len(ordered) - 1, -1, -1):
			order = ordered[o]
			if o > 0:
				orderStart = order[2]
				for c in range(len(comments) - 1, -1, -1):
					comment = comments[c]
					commentEnd = comment[3]
					if orderStart - 1 <= commentEnd <= orderStart:
						comment = comments.pop(c)
						order.append(comment)
						break
