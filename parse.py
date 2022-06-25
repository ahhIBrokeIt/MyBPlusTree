####
# string parser/interpreter
####

from collections import deque
import math

commandList = ['GET', 'PUT', 'DELETE', 'HELP', 'VISUAL', 'EXIT', 'INFO']
typeList = ['NODE', 'EDGE', 'PATH']
conditionList = ['WHERE']
symbolList = {' AND ': ' ⋀ ',
              ' OR ': ' ⋁ ',
              ' NOT ': ' ⌐ ',
              '<=': '≤',
              '>=': '≥',
              ' TO ': ' → '}
logicList = ['⋀', '⋁']
cmpList = ['=', '<', '>', '≤', '≥']
GraphAttrs = {'node': [('degree', 'Int', -1),
                       ('adjacent', 'Bool', -4)],
              'edge': [('weight', 'Int', -1)]}
keywords = commandList + typeList + conditionList + list(symbolList.keys())
opLevel = {'⋀': 1, '⋁': 1, '+': 1, '-': 1, '*': 2, '/': 2}


def nodeDegree(key, edgeList, attrs):
    degree = 0
    for edge in edgeList:
        LinkFromKey = getFieldValue(edge[0], getFieldPos(
            'edge', 'LinkFrom', attrs)[0], edgeList)
        if int(LinkFromKey) == key:
            degree += 1
    return degree


def isInt(strInt):
    """boolean check if string can be an integer"""
    try:
        int(strInt)
        return True
    except ValueError:
        return False


def IDvalue(unknownValue, node, edge, attrs):

    # determine if unknown is obj.attr
    value = None
    if '.' in unknownValue and unknownValue[0] != '"':
        splitter = unknownValue.split('.')
        if len(splitter) == 2:
            left = (splitter[0], splitter[1])
        else:
            error = "Query error: unable to parse object '" + unknownValue + "'"
            return (None, error)

        # identify obj from tables
        if left[0].lower() not in attrs.keys():
            error = "Query error: object '" + left[0] + "' not recognized."
            return (None, error)

        entry = None
        if left[0].upper() == 'NODE':
            entry = node
        if left[0].upper() == 'EDGE':
            entry = edge

        # if you made it this far, the object is known
        value, found = None, False
        valpos = 0
        for att in attrs[left[0].lower()]:
            if att[0] == left[1]:
                found = True
                objType = att[1]
                break
            valpos += 1
        if found == False:
            error = "Query error: object does not have attribute '" + \
                left[1] + "'"
            return (None, error)

        if valpos >= 1:
            value = entry[1][valpos - 1]
        else:
            value = entry[0]
        value = (objType, value)

    else:  # huh ... must be a "string" or int
        if unknownValue[0] == '"':
            if unknownValue[-1] != '"':
                error = "Query error: object string '" + unknownValue + "' does not end."
                return (None, error)
            value = ("V20", unknownValue[1:-1])
        elif isInt(unknownValue):
            value = ("Int", int(unknownValue))

    if value == None:
        error = "Query error: unable to assign value to '" + unknownValue + "'"
        return (None, error)

    return (value, True)


def WhatIsTheTruth(node, edge, attrs, statement):
    """Determine the truth value of statement"""

    # I've been here before ...
    if statement[0] in [True, False]:
        return statement

    # # handle negation
    negate = False
    negpos = statement.find('⌐')
    if negpos != -1:
        if negpos == 0:
            statement = statement[1:]
            negate = True
        else:
            error = "Query error: negation not at beginning of statement '" + statement + "'"
            return (None, error)

    op = None
    for cmp in cmpList:
        splitter = statement.split(cmp)
        if len(splitter) == 2:
            op = cmp
            break
    if op == None:
        error = "Query error: unable to parse condition '" + statement + "'"
        return (None, error)

    # main parse operands from comparison
    leftop, rightop = statement.split(op)

    # check for missing parts
    if leftop == '':
        return (None, "Query error: left side missing from statement '" + statement + "'")
    if rightop == '':
        return (None, "Query error: right side missing from statement '" + statement + "'")

    # identify the value of each operand
    leftv = IDvalue(leftop, node, edge, attrs)
    rightv = IDvalue(rightop, node, edge, attrs)

    if leftv[0] == None:
        return (None, leftv[1])
    if rightv[0] == None:
        return (None, rightv[1])
    if leftv[0][0] != rightv[0][0]:
        error = "Query error: type mismatch between '" + leftop + \
            "'=(" + leftv[0][0] + ") and '" + \
                rightop + "'=(" + rightv[0][0] + ")."
        return (None, error)

    left = leftv[0][1]
    right = rightv[0][1]

    # left and right sides analyzed --> comparison can be made.
    result = False
    if op == '=' and left == right:
        result = True
    elif op == '<' and left < right:
        result = True
    elif op == '>' and left > right:
        result = True
    elif op == '≤' and left <= right:
        result = True
    elif op == '≥' and left >= right:
        result = True
    if negate == True:
        result = not result

    # print(":::",left, op,right," ==>",result)
    # print(leftv,"  -- ",rightv, " ->> ",result)
    return (result, None)


def InFix2Postfix(myInfix, opsList):
    """Convert infix notation to postfix notation"""
    # 1. initialize stack to hold operation symbols and parenthesis
    poststr = []
    pos = 0
    postStack = deque()

    while pos < len(myInfix):
        if myInfix[pos] == '(':   # the next input is a left parenthesis
            postStack.append('(')
        elif myInfix[pos] not in opsList + [')']:  # handle an operand
            nCnt = 0
            while pos + nCnt < len(myInfix) and myInfix[pos + nCnt] not in opsList + [')']:
                nCnt += 1
            poststr.append(myInfix[pos:pos + nCnt])
            pos += nCnt - 1

        elif myInfix[pos] in opsList:  # handle an operator
            while len(postStack) > 0 and postStack[-1] != '(' and opLevel[postStack[-1]] >= opLevel[myInfix[pos]]:
                poststr.append(postStack.pop())

            postStack.append(myInfix[pos])

        else:
            poststr.append(postStack.pop())
            while postStack[-1] != '(':  # stack's top is not a left parenthesis
                poststr.append(postStack.pop())
            postStack.pop()  # pop and discard the last left parenthesis

        pos += 1

    while len(postStack) > 0:
        poststr.append(postStack[-1])
        postStack.pop()

    return poststr


def EvalPostfix(node, edge, attrs, postFixEquation, opsList):
    """Evaluate postfix notation, return True/False/(None,error)"""
    bools = deque()
    ans = True
    pos = 0

    while pos < len(postFixEquation):

        if postFixEquation[pos] not in opsList:  # input is a statement
            # Read the next input and push it onto the stack
            bools.append(postFixEquation[pos])
        else:
            # Read the next character, which is an operator symbol
            op = postFixEquation[pos]

            # Use top and pop to get the two numbers off the top of the stack
            cond1 = bools.pop()
            cond2 = bools.pop()

            cond1Value = WhatIsTheTruth(node, edge, attrs, cond1)
            cond2Value = WhatIsTheTruth(node, edge, attrs, cond2)
            if cond1Value[0] == None:
                return cond1Value
            if cond2Value[0] == None:
                return cond2Value
            if op == '⋀':
                ans = cond1Value[0] and cond2Value[0]
            if op == '⋁':
                ans = cond1Value[0] or cond2Value[0]
            bools.append((ans, None))

        pos += 1

    if len(bools) > 0:  # just in case the question is one statement
        cond1Value = WhatIsTheTruth(node, edge, attrs, bools[-1])
        if cond1Value[0] == None:
            return cond1Value
        ans = cond1Value[0]

    return ans


def FindMatch(type, nodeList, edgeList, cond, attrs):

    # if node or edge list is empty, create dummy entry for the for loops
    if nodeList == []:
        nodeList = [(math.inf, [0 for _ in range(len(attrs['node']))])]
    if edgeList == []:
        edgeList = [(math.inf, [0 for _ in range(len(attrs['edge']))])]

    type = type.lower()
    foundEntries = []

    for node in nodeList:
        for edge in edgeList:

            entryCondition = False
            if cond == True:
                entryCondition == True
            else:
                entryCondition = EvalPostfix(
                    node, edge, attrs, cond, logicList)

            if cond == True or entryCondition == True:
                if type == 'node':
                    foundEntries.append(node)
                elif type == 'edge':
                    foundEntries.append(edge)
            elif entryCondition not in [True, False]:
                return entryCondition

    i = 0
    while i < len(foundEntries):
        if foundEntries[0][0] == math.inf:
            foundEntries.pop(i)
            i = -1
        i += 1

    return foundEntries


def findNode(cond, nodeList, attrs):

    foundEntries = (
        None, "Query error: no node found with condition '" + cond[0]+"'.")

    for symbol in cmpList:
        parseStatement = cond[0].split(symbol)
        if len(parseStatement) == 2:
            break

    if len(parseStatement) != 2:
        return (None, "Query error: unable to parse '" + cond[0] + "'.")
    else:
        parseLeft = parseStatement[0].split('.')
        if len(parseLeft) != 2:
            return (None, "Query error unable to parse '" + parseLeft[0] + "'.")
        elif parseLeft[0].lower() != 'node':
            return (None, "Query error unable to parse '" + parseLeft[0] + "' as a node.")

    for node in nodeList:

        entryCondition = False
        entryCondition = EvalPostfix(node, (0, (1)), attrs, cond, logicList)

        if cond == True or entryCondition == True:
            return node
        elif entryCondition not in [True, False]:
            return entryCondition

    return foundEntries


def getFieldPos(type, field, attrs):
    valpos = 0
    fieldType = None
    for att in attrs[type.lower()]:
        if att[0] == field:
            fieldType = att[1]
            break
        valpos += 1
    return valpos, fieldType


def getFieldValue(key, fieldpos, entryList):
    for entry in entryList:
        if entry[0] == key:
            if fieldpos >= 1:
                return str(entry[1][fieldpos - 1])
            if fieldpos == 0:
                return str(entry[0])
    return ''


def printEntryByFields(type, fields, entryList, attrs):

    if entryList[0] == 'empty':
        print(" 0 entries found")
    else:
        fieldposType = []
        enstrLst = []
        for field in fields:
            fieldposType.append(getFieldPos(type, field, attrs))

        fieldpos = [ent[0] for ent in fieldposType]
        fieldType = [ent[1] for ent in fieldposType]
        for entry in entryList:
            enstr = '('
            for i in range(len(fieldpos)):
                ind = fieldpos[i]
                if ind >= 1:
                    val = str(entry[1][ind - 1])
                    if fieldType[i] == 'V20':
                        val = '"' + val + '"'
                else:
                    val = str(entry[0])
                enstr += val + ", "
            enstrLst.append(enstr[0:-2] + ')')

        ents = [str(i + 1) for i in range(len(enstrLst))]
        maxent = max([len(en) for en in ents])
        fent = [(maxent - len(en)) * ' ' + en for en in ents]

        for i in range(len(enstrLst)):
            print(" ", fent[i], " ", enstrLst[i], sep='')


def printPath(initV, termV, fields, prevVerts, succEdges, distance, nodeList, edgeList, attrs):
    '''use Dijkstra's algorithm to find shortest path,
       then print out path'''
    if distance[termV] == math.inf:
        print(" no path found.")
    else:
        vertPath, edgePath = [], []
        loopKey = termV
        while loopKey != initV:
            vertPath.append(loopKey)
            edgePath.append(succEdges[loopKey])
            if prevVerts[loopKey] != -1:
                loopKey = prevVerts[loopKey]
        vertPath.append(initV)

        path = ''
        vertPath = vertPath[::-1]
        edgePath = edgePath[::-1]
        for i in range(len(vertPath)-1):
            vName = getFieldValue(vertPath[i], getFieldPos(
                'node', fields[0], attrs)[0], nodeList)
            eName = getFieldValue(edgePath[i], getFieldPos(
                'edge', fields[1], attrs)[0], edgeList)
            path += '(' + vName + ') ' + '─┤' + eName + '├─> '
        vName = getFieldValue(
            vertPath[-1], getFieldPos('node', fields[0], attrs)[0], nodeList)
        path += '(' + vName + ')'
        print(path)
    pass

########
############
#################
#################
############
########


def parenthesesVerifier(checkStr):
    '''ensure string has valid parentheses'''
    level = 0
    ind = 0
    while ind < len(checkStr):
        if checkStr[ind] == '(':
            level += 1
            lastOpen = ind
        if checkStr[ind] == ')':
            level -= 1
            if level < 0:
                return (')', ind)
        ind += 1
    if level > 0:
        return ('(', lastOpen)
    return (None, 0)


def parenthesesCleaner(checkStr):
    """removes redundant parentheses"""
    lastOpen, ind, opsymb = 0, 0, -1
    while ind < len(checkStr):
        if checkStr[ind] == '(':
            lastOpen = ind

        if checkStr[ind] in logicList:
            opsymb = ind

        if checkStr[ind] == ')':
            if lastOpen > opsymb and opsymb < ind:
                checkStr = checkStr[0:lastOpen] + \
                    checkStr[lastOpen + 1:ind] + checkStr[ind + 1:]
                lastOpen, ind, opsymb = 0, -1, -1

        ind += 1
    return checkStr


def queryVerifier(query):

    # condut parentheses check
    pResult = parenthesesVerifier(query)
    if pResult[0] != None:
        pos, ind = 0, 0
        while ind < pResult[1] and pos < len(query):
            if query[pos] == ' ':
                ind -= 1
            pos += 1
            ind += 1
        errType = 'extra closed parenthesis'
        if pResult[0] == '(':
            errType = 'extra open parenthesis'
        error = pResult[1] * ' ' + '↑ ' + errType
        return (True, error)

    comms = query.split(' ')
    if comms[0].upper() not in commandList:
        error = "Command error: '" + \
            comms[0] + "' is not a recognized command. Use command HELP for options."
        return (True, error)

    comms = query.upper().split(' ')
    for i in range(len(comms) - 1):
        if comms[i] == comms[i + 1] and comms[i] == 'AND':
            error = "input error: '" + comms[i] + "' duplicate and"
            return (True, error)
        if comms[i] == comms[i + 1] and comms[i] == 'OR':
            error = "input error: '" + comms[i] + "' duplicate or"
            return (True, error)
        if comms[i] in ['(', ')'] and comms[i + 1] in ['AND', 'OR']:
            error = "input error: missing statement"
            return (True, error)
        if comms[i] in ['AND', 'OR', 'TO'] and comms[i + 1] in ['AND', 'OR', 'TO']:
            error = "input error: '" + \
                comms[i] + "' '" + comms[i+1] + "': missing statement"
            return (True, error)

    return (None, True)


def saveSpace(inputStr):
    """preserve spaces in quotes"""
    inPar = False
    newStr = ''
    for ch in inputStr:
        if ch == '"':
            inPar = not inPar
            newStr += ch
        elif ch == ' ' and inPar:
            newStr += '■'
        else:
            newStr += ch
    return newStr


def commandParse(command):
    """first main parse, command and everything else"""
    # return command, args
    command += ' '
    command = command.replace('  ', ' ')
    command = command.strip()
    command = saveSpace(command)
    index = command.find(' ')
    if index == -1:
        return command.upper(), []
    else:
        comm = command[0:index]
        args = command[index + 1:]
    return comm.upper(), args


def parseFields(inputStr):
    newStr = ''
    POn = False
    for ch in inputStr:
        if ch == '(':
            POn = True

        if POn == True:
            newStr += ch
        if ch == ')':
            break
        fields = newStr[1:].split(',')
        fields = [field.strip() for field in fields]

    return fields


def formatInput(rawInput):

    if rawInput.find('"') == -1:
        for logname in keywords:
            rawInput = rawInput.replace(logname.lower(), logname.upper())
        for symbol in symbolList.keys():
            rawInput = rawInput.replace(symbol, symbolList[symbol])
        return rawInput
    else:
        formatInput = ''
        done = False
        pos = 0
        while done == False:
            consumeMe = rawInput[pos:]
            lqt = consumeMe.find('"')
            if lqt == -1:
                done = True
                formatInput += consumeMe
                break
            else:
                rqt = consumeMe[lqt + 1:].find('"')
                newInput = consumeMe[0:lqt]
                for logname in keywords:
                    newInput = newInput.replace(
                        logname.lower(), logname.upper())
                for symbol in symbolList.keys():
                    newInput = newInput.replace(symbol, symbolList[symbol])

                formatInput += newInput + consumeMe[lqt:lqt + rqt + 2]
                pos += lqt + rqt + 2

    return formatInput


def parseArgs(arg):
    """parses out arguments, parameters, and conditions"""

    if arg == []:
        return ([], [], '')

    args, fields, conditions = None, None, None

    WHEREind = arg.upper().find(' WHERE ')
    if WHEREind != -1:
        conditions = arg[WHEREind + 6:]
        conditions = formatInput(conditions)
        conditions = parenthesesCleaner(conditions.replace(' ', ''))
        arg = arg[0:WHEREind]

    labelBgn = arg.find('(')
    labelEnd = arg.rfind(')')
    if labelBgn != -1 and labelEnd != -1:
        fieldStr = arg[labelBgn:labelEnd + 1][1:-1]
        fields = [field.strip() for field in fieldStr.split(',')]
        arg = arg[0:labelBgn]
    else:
        fields = []
    args = [ar for ar in arg.split(' ') if len(ar) > 0]
    return (args, fields, conditions)


def fieldVerifier(field, attrs):
    valpos, typeName = None, []
    for atype, atts in attrs.items():
        for att in atts:
            if att[0] == field:
                valpos = int(att[-1])
                typeName.append(atype)
    return typeName, valpos


def argsVerifier(arg, fields, attrs):
    """parses out argument parameters and conditions"""

    if len(arg) > 1:
        error = "Expecting only one argument type"
        return (True, error)
    elif len(arg) == 1:
        argType = arg[0].upper()
        if argType not in typeList:
            error = "Graph type unknown: '" + arg + "' not recognized."
            return (True, error)

    if fields != None:
        for field in fields:
            types, valpos = fieldVerifier(field, attrs)
            if valpos == None:
                error = "Query error: object does not has attribute '" + field + "'"
                return (True, error)
            if arg[0].lower() not in types and arg[0].lower() != 'path':
                error = "Query error: object mismatch with '" + field + "'"
                return (True, error)

    return (None, True)


def entryVerifyer(type, parms, attr):

    attfields = attr[type]

    if len(attfields) != len(parms):
        error = "number of fields does not match number of type attributes"
        return (True, error)

    entry = []
    for ind in range(len(parms)):
        if attfields[ind][1] == 'V20':  # format text field to V20
            if len(parms[ind]) > 20:
                error = "text length of '" + \
                    parms[ind] + "'exceeds 20 charactors."
                return (True, error)
            else:
                entry.append(parms[ind])

        if attfields[ind][1] == 'Int':  # format Int as integer
            if not isInt(parms[ind]):
                error = "parameter '" + parms[ind] + \
                    "' cannot be resolved as an integer."
                return (True, error)
            else:
                entry.append(int(parms[ind]))

    return (None, entry)


def findDependantEdges(nodeKey, edgeList, attrs):
    linkFromPos, linkToPos = -1, -1
    for att in attrs['edge']:
        if att[0] == "LinkFrom":
            linkFromPos = int(att[-1]) - 2
        if att[0] == "LinkTo":
            linkToPos = int(att[-1]) - 2

    foundEdges = dict()
    for edge in edgeList:
        if edge[1][linkFromPos] == nodeKey or edge[1][linkToPos] == nodeKey:
            foundEdges.update({edge[0]: edge[0]})

    newList = [entry for entry in edgeList if entry[0]
               not in foundEdges.keys()]
    return list(foundEdges.keys()), newList

########
############
#################
#################
############
########
