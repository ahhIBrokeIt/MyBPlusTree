import math
import queue

class Graph:
    """Graph class holds lists of vertecies/edges, and graph methods"""

    def __init__(self):
        self.verts = dict()
        self.edges = dict()
        self.totalVerts = 0
        self.totalEdges = 0

    def AddVertex(self, key, name, vx, vy):
        newVert = Vertex(key, name, vx, vy)
        self.verts.update({key: newVert})
        self.totalVerts += 1

    def AddEdge(self, key, name, srcKey, tarKey, weight):
        newEdge = Edge(key, name, srcKey, tarKey, weight)
        self.edges.update({key: newEdge})
        self.totalEdges += 1

    def DijkstraShortestPath(self,vertKey):
        """Graph traversal using Disjkstra minweight algorithm"""

        def allVisited(vis):
            return sum([val for val in vis.values()])

        # Set distances of each vertex to "inf" and all prev vertecies are unvisited
        succEdges = dict()
        prevVerts = dict()
        distance = dict()
        visited = dict()
        for vkey in self.verts.keys():
            distance.update({vkey: math.inf})
            prevVerts.update({vkey: -1})
            visited.update({vkey: 0})
            succEdges.update({vkey: -1})

        # set starting Vertex to a distance of 0
        distance[vertKey] = 0

        done = False
        while allVisited(visited) < self.totalVerts and done == False:
            minWeight = math.inf
            currKey = -1
            for vkey in self.verts.keys():
                if distance[vkey] < minWeight and visited[vkey] == 0:
                    minWeight = distance[vkey]
                    currKey = vkey
            if currKey == -1: done = True

            if done == False:
                visited.update({currKey: 1})
                for edgeKey, edge in self.edges.items():
                    if edge.srcInd == currKey:
                        altPath = distance[currKey] + edge.weight
                        if altPath < distance[edge.tarInd]:
                            distance.update({edge.tarInd: altPath})
                            prevVerts.update({edge.tarInd: currKey})
                            succEdges.update({edge.tarInd: edgeKey})

        return prevVerts, succEdges, distance

class Vertex:
    """Defines the vetex class: contains a key label, and a xy-point"""
    def __init__(self, key, name, x=0, y=0):
        self.key = key
        self.name = name
        self.x = x
        self.y = y

class Edge:
    """Edge class contains source/target keys and index positions of verteces"""
    def __init__(self, key, name, sourceKey, targetKey, weight):
        self.key = key
        self.name = name
        self.srcInd = sourceKey
        self.tarInd = targetKey
        self.weight = weight
