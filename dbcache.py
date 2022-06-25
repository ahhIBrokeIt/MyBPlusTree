###################################
# -- This script is designed to run in Python 3.8 --
#  in-memory buffer pool class
###################################

import random
from collections import deque

# define cache buffer


class cache():
    """class for storing nodes in buffer
       methods employed: FIFO, LIFO, LFU, MFU, RR
    """

    def __init__(self, maxCount=1, DBHeader=None, method="FIFO"):
        self.nodes = dict()         # hash map to store nodes
        self.rids = set()           # set of nodes currently in cache
        self.header = DBHeader      # store header information
        self.nodeCount = 0          # initalize node counter
        self.nodeMax = maxCount     # max number of nodes allowed
        self.method = method        # method to rank node in cache
        self.usageList = deque()    # queue for FIFO/LIFO ranking
        self.usageFreq = dict()     # stores frequency ranking for LFU/MFU

    def setMaxCount(self, maxNum):
        if maxNum == 0:
            self.nodeMax = 1
        else:
            self.nodeMax = maxNum

    def setHeader(self, DBHeader):
        self.header = DBHeader

    def setMethod(self, method):
        self.method = method

    def lockNode(self, node):
        node.inUse = True

    def unlockNode(self, node):
        node.inUse = False

    def getWorstOffender(self):
        """selects which node to delete by method, return rid for deletion"""
        if self.method == "FIFO":
            return self.usageList[0]
        elif self.method == "LIFO":
            return self.usageList[-1]
        elif self.method == "LFU":
            keys = list(self.usageFreq.keys())
            vals = list(self.usageFreq.values())
            minVal = min(vals)
            return keys[vals.index(minVal)]
        elif self.method == "MFU":
            keys = list(self.usageFreq.keys())
            vals = list(self.usageFreq.values())
            maxVal = max(vals)
            return keys[vals.index(maxVal)]
        elif self.method == "RR":
            return random.choice(list(self.nodes.keys()))
        elif self.method == "MID":  # my own rotation process
            return self.usageList[self.nodeCount // 2]

    def popUsage(self, key):
        if self.method == "FIFO":
            self.usageList.popleft()
        elif self.method == "LFU" or self.method == "MFU":
            self.usageFreq.pop(key)

    def delUsage(self, key):
        if self.method == "FIFO" or self.method == "MID":
            self.usageList.remove(key)
        elif self.method == "LFU" or self.method == "MFU":
            self.usageFreq.pop(key)

    def insertUsage(self, rid):
        if self.method == "FIFO" or self.method == "MID":
            self.usageList.append(rid)
        elif self.method == "LFU" or self.method == "MFU":
            self.usageFreq.update({rid: 1})

    def updateUsage(self, rid):
        if self.method == "LFU" or self.method == "MFU":
            if self.usageFreq[rid] == None:
                self.usageFreq.update({rid: 1})
            else:
                self.usageFreq.update({rid: self.usageFreq.get(rid) + 1})
        if self.method == "FIFO" or "MID":
            self.usageList.remove(rid)
            self.usageList.append(rid)
        # if self.method == "RR": pass

    def getNode(self, key):
        self.updateUsage(key)
        return self.nodes[key]

    def insNode(self, node, *args):
        """insert node to cache, possibly returns node to potentially update to file"""
        commitNode = None           # potential node to commit ot file
        if len(args) == 1:          # handle any change of flags
            node.dirty = args[0]
        elif len(args) > 1:
            node.dirty = args[0]
            node.inUse = args[1]

        if node.rid in self.rids:  # node is already present in buffer
            self.updateUsage(node.rid)
            self.nodes.update({node.rid: node})
        else:                       # node is not in cache
            if self.nodeCount >= self.nodeMax:  # AND there's no room! yikes!
                # new node buffer overflow --> rotate out worst offending node
                rid = self.getWorstOffender()
                commitNode = self.nodes[rid]
                self.nodes.pop(rid)
                self.rids.remove(rid)
                self.popUsage(rid)
                self.nodeCount -= 1

            self.insertUsage(node.rid)
            self.nodes.update({node.rid: node})
            self.rids.add(node.rid)
            self.nodeCount += 1

        return commitNode

    def delNode(self, rid):
        if self.nodes[rid].inUse == False:
            self.nodes.pop(rid)
            self.rids.remove(rid)
            self.delUsage(rid)
            self.nodeCount -= 1
        pass
