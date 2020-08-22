import re

def uninitialisedStaticVariable(err, files, history):
	# indicator whether the fix is found or not	
	indicator = 0
	# open and read file to get line that caused problems
	f = open( err.getProblemLines()[1][0], "r")
	
	data = f.readlines()
	f.close()

	addition=''
	#open and read file to detect error fix
	f = open( err.getProblemLines()[0][0], "r")
	data = f.readlines()
	
	if not indicator:
		for i in range(err.getProblemLines()[0][1], len(data)):
			m = re.search('(.*)(([a-zA-Z_-]+))[ ]+.*{',data[i])
			if m:
				break
			m= re.search('(.*)([a-zA-Z_-]+)[ ]+.*;',data[i])
			if m:
				if data[i+1].find('__index__')>=0:
					continue
				if data[i].find('[')>0:
					m = re.search('([ \t]*)([a-zA-Z_-]+)[ ]+([a-zA-Z0-9_-]+)\[(.+)\].*;', data[i])
					if m:
						varType = m.group(2)
						variable = m.group(3)
						expressionData = m.group(4)

						temporaryData = data[i][data[i].find(m.group(3)):]
						temporaryLen = len(re.findall('\[', temporaryData))
						newExpressionData = []
						for k in range(0,temporaryLen):
							newExpressionData.append(\
							temporaryData[temporaryData.find('[')+1:temporaryData.find(']')])	
							temporaryData = temporaryData[temporaryData.find(']')+1:]	

						inl = m.group(1)
						addition = initialiseUsingLoop(varType, variable, temporaryLen, newExpressionData, inl, history)
						err.setBugFix(data[i] + data[i].replace(data[i].strip() , addition))
				else:
					m = re.search('([ \t]*)([a-zA-Z_-]+)[ ]+(.+).*;', data[i])
					if m:
						if data[i][data[i].find(m.group(2))::].find('=')<0:
							varType = m.group(2)
							if initialise(varType)!= 'Invalid':
								addition = data[i].replace(';' , '= ' + initialise(varType) + ';')
								err.setBugFix(addition)

				if addition:
					err.setChangedFile(err.getProblemLines()[0][0])
					err.setChangedLine(i+1)
					err.setBug(data[i])		
					break

		if (addition, err.getChangedLine(), err.getChangedFile()) not in history:
			history.append((addition, err.getChangedLine(), err.getChangedFile()))
			indicator = 1

	f.close()

def uninitialisedDinamicllyAllocatedVariable(err, files, history):

	for file in files:
		f = open( file, "r")
		data = f.readlines()
		f.close()
		lineCausedProblems = ''
		addition=''

		for elem in err.getProblemLines():
			m = re.search('(malloc|calloc|realloc)(.+)', data[elem[1]-1])
			if m:
				lineCausedProblems = data[elem[1] - 1]
				err.setChangedLine(elem[1])
				break
		


		m = re.search('(malloc|calloc|realloc)(.+);', lineCausedProblems)
		if m and not addition:
			expressionData = m.group(2).replace('(', '', 1)[::-1].replace(')', '', 1)[::-1].strip()
			expressionData = re.sub('sizeof[ ]*\([ ]*([a-zA-Z_-]+)[ ]*\)', '1' , expressionData)
			start = lineCausedProblems.find('*')
			end = lineCausedProblems.find('=')
			varType = lineCausedProblems[0:start].strip()
			inl = lineCausedProblems[0:start - len(varType) - 1]
			variable = lineCausedProblems[lineCausedProblems.find('*') + 1 : lineCausedProblems.find('=')]
			
			if initialise(varType)!= 'Invalid':
				if not re.findall('[a-zA-Z]+', expressionData) and int(eval(expressionData)) == 1:
					addition = lineCausedProblems[start:end] + " = " + initialise(varType) + ';'
				else:
					addition = initialiseUsingLoop(varType, variable, 1, [expressionData], inl, history)

		if addition and (addition, err.getChangedLine(), err.getChangedFile()) not in history:
			err.setChangedFile(file)
			history.append((addition, err.getChangedLine(), err.getChangedFile()))		
			# set what should be changed
			err.setBug(lineCausedProblems)
			err.setBugFix(lineCausedProblems + lineCausedProblems.replace(lineCausedProblems.strip() , addition) )
			break
		
		# if statement 
		m = re.search('(malloc|calloc|realloc)(.+)', lineCausedProblems)
		if m and not addition:

			# here we get varType, variable, expressionData and inl
			start = lineCausedProblems.find('sizeof(') + 7
			end = lineCausedProblems[start:].find(')')
			varType = lineCausedProblems[start:][0:end]
			n = re.search('([ \t]*).*\([ ]*(.*)[ ]*=[ ]*(malloc|calloc|realloc)[ ]*\((.*)NULL', lineCausedProblems)
			if n:
				inl = n.group(1)
				variable = n.group(2)
				expressionData = re.sub('sizeof[ ]*\([ ]*([a-zA-Z_-]+)[ ]*\)', '1' , n.group(4))
				if expressionData.find(')')>=0:
					expressionData = expressionData[0:expressionData.find(')')]	
 
			# here we find where to add initialisation code
			indicator = 0
			if m.group(2).find('!=')>=0:
				addition = '\t' + initialiseUsingLoop(varType, variable, 1, [expressionData], inl + '\t', history)
			elif m.group(2).find('==')>=0:
				addition = lineCausedProblems.replace('==' , '!=')
				addition += inl + '\t'
				addition += initialiseUsingLoop(varType, variable, 1, [expressionData], inl + '\t' , history)
				addition += inl + '}\n'
				addition = lineCausedProblems.replace(lineCausedProblems, addition) + \
					   lineCausedProblems.replace(lineCausedProblems.lstrip() , 'else ') + \
					   'if (' + variable + '==NULL)'
				if lineCausedProblems.find('{')>=0:
					addition += '{\n'
				else:
					addition += '\n'

				# ZAMENI DA BUDE ELSE IF P[I] == NULL 
				indicator = 1;
			
			if addition and (addition, err.getChangedLine(), err.getChangedFile()) not in history:
				err.setChangedFile(file)
				history.append((addition, err.getChangedLine(), err.getChangedFile()))		
				# set what should be changed
				err.setBug(lineCausedProblems)
				if indicator:
					err.setBugFix(addition)
				else:
					err.setBugFix(lineCausedProblems + lineCausedProblems.replace(lineCausedProblems.strip() , addition))
				break		


def initialiseUsingLoop(varType, variable, length, expressionData, inl, history):
	count = 0
	addition = ''
	index = []
	
	for line in history:
		searchLine = line[0]
		while re.findall('int __index__', searchLine):
			
			searchLine = searchLine[searchLine.find('int __index__')+len('int __index__'):]
			count += 1

	for i in range(0,length):
		if count:
			addition += 'int __index' + str(count+1) + '__;\n' + inl
			index.append( '__index' + str(count+1) + '__')
			count +=1
		else:
			addition += 'int '+ '__index__' +';\n' + inl
			index.append( '__index__')
			count += 1
		
	if re.findall('[a-zA-Z]+', inl):
		inl = ''

	addition = addition[0:addition.rfind(inl)]

	for i in range(0,length):
		if not re.findall('[a-zA-Z]+', expressionData[i]):
			expressionData[i] = str(int(eval(expressionData[i])))

		for j in range(0,i+1):
			addition += inl

		addition += 'for( '+ index[i] +' = 0; ' + index[i] +' < ' + expressionData[i] + '; ' \
			+ index[i] + ' ++)\n'

	for i in range(0,length+1):
		addition += inl
	
	arrayIndex = ''
	for i in range(0,length):
		arrayIndex += '[' + index[i] + ']'

	addition +=  variable.strip() + arrayIndex + ' = ' + initialise(varType) + ';\n'

	return addition	


def initialise(varType):
	initialisator = {
		'int': '0',
		'double': '0',
		'float': '0',
		'boolean': 'False',
		'char': '\'\\0\''
	    }
	
	if varType in initialisator:
		return initialisator[varType]
	else:
		return 'Invalid'

