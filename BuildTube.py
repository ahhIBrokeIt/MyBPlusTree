
def TubeIT():
    file = open("LondonTube.txt", 'r')
    lines = file.readlines()
    file.close()

    lines = lines[1:]

    nodes = dict()
    for txtline in lines:
        line, direction, stationA, stationB, dist, runTime, highTime, lowTime = txtline[:-1].split(',')
        # print(stationA, ', ', line, ', ', sep='')
        nodes.update({stationA: [line]})

    for txtline in lines:
        line, direction, stationA, stationB, dist, runTime, highTime, lowTime = txtline[:-1].split(',')
        # print(stationA, ', ', line, ', ', sep='')
        nodes[stationA].append(line)

    maxLines = 0
    for key, vals in nodes.items():
        uniq = dict()
        for val in vals:
            uniq.update({val: val})
        nodes[key] = list(uniq)

    # for key in nodes.keys():
    #     print(nodes[key])
    print(" nodes count = ",len(nodes.keys()))
    # print(nodes)

    nodeList = []
    i = 0
    for key in nodes.keys():
        for val in nodes[key]:
            nodeList.append([i, key, val])
            i += 1

    # for node in nodeList:
    #     print(node)

    edges = dict()
    for txtline in lines:
        line, direction, stationA, stationB, dist, runTime, highTime, lowTime = txtline[:-1].split(',')
        # print(stationA, ', ', line, ', ', sep='')
        edges.update({stationA + 'α' + stationB: [line, direction, stationA, stationB, dist, runTime]})

    i = 1
    edgeList = []
    for key in edges.keys():
        statA, statB = key.split('α')
        # print(key, ":::", statA, ":::", statB)
        for node in nodeList:
            if statA == node[1]:
                for Tonode in nodeList:
                    if statB == Tonode[1]:
                        edgeList.append([i, node[0], Tonode[0], edges[key][1], edges[key][4], edges[key][5]])
                        i += 1

    for j in range(len(nodeList)-1):
        if nodeList[j][1] == nodeList[j + 1][1]:
            # print(nodeList[j], "  --  ", nodeList[j + 1])
            edgeList.append([i, nodeList[j][0], nodeList[j+1][0], 'interchange', '0.0', '0.0'])
            i += 1

    print(" edges count = ",len(edgeList))

    return nodeList, edgeList