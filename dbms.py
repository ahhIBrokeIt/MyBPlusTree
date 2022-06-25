###################################
# -- This script is designed to run in Python 3.8 --
#  Graph DataBase - Main file
###################################

import BTree
import parse
import sys
import os
import concurrent.futures
import WGraph
import BuildTube


def getValidInt(prompt):
    """Integer input validator. input prompt for integer variable, returns integer type"""
    valid = False
    while not valid:
        error = False
        try:
            integer = int(input(prompt))
        except:
            error = True
        if error:
            print("    That isn't an integer. Try again with a numerical value.")
        elif integer < 1:
            print("    Integer must have a positvie value.")
        else:
            valid = True

    return integer


def ExitAngry(prompt):
    """You made a mistake so egregious, one must immediately exit entirely from the program."""
    print(prompt)
    sys.exit()


def CATTableVerifier():
    """verifies table.cat exists and table names have length <= 20"""
    if not os.path.exists('Table.cat'):
        ExitAngry("Table.cat file missing. Cannot continue with file.")

    tabFile = open('Table.cat', 'r')
    lines = tabFile.readlines()
    tabFile.close()
    for line in lines:
        parms = line.split(',')
        if len(parms) != 2:
            ExitAngry(
                "Table.cat error: incorrect number of parameters with line containing: " + line)
        if len(parms[0]) > 20:
            ExitAngry("Table.cat error: table name '" +
                      parms[0] + "' is too long. Max length is 20.")
        if len(parms[1]) > 20:
            ExitAngry("Table.cat error: file name '" +
                      parms[1] + "' is too long. Max length is 20.")


def CATAtterVerifier():
    """verifies Attr.cat exists and table/attribute names have length <= 20"""
    if not os.path.exists('Attr.cat'):
        ExitAngry("Attr.cat file missing. Cannot continue without file.")

    AttrFile = open('Attr.cat', 'r')
    lines = AttrFile.readlines()
    AttrFile.close()

    nodecheck, edgecheck = False, False
    edgeFromCheck, edgeToCheck = False, False
    for line in lines:
        parms = line[:-1].split(',')
        if len(parms) != 5:
            ExitAngry(
                "Attr.cat error: incorrect number of parameters with line containing: " + line)
        if len(parms[1]) > 20:
            ExitAngry("Attr.cat error: table name '" +
                      parms[1] + "' is too long. Max length is 20.")
        if len(parms[2]) > 20:
            ExitAngry("Attr.cat error: attribute name '" +
                      parms[2] + "' is too long. Max length is 20.")
        if parms[1] not in ['node', 'edge']:
            ExitAngry("Attr.cat error: attribute type '" +
                      parms[2] + "' is not a node or edge.")
        if parms[3] not in ['Int', 'V20']:
            ExitAngry("Attr.cat error: attribute type '" +
                      parms[3] + "' is unknown. Must use 'Int' or 'V20'.")
        if parms[3] != 'Int' and parms[4] == '1':
            ExitAngry("Attr.cat error: attribute '" +
                      parms[2] + "' must be 'Int' type.")
        if parms[1] == 'edge':
            edgecheck = True
        if parms[1] == 'node':
            nodecheck = True
        if parms[1] == 'edge' and parms[2] == 'LinkTo':
            edgeToCheck = True
        if parms[1] == 'edge' and parms[2] == 'LinkFrom':
            edgeFromCheck = True

    if nodecheck == False:
        ExitAngry("Attr.cat error: attribute 'node' missing.")
    if edgecheck == False:
        ExitAngry("Attr.cat error: attribute 'edge' missing.")
    if edgeFromCheck == False:
        ExitAngry("Attr.cat error: edge attribute 'LinkFrom' missing.")
    if edgeToCheck == False:
        ExitAngry("Attr.cat error: edge attribute 'LinkTo' missing.")
    pass


def findFirstNode(leafNodes):
    """given sorted list of tuples with keys ---> return index wof first non-negative key value"""

    if len(leafNodes) == 0:
        return None

    lower = 0
    upper = len(leafNodes)
    index = len(leafNodes) // 2
    done = False
    while not done:
        if leafNodes[index][0] == 0:
            return index
        elif leafNodes[index][0] < 0:
            lower = index
            index = int(0.5 * (lower + upper))
        elif leafNodes[index][0] > 0:
            upper = index
            index = int(0.5 * (lower + upper))
        if abs(lower - upper) <= 1:
            done = True

    if leafNodes[lower][0] >= 0:
        return lower
    else:
        return upper


def parseVertsEdges(db):
    AllTheData = db.ReadOut()
    split = findFirstNode(AllTheData)
    if split != None:
        edgeList = AllTheData[0:split]
        nodeList = AllTheData[split:]
    else:
        edgeList = []
        nodeList = []

    return nodeList, edgeList


def packageGraph(nodeName, edgeName, attrs, nodeList, edgeList):
    """with datanode list --> return graph of nodes and edges"""
    dbGraph = WGraph.wGraphClass.Graph()
    for node in nodeList:
        vName = parse.getFieldValue(node[0], parse.getFieldPos(
            'node', nodeName, attrs)[0], nodeList)
        dbGraph.AddVertex(node[0], vName, 0, 0)

    for edge in edgeList:
        eName = parse.getFieldValue(edge[0], parse.getFieldPos(
            'edge', edgeName, attrs)[0], edgeList)
        eFrom = parse.getFieldValue(edge[0], parse.getFieldPos(
            'edge', 'LinkFrom', attrs)[0], edgeList)
        eTo = parse.getFieldValue(edge[0], parse.getFieldPos(
            'edge', 'LinkTo', attrs)[0], edgeList)
        dbGraph.AddEdge(edge[0], eName, int(eFrom), int(eTo), 7)

    return dbGraph


def printSchema(attrType, attrs):
    fields = '( '
    for att in Attrs[attrType]:
        fields += att[0] + ' (' + att[1] + ')' + ', '
    fields = fields[0:-2] + ' )'
    print("\t       ", attrType, fields)


if __name__ == "__main__":

    if len(sys.argv) == 1:
        ExitAngry(
            "No database file given. Please restart with a database file as an argument.")
    dbFilename = sys.argv[1]

    # aquire catalog information.
    FileTable = BTree.CATTableFileReader('Table.cat', dbFilename)

    # Verify cat files
    CATTableVerifier()
    CATAtterVerifier()

    # Perform table association and attribution checks
    if FileTable == None:
        ExitAngry(
            "Table.cat error: No table association for file '" + dbFilename + "'")
    Attrs = BTree.CATTableAttrReader('Attr.cat', FileTable)

    # Everything checks out --> start dbms

    if not os.path.exists(dbFilename):
        print("The file ", dbFilename,
              " does not exist. Creating new database.", sep='')
        numBlocks = getValidInt("\tEnter number of blocks: ")
        DBfile = open(dbFilename, 'wb+')
        MyTree = BTree.BPlusTree(numBlocks, DBfile, Attrs)
        MyTree.newDB()
    else:
        DBfile = open(dbFilename, 'rb+')
        MyTree = BTree.BPlusTree(1, DBfile, Attrs)
        MyTree.readDB()

    print("┌──────────────────────────────────────────────────────┐")
    print("├─ Your Database options:                              │")
    print("│   GET   PUT   DELETE   VISUAL   EXIT   INFO   HELP   │")
    print("└──────────────────────────────────────────────────────┘")

    option = 'not zero'
    while option != 0:

        # option = getValidInt("Enter your option: ")
        inputLine = input("\t>>> ")

        command, args = None, None
        error = parse.queryVerifier(inputLine)
        if error[0] != None:
            print("\t   ", error[1])
        else:
            command, args = parse.commandParse(inputLine)
            args, fields, conditions = parse.parseArgs(args)

        # print("  command : >", command,"<", sep='')
        # print("arguments :", args)

        if command == 'EXIT':
            option = 0
            print("Commiting database to file.")
            MyTree.cacheOut()
            DBfile.close()

########################

        if command == 'GET':
            error = (None, True)
            if args == []:
                error = (True, "\t   " + 'GET <???> missing object type.')
            elif args[0] not in ['node', 'edge', 'path']:
                error = (True, "\t   '" + args[0] + "': unknown object type.")
            elif fields == []:
                error = (True, "\t   " + 'GET ' +
                         args[0] + ' (???) fields missing.')
                printSchema(args[0].lower(), Attrs)

            elif args[0].upper() == 'PATH' and len(fields) != 2:
                error = (True, "\t   " + 'GET ' +
                         args[0] + ' must have only two fields. (node, edge)')

            if error[0] == None:
                error = parse.argsVerifier(args, fields, Attrs)

            if error[0] == None and args[0].upper() == 'PATH':
                field1Type = parse.fieldVerifier(fields[0], Attrs)[0]
                field2Type = parse.fieldVerifier(fields[1], Attrs)[0]
                if 'node' not in field1Type:
                    error = (True, "first field not a node attribute.")
                elif 'edge' not in field2Type:
                    error = (True, "second field not an node attribute.")

            if error[0] == None:
                vertList, EdgeList = parseVertsEdges(MyTree)
                argType = args[0].lower()
                if argType in ['node', 'edge']:
                    postfixConditions = True
                    if conditions != None:
                        conditions = conditions.replace('■', ' ')
                        postfixConditions = parse.InFix2Postfix(
                            conditions, parse.logicList)
                    FoundEntries = parse.FindMatch(
                        args[0].lower(), vertList, EdgeList, postfixConditions, Attrs)

                    if FoundEntries == []:
                        FoundEntries = ['empty']
                    if FoundEntries[0] == None:
                        print(FoundEntries[1])
                    else:
                        distinct = dict()
                        for ent in FoundEntries:
                            distinct.update({ent[0]: ent})
                        FoundEntries = [val for val in distinct.values()]
                        parse.printEntryByFields(
                            args[0].lower(), fields, FoundEntries, Attrs)
                elif argType == 'path':
                    # parse path conditions
                    conditions = conditions.replace('■', ' ')
                    splitter = conditions.split('→')
                    if len(splitter) == 2:
                        PfixInit = parse.InFix2Postfix(
                            splitter[0], parse.logicList)
                        PfixTerm = parse.InFix2Postfix(
                            splitter[1], parse.logicList)
                        err1 = parse.findNode(PfixInit, vertList, Attrs)
                        err2 = parse.findNode(PfixTerm, vertList, Attrs)
                        if err1[0] == None:
                            print(err1[1])
                        elif err2[0] == None:
                            print(err2[1])
                        else:
                            InitVal, TermVal = err1, err2
                            dbGraph = packageGraph(
                                fields[0], fields[1], Attrs, vertList, EdgeList)
                            vertP, edgeP, dist = dbGraph.DijkstraShortestPath(
                                InitVal[0])
                            parse.printPath(
                                InitVal[0], TermVal[0], fields, vertP, edgeP, dist, vertList, EdgeList, Attrs)
                    else:
                        error = (
                            True, '2 nodes required:  node1.attr TO node2.attr')
            else:
                print(error[1])

########################

        if command == 'PUT':
            error = (None, True)
            if args == []:
                error = (True, "\t   " + 'PUT <???> missing object type.')
            elif args[0] not in ['node', 'edge']:
                error = (True, "\t   '" + args[0] + "': unknown object type.")
            elif fields == []:
                error = (True, "\t   " + 'PUT ' +
                         args[0] + ' (???) fields missing.')
                printSchema(args[0].lower(), Attrs)

            if error[0] == None:
                if fields != []:
                    vertList, EdgeList = parseVertsEdges(MyTree)
                    fields = parse.parseFields(inputLine)
                    entry = parse.entryVerifyer(args[0], fields, Attrs)

                    if entry[0] == None:
                        if args[0].lower() == 'node':
                            if entry[1][0] < 0:
                                entry = (
                                    True, 'node key cannot be a negative integer.')
                        else:
                            if entry[1][0] <= 0:
                                entry = (
                                    True, 'edge key must be a positive integer.')
                        if entry[0] == True:
                            print("\t   ", entry[1])
                    if entry[0] == None:
                        if args[0].lower() == 'edge':
                            entry[1][0] = 0 - entry[1][0]
                            linkFm = entry[1][int(parse.getFieldPos(
                                'edge', 'LinkFrom', Attrs)[0])]
                            linkTo = entry[1][int(parse.getFieldPos(
                                'edge', 'LinkTo', Attrs)[0])]

                            if MyTree.searchKey(linkFm) == None:
                                entry = (False, None)
                                print("\t   ", "node with key ", linkFm,
                                      " not in database.", sep='')
                            if MyTree.searchKey(linkTo) == None:
                                entry = (False, None)
                                print("\t   ", "node with key ", linkTo,
                                      " not in database.", sep='')

                        if entry[0] == None:
                            error = MyTree.insertKey(entry[1])
                            if error == 'full':
                                print(
                                    '\t   ', 'Cannot insert entry. Database is full')
                    else:
                        print('\t   ', entry[1])
                else:
                    printSchema(args[0].lower(), Attrs)
            else:
                print(error[1])

########################

        if command == 'DELETE':
            error = (None, True)
            if args == []:
                error = (True, "\t   " + 'DELETE <???> missing object type.')
            elif fields != []:
                error = (True, "\t   " + 'DELETE ' +
                         args[0] + ' no fields for delete.')
            elif args[0].lower() not in ['node', 'edge']:
                error = (True, "\t   " +
                         'DELETE <type>: object type must be node or edge.')

            if error[0] == None:
                error = parse.argsVerifier(args, fields, Attrs)

            if error[0] == None:
                vertList, EdgeList = parseVertsEdges(MyTree)
                postfixConditions = True
                if conditions != None:
                    conditions = conditions.replace('■', ' ')
                    postfixConditions = parse.InFix2Postfix(
                        conditions, parse.logicList)

                FoundEntries = parse.FindMatch(
                    args[0].lower(), vertList, EdgeList, postfixConditions, Attrs)
                if len(FoundEntries) > 1 and FoundEntries[0] == None:
                    print(FoundEntries[1])
                else:
                    if args[0].lower() == 'node':
                        FoundEntries = [
                            entry for entry in FoundEntries if entry[0] >= 0]
                    elif args[0].lower() == 'edge':
                        FoundEntries = [
                            entry for entry in FoundEntries if entry[0] < 0]
                    if FoundEntries == []:
                        FoundEntries = ['empty']

                    distinct = dict()
                    for ent in FoundEntries:
                        distinct.update({ent[0]: ent})

                    FoundEntries = [val for val in distinct.values()]
                    if FoundEntries[0] == 'empty':
                        print("\t\t0 entries deleted.")
                    elif args[0].lower() == 'node':
                        nodesDel = len(
                            [entry for entry in FoundEntries if entry[0] >= 0])
                        edgesDel = 0
                        print(" nodes to delete: ", nodesDel)
                        for entry in FoundEntries:
                            MyTree.deleteKey(entry[0])
                            DepEdges, EdgeList = parse.findDependantEdges(
                                entry[0], EdgeList, Attrs)
                            edgesDel += len(DepEdges)
                            for edgekey in DepEdges:
                                MyTree.deleteKey(edgekey)

                        print("\t\t", nodesDel, " nodes deleted. ",
                              edgesDel, " orphan edges deleted.", sep='')

                    elif args[0].lower() == 'edge':
                        edgesDel = len(FoundEntries)
                        for entry in FoundEntries:
                            MyTree.deleteKey(entry[0])
                        print("\t\t", edgesDel, " edges deleted.", sep='')
            else:
                print(error[1])

########################

        if command == 'VISUAL':
            error = (None, True)
            if args == []:
                args = ['PATH']
            if fields == []:
                error = (True, "\t   " + 'VISUAL (???) fields missing.')
            elif len(fields) != 2:
                error = (True, "\t   " +
                         'VISUAL must have only two fields. (node, edge)')

            if error[0] == None:
                error = parse.argsVerifier(args, fields, Attrs)

            if error[0] == None:
                field1Type = parse.fieldVerifier(fields[0], Attrs)[0]
                field2Type = parse.fieldVerifier(fields[1], Attrs)[0]
                if 'node' not in field1Type:
                    error = (True, "first field not a node attribute.")
                elif 'edge' not in field2Type:
                    error = (True, "second field not an edge attribute.")

            if error[0] == None:
                vertList, EdgeList = parseVertsEdges(MyTree)
                graph = packageGraph(
                    fields[0], fields[1], Attrs, vertList, EdgeList)
                if len(vertList) > 0:
                    vgraph = WGraph.DisplayGraph(graph, dbFilename)
                    with concurrent.futures.ProcessPoolExecutor() as executor:
                        executor.map(vgraph.RunGraph())
                else:
                    print("Graph has zero nodes. Nothing to visualize.")
            else:
                print(error[1])

########################

        # # load the london tube system
        # if command == 'LOAD':
        #     nodelst, edgelst = BuildTube.TubeIT()

        #     for node in nodelst:
        #         print(node, flush=True)
        #         MyTree.insertKey(node)

        #     for edge in edgelst:
        #         entry = []
        #         entry.append(0 - edge[0])
        #         for val in edge[1:]:
        #             entry.append(val)
        #         print(entry)
        #         MyTree.insertKey(entry)

########################

        if command == 'INFO':
            if args == []:
                printSchema('node', Attrs)
                printSchema('edge', Attrs)
            elif args[0].lower() in ['node', 'edge']:
                printSchema(args[0].lower(), Attrs)

########################

        if command == 'HELP':
            if args == []:
                print("\t   HELP <command> -- provides expected grammar of <command>")
                print(
                    "\t\t available commands are: GET, PUT, DELETE, VISUAL, EXIT, HELP")
            elif args[0].upper() == 'GET':
                print("\t   GET <node/edge> (field, ..., field) WHERE <condition>")
                print(
                    "\t\t returns a list entries that satisfy <condition> ordered by (fields)")
                print(
                    "\t   GET PATH (node.field, edge.field) WHERE node1.field TO node2.field")
                print("\t\t returns the shrtest path from node1 to node2")
            elif args[0].upper() == 'PUT':
                print(
                    "\t   PUT <node/edge>                      returns schema for type")
                print(
                    "\t   PUT <node/edge> (field, ..., field)  will insert/overwrite an entry")
            elif args[0].upper() == 'DELETE':
                print("\t   DELETE <node/edge> WHERE <condition>")
                print(
                    "\t\t unceremoniously deletes all entries that satisfy <condition>")
                print("\t   DELETE <node/edge>")
                print("\t\t unceremoniously deletes all entries")
            elif args[0].upper() == 'VISUAL':
                print("\t   VISUAL (node.field, edge.field)")
                print("\t\t Force-directed graph visualization.")
                print("\t\t Nodes and edges labeled by node.field and edge.field")
            elif args[0].upper() == 'EXIT':
                print("\t   EXIT ")
                print(
                    "\t\t Single word command to EXIT for ending the program.\n\t\tHere, let me help you with that ...")
                option = 0
            elif args[0].upper() == 'INFO':
                print("\t   INFO               displays schema for all types")
                print("\t   INFO <node/edge>   displays schema for type")
            elif args[0].upper() == 'HELP':
                print("\t   HELP!  Title song of eponymous album by the Beatles.")
                print("\t\t Released 6 August 1965, published by Parlophone Records.")
                print(
                    "\t\t Produced by George Martin (no relation to author George R.R. Martin).")

########################
