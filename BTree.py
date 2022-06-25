###################################
# -- This script is designed to run in Python 3.8 --
#  B+ Tree data structure (with a graph stuffed in it!)
###################################

import abc      # for ABstract Class
import os       # Operating System, for file checking
import struct   # for handling binary file structures
import dbcache  # for handling cache
# from colorama import Fore, Back, Style      # add some color to dbms, some panache!

# invoke global in-memory cache
cache = dbcache.cache()


def CATTableFileReader(filename, dbFilename):
    file = open(filename, 'r')
    lines = file.readlines()
    file.close()

    tabDict = dict()
    for line in lines:
        if line[-1] == '\n':
            line = line[0:-1]
        splitLine = line.split(',')
        if len(splitLine) == 2:
            table, file = splitLine[0], splitLine[1]
            tabDict.update({file: table})

    if dbFilename in tabDict.keys():
        return tabDict[dbFilename]
    else:
        return None


def CATTableAttrReader(filename, fileTable):
    file = open(filename, 'r')
    lines = file.readlines()
    file.close()

    tables = dict()
    for line in lines:
        if line[-1] == '\n':
            line = line[0:-1]
        splitLine = line.split(',')
        if len(splitLine) == 5:
            tname, fieldtype, fieldname, type, pos = splitLine[
                0], splitLine[1], splitLine[2], splitLine[3], splitLine[4]
            if tname != fileTable:
                continue
            if fieldtype in tables:
                tables[fieldtype].append((fieldname, type, int(pos)))
            else:
                tables.update({fieldtype: [(fieldname, type, int(pos))]})

    for table in tables.keys():
        fields = tables[table]
        fields.sort(key=lambda tup: tup[2])

    return tables


def PrintData(prompt, entry):
    """Pretty-print the db Entry"""
    global cache
    fields = [str(ent) for ent in entry]

    if entry[0] >= 0:
        type = 'node'
    else:
        type = 'edge'

    entryLen = {}
    for i in range(len(cache.header['catalog'][type])):
        thisLength = max(
            len(cache.header['catalog'][type][i][0]), len(fields[i]))
        entryLen.update({i: thisLength})

    names = prompt
    entfield = len(names) * ' '
    for i in range(len(cache.header['catalog'][type])):
        names += cache.header['catalog'][type][i][0] + \
            (entryLen[i] - len(cache.header['catalog'][type][i][0])) * ' ' + '  '
        entfield += fields[i] + (entryLen[i] - len(fields[i])) * ' ' + '  '

    print(names)
    print(entfield)


def readDBHeader(dbfile):
    """returns header information of db file"""
    header = dict()
    blockArray = []
    dbfile.seek(0)
    minK = int(struct.unpack('I', dbfile.read(4))[0])
    maxK = int(struct.unpack('I', dbfile.read(4))[0])
    blockCount = int(struct.unpack('Q', dbfile.read(8))[0])
    root = int(struct.unpack('Q', dbfile.read(8))[0])
    dataRoot = int(struct.unpack('Q', dbfile.read(8))[0])
    block0 = int(struct.unpack('I', dbfile.read(4))[0])
    for _ in range(blockCount):
        block = int.from_bytes(dbfile.read(
            1), byteorder='little', signed=False)
        blockArray.append(block)

    # make a header
    header.update({'minKey': minK})
    header.update({'maxKey': maxK})
    header.update({'blockCount': blockCount})
    header.update({'rootRID': root})
    header.update({'dataRootRID': dataRoot})
    header.update({'block0': block0})
    header.update({'blockArray': blockArray})
    return header


def writeHeader(dbfile, house):
    """overwrite db header information"""
    dbfile.seek(0)
    dbfile.write(struct.pack('I', house['minKey']))
    dbfile.write(struct.pack('I', house['maxKey']))
    dbfile.write(struct.pack('Q', house['blockCount']))
    dbfile.write(struct.pack('Q', house['rootRID']))
    dbfile.write(struct.pack('Q', house['dataRootRID']))
    dbfile.write(struct.pack('I', house['block0']))  # block0 start position
    dbfile.write(bytearray(house['blockArray']))

#####
#######
# mini-map marker
#######
#####
# main B+ tree class


class BPlusTree:
    """<pun>root</pun> class for B+ tree"""

    def makeHouse(self):
        house = dict()
        house.update({'file': self.file})
        house.update({'minKey': self.minKey})
        house.update({'maxKey': self.maxKey})
        house.update({'blockCount': self.blockCount})
        house.update({'blockSize': self.blockSize})
        house.update({'block0': self.block0})
        house.update({'blockArray': self.blockArray})
        house.update({'arrayPos': self.arrayPos})
        house.update({'freeSlots': self.freeSlots})
        house.update({'catalog': self.catalog})
        if self.root != None:
            house.update({'rootRID': self.root.rid})
        else:
            house.update({'rootRID': 0})

        if self.dataRoot != None:
            house.update({'dataRootRID': self.dataRoot.rid})
        else:
            house.update({'dataRootRID': 0})
        return house

    def __init__(self, numBlocks, dbfile, catalog=None, bufferSize=None):
        global cache
        self.maxKey = 4  # <----  max allowable keys/node
        self.minKey = self.maxKey // 2  # <----  min allowable keys/node
        self.blockSize = 512  # <----  block size (in bytes)
        self.blockCount = numBlocks  # <----  number of blocks allowable in db
        self.blockArray = [0 for _ in range(self.blockCount)]
        self.freeSlots = numBlocks
        self.block0 = 0
        self.file = dbfile
        self.bufferSize = bufferSize
        self.catalog = catalog

        self.root = None
        self.dataRoot = None

        self.arrayPos = 0
        # move header information to cache
        cache.header = self.makeHouse()
        if self.bufferSize == None:
            # set default cache size to 10% of DB size
            cacheSize = max(2, self.blockCount // 10)
            cache.setMaxCount(cacheSize)
        else:
            cache.setMaxCount(self.bufferSize)

    def readDB(self):
        global cache
        overhead = readDBHeader(self.file)
        self.minKey = overhead['minKey']
        self.maxKey = overhead['maxKey']
        self.blockCount = overhead['blockCount']
        self.rootRef = overhead['rootRID']
        self.dataRootRef = overhead['dataRootRID']
        self.block0 = overhead['block0']
        self.blockArray = overhead['blockArray']
        self.arrayPos = 0

        # setup cache overhead
        cache.header = overhead
        cache.header['arrayPos'] = 0
        cache.header.update({'file': self.file})
        cache.header.update({'blockSize': self.blockSize})
        cache.header['freeSlots'] = self.blockCount - \
            sum(cache.header['blockArray'])
        cache.header.update({'catalog': self.catalog})

        if self.bufferSize == None:
            # set default cache size to 10% of DB size
            cacheSize = max(1, self.blockCount // 10)
            cache.setMaxCount(cacheSize)
        else:
            cache.setMaxCount(self.bufferSize)

        # prepare db with root nodes
        self.dataRoot = RID().node(self.dataRootRef)
        if cache.header['dataRootRID'] == cache.header['rootRID']:
            self.root = self.dataRoot
        else:
            self.root = RID().node(self.rootRef)

    def newDB(self):
        global cache
        # write new empty database
        rootRef, drootRef = 0, 0
        emptyBlock = [0 for _ in range(self.blockSize)]

        self.file.write(struct.pack('I', self.minKey))
        self.file.write(struct.pack('I', self.maxKey))
        self.file.write(struct.pack('Q', self.blockCount))
        self.file.write(struct.pack('Q', rootRef))
        self.file.write(struct.pack('Q', drootRef))
        self.block0 = struct.calcsize('IIQQQI') + self.blockCount
        self.file.write(struct.pack('I', self.block0))  # block0 start position
        self.file.write(bytearray(self.blockArray))
        for _ in range(self.blockCount):
            self.file.write(bytearray(emptyBlock))

        # formally start a new dataRoot node
        self.dataRoot = RID().newDataNode()
        RID().writeNode(self.dataRoot)
        self.root = None
        cache.header = self.makeHouse()

    def searchKey(self, key):
        """search db for key --> return tuple"""
        # mount to the root
        if self.root != None:
            node = RID().node(self.root.rid)
        else:
            node = RID().node(self.dataRoot.rid)
        # jump down
        return node.search(key)

    def RootSplit(self, key, link):
        """Handle splitting root at key"""
        global cache
        newRoot = RID().newIndexNode(key, [self.root.rid, link])
        self.root = newRoot
        self.rootRef = self.root.rid
        RID().updateNode(newRoot)
        cache.header.update({'rootRID': self.root.rid})
        cache.header.update({'dataRootRID': self.dataRoot.rid})

    def insertKey(self, keyDat):
        """inserts (key, data) tuple into tree"""

        inputKey, data = keyDat[0], tuple(keyDat[1:])

        # if tree is still a seed --> fill dataRoot node
        if self.root == None or self.root == self.dataRoot:
            (key, link) = self.dataRoot.insert((inputKey, data), 0)
            if key != None and key != 'full':     # the seed breaks open --> and spawns a root!
                newRoot = RID().newIndexNode(
                    key, [self.dataRoot.rid, link.rid])
                self.rootRef = newRoot.rid
                self.root = newRoot
                RID().updateNode(self.root)
                cache.header.update({'rootRID': self.root.rid})
                cache.header.update({'dataRootRID': self.dataRoot.rid})
        else:                  # regular tree growth
            (key, link) = self.root.insert((inputKey, data), 0)
            if key != None and key != 'full':
                self.RootSplit(key, link.rid)

        if key == 'full':
            return 'full'
        # update new root reference information
        self.dataRoot = RID().node(self.dataRoot.rid)
        if self.root != None:
            self.root = RID().node(self.root.rid)
            RID().updateNode(self.dataRoot)
            cache.header.update({'rootRID': self.root.rid})
            cache.header.update({'dataRootRID': self.dataRoot.rid})

    def deleteKey(self, key):
        """deletes (key, data) tuple from tree"""

        delLink = None

        if self.root == None:   # little tree version
            LeftNbor = self.dataRoot
            RightNbor = self.dataRoot
            LeftAnchor = self.dataRoot
            RightAnchor = self.dataRoot
            self.dataRoot.delete(key, 0, LeftNbor, RightNbor,
                                 LeftAnchor, RightAnchor, 0, 0, self.dataRoot)
        else:                   # big tree version
            LeftNbor = self.root
            RightNbor = self.root
            LeftAnchor = self.root
            RightAnchor = self.root
            delLink = self.root.delete(
                key, 0, LeftNbor, RightNbor, LeftAnchor, RightAnchor, 0, 0, self.dataRoot)

        if delLink != None:     # handle last-minute deletion
            RID().delNode(delLink)
            self.root = RID().node(self.root.rid)
            self.dataRoot = RID().node(self.dataRoot.rid)
            RID().updateNode(self.root)
            cache.header.update({'rootRID': self.root.rid})
            cache.header.update({'dataRootRID': self.dataRoot.rid})

        # check for root re-wiring
        if self.root != self.dataRoot and self.root != None:
            if len(self.root.keys) == 0:
                tempRID = self.root.link[0]
                RID().delNode(self.root)
                self.root = RID().node(tempRID)
                self.dataRoot = RID().node(self.dataRoot.rid)
                RID().updateNode(self.root)
                cache.header.update({'rootRID': self.root.rid})
                cache.header.update({'dataRootRID': self.dataRoot.rid})
                if self.root.rid == self.dataRoot.rid:
                    self.root = None
        else:
            pass

        # ensure in-memory roots are up to date
        if self.root != None:
            cache.header.update({'rootRID': self.root.rid})
            self.root = RID().node(self.root.rid)
        cache.header.update({'dataRootRID': self.dataRoot.rid})
        self.dataRoot = RID().node(self.dataRoot.rid)

    def printArray(self):
        global cache
        house = cache.header
        self.blockArray = house['blockArray']
        self.blockCount = house['blockCount']

        print("Tree Used vs. Free Dump")
        for i in range(self.blockCount):
            print(i % 10, " ", end='')
        print()
        for i in range(self.blockCount):
            print(self.blockArray[i], " ", end='')
        print("\n", flush=True)

    def recDump(self, cur_node, tabs):
        """Recursive portion of pre-order traversal"""
        if cur_node == None:
            cur_node = self.dataRoot

        cur_node.printNode(tabs)
        print("")
        for nextLink in cur_node.link:
            if nextLink != None:
                self.recDump(RID().node(nextLink), tabs + "    ")

    def dump(self):
        """Prints traversal of tree"""
        self.printArray()

        print("Dump of B+Tree")
        self.recDump(self.root, '')

    def leafDump(self):
        """Prints leaf-traversal of tree (left to right)"""
        print("Leaves of B+Tree")
        node = self.dataRoot
        while True:
            node.printNode('    ')
            if node.next != -1:
                print(',')
            else:
                print('.')
                break
            node = RID().node(node.next)

    def ReadOut(self):
        """Get list of all key values in DB"""
        readout = []
        node = self.dataRoot
        while True:
            for val in node.slots:
                readout.append(val)
            if node.next == -1:
                break
            else:
                node = RID().node(node.next)
        return readout

    def isEmpty(self):
        """return True if DB empty, return False o.w."""
        droot = self.dataRoot
        if len(droot.slots) == 0:
            return True
        return False

    def cacheOut(self):
        """commit all dirty nodes to file"""
        global cache
        writeHeader(self.file, cache.header)
        for rid in cache.nodes.keys():
            if cache.nodes[rid].dirty == True:
                if hasattr(cache.nodes[rid], 'keys'):
                    RID().writeIndexNode(self.file, cache.nodes[rid])
                else:
                    RID().writeDataNode(self.file, cache.nodes[rid])
        pass

#####
#######
# mini-map marker
#######
#####
# Define RID class


class RID(BPlusTree):
    """Reference ID class"""

    def __init__(self): pass

    def findFreeBlock(self):
        global cache
        refID = cache.header['arrayPos']
        while cache.header['blockArray'][refID] > 0:
            refID = (refID + 1) % cache.header['blockCount']
            if refID == cache.header['arrayPos']:  # no room --> return nothing
                return None
        cache.header['arrayPos'] = refID
        return refID

    def isNodeInCache(self, refID):
        global cache
        if refID in cache.rids:
            return 1
        else:
            return 0

    def cacheHandle(self, node, *flags):
        global cache
        oldNode = cache.insNode(node, *flags)
        if oldNode != None:
            if oldNode.dirty == True:
                self.writeNode(oldNode)

    def node(self, refID):
        """returns node with given refID"""
        global cache
        # check cache first
        if refID in cache.rids:
            return cache.getNode(refID)
        # not in cache --> get from file and throw to cache
        nodeFromFile = self.readNode(refID)
        self.cacheHandle(nodeFromFile, False, False)
        return nodeFromFile

    def newIndexNode(self, key, links):
        """create new index-node to db file on block with refID"""
        global cache
        refID = self.findFreeBlock()
        if refID == None:
            return None
        # if you're here, there is room --> return new node
        newNode = IndexNode(
            cache.header['minKey'], cache.header['maxKey'], key, links, refID)
        cache.header['blockArray'][refID] = 1
        cache.header['freeSlots'] -= 1
        self.cacheHandle(newNode, True, False)
        return newNode

    def newDataNode(self):
        """create new data-node to db file on block with refID"""
        global cache
        refID = self.findFreeBlock()
        if refID == None:
            return None
        # if you're here, there is room --> return new node
        newNode = DataNode(
            cache.header['minKey'], cache.header['maxKey'], refID)
        cache.header['blockArray'][refID] = 1
        cache.header['freeSlots'] -= 1
        self.cacheHandle(newNode, True, False)
        return newNode

    def updateNode(self, node):
        """update node to db file on block using node.rid"""
        global cache
        self.cacheHandle(node, True)

    def writeNode(self, node):
        global cache
        # if node.keys exists --> node is an index-node, o.w. node is data-node
        if hasattr(node, 'keys'):
            self.writeIndexNode(cache.header['file'], node)
        else:
            self.writeDataNode(cache.header['file'], node)

    def writeIndexNode(self, dbfile, node):
        """writes index-node to file"""
        global cache
        nodeSize = 0
        dbfile.seek(cache.header['block0'] +
                    node.rid * cache.header['blockSize'])
        dbfile.write(struct.pack('c', bytes('I', 'ascii')))
        nodeSize += struct.calcsize('c')
        dbfile.write(struct.pack('I', node.rid))
        nodeSize += struct.calcsize('I')
        dbfile.write(struct.pack('h', len(node.keys)))
        nodeSize += struct.calcsize('h')
        dbfile.write(struct.pack('h', len(node.link)))
        nodeSize += struct.calcsize('h')
        for key in node.keys:
            dbfile.write(struct.pack('q', key))
            nodeSize += struct.calcsize('q')
        for refid in node.link:
            dbfile.write(struct.pack('q', refid))
            nodeSize += struct.calcsize('q')
        for _ in range(cache.header['blockSize'] - nodeSize):
            dbfile.write(struct.pack('b', 0))

    def writeDataNode(self, dbfile, node):
        """writes data-node to file"""
        global cache
        nodeSize = 0
        dbfile.seek(cache.header['block0'] +
                    node.rid * cache.header['blockSize'])
        # write data node header
        dbfile.write(struct.pack('c', bytes('D', 'ascii')))
        dbfile.write(struct.pack('h', len(node.slots)))
        dbfile.write(struct.pack('q', node.next))
        dbfile.write(struct.pack('I', node.rid))
        nodeSize += struct.calcsize('c') + struct.calcsize('h') + \
            struct.calcsize('q') + struct.calcsize('I')
        # write data node keys and values
        for slot in node.slots:
            dbfile.write(struct.pack('q', slot[0]))
            nodeSize += struct.calcsize('q')
        for slot in node.slots:
            if slot[0] >= 0:     # positive key ==> node
                dataCAT = cache.header['catalog']['node'][1:]
            else:           # negative key ==> edge
                dataCAT = cache.header['catalog']['edge'][1:]
            data = slot[1]
            for i in range(len(dataCAT)):
                if dataCAT[i][1] == 'Int':
                    dbfile.write(struct.pack('q', data[i]))
                    nodeSize += struct.calcsize('q')

                if dataCAT[i][1] == 'V20':
                    dbfile.write(data[i].encode('ascii'))
                    filler = [0 for _ in range(20 - len(data[i]))]
                    dbfile.write(bytearray(filler))
                    nodeSize += 20
        # write filler to reach preset blockSize bytes
        for _ in range(cache.header['blockSize'] - nodeSize):
            dbfile.write(struct.pack('b', 0))

    def readNode(self, refID):
        global cache
        """loads node from DB file"""
        dbfile = cache.header['file']
        dbfile.seek(cache.header['block0'] + refID * cache.header['blockSize'])
        nodeType = chr(ord(struct.unpack('c', dbfile.read(1))[0]))
        if nodeType == 'I':
            node = IndexNode(
                cache.header['minKey'], cache.header['maxKey'], None, None, refID)
            node.rid = int(struct.unpack('I', dbfile.read(4))[0])
            KeyLinks = struct.unpack('h', dbfile.read(2))
            numKeys = int(KeyLinks[0])
            KeyLinks = struct.unpack('h', dbfile.read(2))
            numLinks = int(KeyLinks[0])
            for _ in range(numKeys):
                key = int(struct.unpack('q', dbfile.read(8))[0])
                node.keys.append(key)
            for _ in range(numLinks):
                refid = int(struct.unpack('q', dbfile.read(8))[0])
                node.link.append(refid)

        elif nodeType == 'D':
            node = DataNode(cache.header['minKey'], cache.header['maxKey'])
            numSlots = int(struct.unpack('h', dbfile.read(2))[0])
            node.next = int(struct.unpack('q', dbfile.read(8))[0])
            node.rid = int(struct.unpack('I', dbfile.read(4))[0])
            keys, vals = [], []
            for _ in range(numSlots):       # read the keys
                key = int(struct.unpack('q', dbfile.read(8))[0])
                keys.append(key)

            for i in range(numSlots):       # read the fields
                if keys[i] >= 0:    # positive key ==> node
                    dataCAT = cache.header['catalog']['node'][1:]
                else:               # negative key ==> edge
                    dataCAT = cache.header['catalog']['edge'][1:]
                fields = []
                for i in range(len(dataCAT)):
                    if dataCAT[i][1] == 'Int':
                        fields.append(
                            int(struct.unpack('q', dbfile.read(8))[0]))

                    if dataCAT[i][1] == 'V20':
                        bstr = dbfile.read(20)
                        stop = bstr.decode('ascii').find('\x00')
                        if stop == -1:
                            stop = 20
                        fields.append(bstr.decode('ascii')[0:stop])
                pass

                vals.append(tuple(fields))

            for i in range(numSlots):       # build data slots
                node.slots.append((keys[i], vals[i]))

        return node

    def delNode(self, node):
        """update data-node to db file on block with refID"""
        global cache
        cache.header['blockArray'][node.rid] = 0
        cache.header['freeSlots'] += 1
        if node.rid in cache.rids:
            cache.delNode(node.rid)
        pass


# Define abstract class methods
class NodeType():
    @abc.abstractmethod
    def insert(self, keyVal): pass
    @abc.abstractmethod
    def printNode(self, indent): pass
    @abc.abstractmethod
    def printStrNode(self, indent): pass
    @abc.abstractmethod
    def search(self, key): pass

    @abc.abstractmethod
    def delete(self, key, cur_lvl, LNbor, RNbor, LAnchor,
               RAnchor, LAnch_lvl, RAnch_lvl, droot): pass

#####
#######
# mini-map marker
#######
#####
###
# Index Node class


class IndexNode(NodeType):
    """Index class structure to handle parsing data."""

    def __init__(self, minK, maxK, key, links=None, rid=-1):
        self.rid = rid
        self.dirty = False
        self.inUse = False
        self.minKey = minK
        self.maxKey = maxK
        self.keys = []
        self.link = []
        if key != None:
            self.keys.append(key)
        if links != None:
            self.link = links

    def search(self, key):
        """search B+ tree by key - index node version"""
        index = 0
        for indexKey in self.keys:
            if key < indexKey:
                break
            index += 1
        return RID().node(self.link[index]).search(key)

    def testsearch(self, key, curCnt):
        index = 0
        for indexKey in self.keys:
            if key < indexKey:
                break
            index += 1
        MorF = RID().isNodeInCache(self.link[index])
        return RID().node(self.link[index]).testsearch(key, curCnt + MorF)

    def indexSplit(self, *keysAndLinks):
        """create new data node with input keysAndLinks = ([keys], [links])"""
        newINode = RID().newIndexNode(0, keysAndLinks[1])
        newINode.keys = keysAndLinks[0]
        RID().updateNode(newINode)
        return newINode

    def insert(self, keyVal, cur_lvl):
        key = keyVal[0]

        # jump down the rabbit hole ... but which one?
        index = 0
        for indexKey in self.keys:
            if key < indexKey:
                break
            index += 1

        # send (key, val) down the pike, and wait for something to surface from the deep
        (key, link) = RID().node(self.link[index]).insert(keyVal, cur_lvl + 1)

        # if normal insertion happened --> traverse back with no changes
        # else: new link provided --> insert new (key, link) node
        if key == None:
            return (None, self)
        elif key == 'full':
            return (key, self)
        else:
            if len(self.keys) < self.maxKey:    # always room for one more ...
                index = 0
                for indexKey in self.keys:
                    if key < indexKey:
                        break
                    index += 1

                self.keys.insert(index, key)
                self.link.insert(index + 1, link.rid)
                RID().updateNode(self)
                return (None, self)
            else:                               # until there isn't --> split index nodes
                if key < self.keys[self.minKey - 1]:
                    # perform un-even split
                    newKeys = self.keys[-self.minKey - 1:]
                    newLinks = self.link[-self.minKey - 1:]
                    minMaxKey = newKeys.pop(0)

                    newNode = self.indexSplit(newKeys, newLinks)
                    self.keys = self.keys[0:self.minKey - 1]
                    self.link = self.link[0:self.minKey]

                    index = 0
                    for indexKey in self.keys:
                        if key < indexKey:
                            break
                        index += 1

                    self.keys.insert(index, key)
                    self.link.insert(index + 1, link.rid)

                    RID().updateNode(self)
                    # send new node back up
                    return (minMaxKey, newNode)
                else:
                    # perform even split
                    newKeys = self.keys[-self.minKey:]
                    newLinks = self.link[-self.minKey:]

                    newNode = self.indexSplit(newKeys, newLinks)
                    self.keys = self.keys[0:self.minKey]
                    self.link = self.link[0:self.minKey + 1]

                    index = 0
                    for indexKey in newNode.keys:
                        if key < indexKey:
                            break
                        index += 1

                    newNode.keys.insert(index, key)
                    newNode.link.insert(index, link.rid)

                    minMaxKey = newNode.keys.pop(0)

                    RID().updateNode(self)
                    RID().updateNode(newNode)
                    # send new right node back up
                    return (minMaxKey, newNode)

        return (None, self)

    def shiftLR(self, leftNode, anchorNode):
        """performs index node shift from left to current"""
        # remove rightmost data from left neighbor
        leftKey = leftNode.keys[-1]
        leftlnk = leftNode.link[-1]
        leftNode.keys.pop(-1)
        leftNode.link.pop(-1)

        # locate pivot key in anchor node and swap pivot key
        pivotIndex = 0
        for key in anchorNode.keys:
            if leftKey < key:
                break
            pivotIndex += 1

        tempkey = anchorNode.keys[pivotIndex]
        anchorNode.keys[pivotIndex] = leftKey

        # shift to current
        self.keys.insert(0, tempkey)
        self.link.insert(0, leftlnk)

        RID().updateNode(self)
        RID().updateNode(leftNode)
        RID().updateNode(anchorNode)

    def shiftRL(self, rightNode, anchorNode):
        """performs index node shift from right to current"""
        # remove rightmost data from left neighbor
        rightKey = rightNode.keys[0]
        rightlnk = rightNode.link[0]
        rightNode.keys.pop(0)
        rightNode.link.pop(0)

        # locate pivot key in anchor node and swap pivot key
        pivotIndex = 0
        for key in anchorNode.keys:
            if rightKey < key:
                break
            pivotIndex += 1

        pivotIndex -= 1

        tempkey = anchorNode.keys[pivotIndex]
        anchorNode.keys[pivotIndex] = rightKey

        # shift to current
        self.keys.append(tempkey)
        self.link.append(rightlnk)

        RID().updateNode(self)
        RID().updateNode(rightNode)
        RID().updateNode(anchorNode)

    def mergeLeft(self, leftNode, anchorNode):
        """merge self to left index"""
        # locate pivot key in anchor node

        keyCheck = leftNode.keys[-1]
        pivotIndex = 0
        for key in anchorNode.keys:
            if keyCheck < key:
                break
            pivotIndex += 1

        keyPivotIndex = pivotIndex
        if keyPivotIndex == len(anchorNode.keys):
            keyPivotIndex -= 1

        # copy pivot key and merge to left node
        leftNode.keys.append(anchorNode.keys[keyPivotIndex])
        for key in self.keys:
            leftNode.keys.append(key)
        for link in self.link:
            leftNode.link.append(link)

        # pop pivot key.link from anchor node
        anchorNode.keys.pop(keyPivotIndex)
        anchorNode.link.pop(keyPivotIndex + 1)

        RID().updateNode(self)
        RID().updateNode(leftNode)
        RID().updateNode(anchorNode)

    def mergeRight(self, rightNode, anchorNode):
        """merge right index to self"""
        keyCheck = self.keys[-1]

        # locate pivot key in anchor node
        pivotIndex = 0
        for key in anchorNode.keys:
            if keyCheck < key:
                break
            pivotIndex += 1

        keyPivotIndex = pivotIndex
        if keyPivotIndex == len(anchorNode.keys):
            keyPivotIndex -= 1

        # copy pivot key and merge to left node
        self.keys.append(anchorNode.keys[keyPivotIndex])
        self.link.append(rightNode.link[0])
        rightNode.link.pop(0)
        for key in rightNode.keys:
            self.keys.append(key)
        for link in rightNode.link:
            self.link.append(link)

        # pop pivot key/link from anchor node
        anchorNode.keys.pop(keyPivotIndex)
        anchorNode.link.pop(keyPivotIndex + 1)

        RID().updateNode(self)
        RID().updateNode(rightNode)
        RID().updateNode(anchorNode)

    def delete(self, key, cur_lvl, LNbor, RNbor, LAnchor, RAnchor, LAnch_lvl, RAnch_lvl, droot):
        """delete for index node"""
        global cache

        index = 0
        for thiskey in self.keys:
            if key < thiskey:
                break
            index += 1

        # determine next neighbors and anchors
        nxtLLvl, nxtRLvl = LAnch_lvl, RAnch_lvl
        if index == 0:                      # next node is leftmost
            nextL = RID().node(LNbor.link[-1])
            nextR = RID().node(self.link[index + 1])
            nxtLAn = LAnchor
            nxtRAn = self
            nxtRLvl = cur_lvl
        elif index == len(self.link) - 1:   # next node is rightmost
            nextL = RID().node(self.link[index - 1])
            nextR = RID().node(RNbor.link[0])
            nxtLAn = self
            nxtRAn = RAnchor
            nxtLLvl = cur_lvl
        else:                               # next node is a middle node
            nextL = RID().node(self.link[index - 1])
            nextR = RID().node(self.link[index + 1])
            nxtLAn = self
            nxtRAn = self
            nxtLLvl, nxtRLvl = cur_lvl, cur_lvl

        # send key down the pike, and wait for something to surface from the deep
        delLink = RID().node(self.link[index]).delete(
            key, cur_lvl + 1, nextL, nextR, nxtLAn, nxtRAn, nxtLLvl, nxtRLvl, droot)

        # goodnight sweet prince, embrace the ever-after
        if delLink != None:
            RID().delNode(delLink)

        # check for underflow
        if len(self.keys) < self.minKey:
            # check if root
            if cur_lvl == 0 and len(self.keys) == 0:
                return None
            else:
                # check for shift
                nodeIsLeftmost, nodeIsRightmost = False, False
                if LNbor.keys[0] > self.keys[0]:
                    nodeIsLeftmost = True
                elif RNbor.keys[0] < self.keys[0]:
                    nodeIsRightmost = True

                leftKeyNum, rightKeyNum = len(LNbor.keys), len(RNbor.keys)
                if nodeIsLeftmost:
                    leftKeyNum = self.minKey
                elif nodeIsRightmost:
                    rightKeyNum = self.minKey

                if leftKeyNum > self.minKey or rightKeyNum > self.minKey:
                    if leftKeyNum > rightKeyNum:
                        self.shiftLR(LNbor, LAnchor)
                    elif leftKeyNum < rightKeyNum:
                        self.shiftRL(RNbor, RAnchor)
                    else:
                        if LAnch_lvl >= RAnch_lvl:
                            self.shiftLR(LNbor, LAnchor)
                        else:
                            self.shiftRL(RNbor, RAnchor)

                else:  # check for merging conditions
                    # node is left-most
                    if nodeIsLeftmost and rightKeyNum == self.minKey:
                        self.mergeRight(RNbor, RAnchor)
                        return RNbor

                    # node is middle-most
                    if leftKeyNum == self.minKey and rightKeyNum == self.minKey:
                        if LAnch_lvl >= RAnch_lvl or self == LNbor:
                            self.mergeLeft(LNbor, LAnchor)
                            return self

                        elif LAnch_lvl < RAnch_lvl or nodeIsRightmost:
                            self.mergeRight(RNbor, RAnchor)
                            return RNbor

                    # node is right-most
                    if nodeIsRightmost and rightKeyNum == self.minKey:
                        self.mergeLeft(LNbor, LAnchor)
                        return LNbor
        return None

    def printNode(self, indent):
        print(indent + '( ', sep='', end='')
        k, l = 0, 0
        while k + l < len(self.keys) + len(self.link):
            if l < len(self.link):
                print('*', sep='', end='')
                l += 1

            if k + l < len(self.keys) + len(self.link) - 1:
                print(", ", end='')

            if k < len(self.keys):
                print(self.keys[k], sep='', end='')
                k += 1

            if k + l < len(self.keys) + len(self.link):
                print(", ", end='')

        print(' )', str(self.rid), end='')

    def printStrNode(self, indent):
        strNode = indent + '( '
        k, l = 0, 0
        while k + l < len(self.keys) + len(self.link):
            if l < len(self.link):
                strNode += '*'
                l += 1

            if k + l < len(self.keys) + len(self.link) - 1:
                strNode += ", "

            if k < len(self.keys):
                strNode += str(self.keys[k])
                k += 1

            if k + l < len(self.keys) + len(self.link):
                strNode += ', '

        return strNode + ' ) ' + str(self.rid)

#########
###########
############
##############
# mini-map marker

# Data Node class


class DataNode(NodeType):
    """Node class structure to handle storing the data."""

    def __init__(self, minK, maxK, rid=-1):
        self.minKey = minK
        self.maxKey = maxK
        self.slots = []
        self.next = -1
        self.link = [None]
        self.rid = rid
        self.dirty = False
        self.inUse = False

    def search(self, key):
        """data node search: check for key -> return data or nothing"""
        for slot in self.slots:
            if key == slot[0]:
                return slot[1]
        return None

    def insert(self, keyVal, cur_lvl):
        """inserts (key, val) tuple in leaf/data node.
           Returns (key, pointer) if needed one node up"""

        key, val = keyVal[0], keyVal[1]

        # duplicate insertion --> overwrite old keyVal tuple
        for i in range(len(self.slots)):
            if key == self.slots[i][0]:
                self.slots[i] = keyVal
                RID().updateNode(self)
                return (None, self)

        # new insertion
        # check if free space allows for worst-case splitting
        if cur_lvl >= cache.header['freeSlots']:
            return ('full', self)

        if len(self.slots) < self.maxKey:

            if len(self.slots) == 0:
                self.slots.append(keyVal)
            else:
                skip = False
                for i in range(len(self.slots)):
                    if self.slots[i][0] >= key:
                        self.slots.insert(i, (key, val))
                        skip = True
                        break
                if skip == False:
                    self.slots.append((key, val))

            RID().updateNode(self)

        else:  # handle splitting the node
            tempNextNode = self.next
            newNode = RID().newDataNode()
            self.next = newNode.rid
            newNode.slots = self.slots[-self.minKey:]
            self.slots = self.slots[0:self.minKey]
            newNode.next = tempNextNode

            found = False
            # determine which node gets the insert
            if key < newNode.slots[0][0]:
                # go to old left (original) node
                nodeSlots = self.slots
            # else go to new (right) node
            else:
                nodeSlots = newNode.slots

            for i in range(len(nodeSlots)):
                if key < nodeSlots[i][0]:
                    found = True
                    nodeSlots.insert(i, (key, val))
                    break
            if found == False:
                nodeSlots.append((key, val))

            minMaxKey = newNode.slots[0][0]

            RID().updateNode(self)
            RID().updateNode(newNode)
            return (minMaxKey, newNode)         # send new node up the chain

        return (None, self)                     # send point back up the chain

    def shiftLR(self, leftNode, anchorNode):
        """performs leaf node shift from left to current"""

        # remove rightmost data from left neighbor
        KeyVal = leftNode.slots[-1]
        leftNode.slots.pop(-1)

        # shift to current
        self.slots.insert(0, KeyVal)

        minMaxKey = self.slots[0][0]

        # locate pivot key in anchor node and replace
        pivotIndex = 0
        for key in anchorNode.keys:
            if minMaxKey < key:
                break
            pivotIndex += 1
        if pivotIndex == len(anchorNode.keys):
            pivotIndex -= 1

        anchorNode.keys[pivotIndex] = minMaxKey

        RID().updateNode(self)
        RID().updateNode(leftNode)
        RID().updateNode(anchorNode)

    def shiftRL(self, rightNode, anchorNode):
        """performs leaf node shift from right to current"""
        # remove leftmost data from right neighbor
        keyVal = rightNode.slots[0]
        rightNode.slots.pop(0)
        oldpivot = keyVal[0]
        minMaxKey = rightNode.slots[0][0]

        # shift to current
        self.slots.append(keyVal)

        # locate pivot key in anchor node and replace
        pivotIndex = 0
        for key in anchorNode.keys:
            if oldpivot < key:
                break
            pivotIndex += 1
        keyPivotIndex = pivotIndex

        keyPivotIndex -= 1
        if keyPivotIndex == len(anchorNode.keys):
            keyPivotIndex -= 1

        anchorNode.keys[keyPivotIndex] = minMaxKey

        RID().updateNode(self)
        RID().updateNode(rightNode)
        RID().updateNode(anchorNode)

    def mergeLeft(self, leftNode, anchorNode):
        # locate pivot key in anchor node and delete
        minMaxKey = self.slots[0][0]
        pivotIndex = 0
        for key in anchorNode.keys:
            if minMaxKey < key:
                break
            pivotIndex += 1

        keyPivotIndex = pivotIndex - 1
        if keyPivotIndex == len(anchorNode.keys):
            keyPivotIndex -= 1

        # delete index key and link from anchor node
        anchorNode.keys.pop(keyPivotIndex)
        anchorNode.link.pop(pivotIndex)

        # move slots over to left neighbor
        for keyVal in self.slots:
            leftNode.slots.append(keyVal)

        # snip self out of link list
        leftNode.next = self.next

        RID().updateNode(self)
        RID().updateNode(leftNode)
        RID().updateNode(anchorNode)

    def mergeRight(self, rightNode, anchorNode):
        # locate pivot key in anchor node and delete

        selfMaxKey = self.slots[-1][0]
        pivotIndex = 0
        for key in anchorNode.keys:
            if selfMaxKey < key:
                break
            pivotIndex += 1

        keyPivotIndex = pivotIndex

        # delete index key and lnk from anchor node
        anchorNode.keys.pop(keyPivotIndex)
        anchorNode.link.pop(keyPivotIndex + 1)

        # move slots over to left neighbor
        for keyVal in rightNode.slots:
            self.slots.append(keyVal)

        # snip right neighbor out of link list
        self.next = rightNode.next

        RID().updateNode(self)
        RID().updateNode(rightNode)
        RID().updateNode(anchorNode)

    def delete(self, key, cur_lvl, LNbor, RNbor, LAnchor, RAnchor, LAnch_lvl, RAnch_lvl, droot):
        """deletes tuple with input key"""
        # perform the delete
        for i in range(len(self.slots)):
            if self.slots[i][0] == key:
                self.slots.pop(i)
                RID().updateNode(self)
                break

        # special condition: last node on the left is empty
        if self == droot and cur_lvl == 0 and len(self.slots) == 0:
            return None

        if len(self.slots) < self.minKey:  # check for regular underflow
            leftKeyNum, rightKeyNum = len(LNbor.slots), len(RNbor.slots)
            ShiftConditionisGood, MergeConditionisGood = False, False

            # check shift condition
            if self.rid == droot.rid and rightKeyNum > self.minKey:
                ShiftConditionisGood = True
            elif self.slots[0][0] > RNbor.slots[0][0] and leftKeyNum > self.minKey:
                ShiftConditionisGood = True
            elif leftKeyNum > self.minKey or rightKeyNum > self.minKey:
                ShiftConditionisGood = True

            if self.rid == droot.rid and rightKeyNum == self.minKey:
                MergeConditionisGood = True
            elif self.slots[0][0] > RNbor.slots[0][0] and leftKeyNum == self.minKey:
                MergeConditionisGood = True
            elif leftKeyNum == self.minKey and rightKeyNum == self.minKey:
                MergeConditionisGood = True

            # special condition: last node on the left
            if self.rid == droot.rid and cur_lvl == 0:
                ShiftConditionisGood, MergeConditionisGood = False, False

            if ShiftConditionisGood and not MergeConditionisGood:
                # check for shiftLR condition
                if self.rid == droot.rid:
                    self.shiftRL(RNbor, RAnchor)
                elif self.slots[0][0] > RNbor.slots[0][0]:
                    self.shiftLR(LNbor, LAnchor)
                else:
                    if leftKeyNum > rightKeyNum:
                        self.shiftLR(LNbor, LAnchor)

                    # check for shiftRL condition
                    elif leftKeyNum < rightKeyNum:
                        self.shiftRL(RNbor, RAnchor)

                    else:
                        if LAnch_lvl >= RAnch_lvl:
                            self.shiftLR(LNbor, LAnchor)
                        else:
                            self.shiftRL(RNbor, RAnchor)

            # check for merge condition
            if MergeConditionisGood:
                if self.rid == droot.rid:
                    self.mergeRight(RNbor, RAnchor)
                    return RNbor
                elif self.slots[0][0] > RNbor.slots[0][0]:
                    self.mergeLeft(LNbor, LAnchor)
                    return self
                else:
                    # check for merge left
                    if LAnch_lvl >= RAnch_lvl:
                        self.mergeLeft(LNbor, LAnchor)
                        return self
                    else:
                        self.mergeRight(RNbor, RAnchor)
                        return RNbor

        # no underflow --> all done
        return None

    def printNode(self, indent):
        """printNode variant for displaying keys of data node"""
        print(indent + '[ ', sep='', end='')
        for i in range(len(self.slots)):
            if i < len(self.slots) - 1:
                print(self.slots[i][0], ", ", sep='', end='')
            else:
                print(self.slots[i][0], " ", sep='', end='')
        print(']', str(self.rid), end='')

    def printStrNode(self, indent):
        """printNode variant for displaying keys of data node"""
        string = indent + '[ '
        for i in range(len(self.slots)):
            if i < len(self.slots) - 1:
                string += str(self.slots[i][0]) + ", "
            else:
                string += str(self.slots[i][0]) + " "
        string += '] ' + str(self.rid)
        return string
