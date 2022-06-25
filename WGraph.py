##########################
#
#  Graph visualizer
#
##########################

import math, random
import wGraphClass
import pygame
import concurrent.futures

# Define the colors we will use in RGB format
BLACK = (  0,   0,   0)
GRAY =  (128, 128, 128)
MIDGRAY=( 64,  64,  64)
WHITE = (255, 255, 255)
BLUE =  (  0,   0, 255)
GREEN = (  0, 255,   0)
RED =   (255,   0,   0)

# Initialize the game engine
pygame.init()

class DisplayGraph:

    def __init__(self, newGraph, filename):
        global pygame
        self.spr = math.pow(10,-2*(1+math.log(2)))  # set spring stength
        self.DecayFactor = 0.90                     # set decay factor 0 < DecayFactor < 1

        self.nodeRad = 6                            # radius of node

        # Set the height and width of the screen
        self.canvasHeight = 600
        self.canvasWidth = 16 * self.canvasHeight // 9
        self.canvasWidth = 4 * self.canvasHeight // 3
        self.size = [self.canvasWidth, self.canvasHeight]

        # set intiial window size (to be adjusted on the fly in cycle)
        self.win_x = [-100.0, 100.0]
        self.win_y = [-100.0, 100.0]
        self.padding = 25.0

        self.graph = newGraph

        self.screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption("Graph of " + filename)

        pygame.font.init()
        VertFont = pygame.font.SysFont('Arial', 12)

        self.textLabel = dict()
        self.caughtVert = dict()
        for vkey in self.graph.verts.keys():
            self.textLabel.update({vkey: VertFont.render(self.graph.verts[vkey].name, True, BLACK)})
            self.caughtVert.update({vkey: False})

        self.edgeLabel = dict()
        for edgekey in self.graph.edges.keys():
            self.edgeLabel.update({edgekey: VertFont.render(self.graph.edges[edgekey].name, True, MIDGRAY)})

        ### initialize vertex positions and movement for each vertex to zero
        # if a vertex is selected by the mouse
        self.dx = dict()
        self.dy = dict()
        i = 0
        for vert in self.graph.verts.values():
            vert.x = 0.75 * self.win_x[1] * math.cos(2 * i * math.pi/len(self.graph.verts))
            vert.y = 0.75 * self.win_y[1] * math.sin(2 * i * math.pi/len(self.graph.verts))
            self.dx.update({vert.key: 0.0})
            self.dy.update({vert.key: 0.0})
            i += 1

    def Pnt2Pixel(self, x, y, winx, winy):
        """convert (x,y) position in window to pixel position on screen"""
        px = math.floor( self.canvasWidth/(winx[1] - winx[0]) * (x - winx[0]))
        py = math.floor(self.canvasHeight/(winy[1] - winy[0]) * (y - winy[0]))
        return [px, py]

    def Pixel2Pnt(self, px, py, winx, winy):
        """convert (px,py) pixel position to approximate window position"""
        x = px * (winx[1] - winx[0]) / self.canvasWidth + winx[0]
        y = py * (winy[1] - winy[0]) / self.canvasHeight + winy[0]
        return [x, y]

    def text_objects(self, text, font):
        textSurface = font.render(text, True, BLACK)
        return textSurface, textSurface.get_rect()

    def message_display(self, vNum, x, y):
        TextSurf = self.textLabel[vNum]
        TextRect = self.textLabel[vNum].get_rect()
        TextRect.center = (x,y)
        self.screen.blit(TextSurf, TextRect)

    def message_edge_display(self, eNum, Pnt, theta):
        angle = -180 * theta / math.pi
        if angle < -90:
            angle += 180
        TextSurf = self.edgeLabel[eNum]
        TextRect = self.edgeLabel[eNum].get_rect()
        TextRect.center = (Pnt[0], Pnt[1])
        self.screen.blit(pygame.transform.rotate(TextSurf, angle), TextRect)

    def DrawVerts(self):
        """plot all veticies from graph object in window size"""
        wx, wy = self.win_x, self.win_y
        for vkey, vert in self.graph.verts.items():
            vertx = math.floor(vert.x)
            verty = math.floor(vert.y)
            px, py = self.Pnt2Pixel(vertx, verty, self.win_x, self.win_y)
            self.message_display(vkey, self.nodeRad + px + 15, self.nodeRad + py - 15)
            pygame.draw.circle(self.screen, BLACK, self.Pnt2Pixel(vertx,verty,wx, wy), self.nodeRad)
            pygame.draw.circle(self.screen, GREEN, self.Pnt2Pixel(vertx,verty,wx, wy), self.nodeRad-2)

    def calcArrow(self, target, theta):
        rad = self.nodeRad + 5
        div = 5*math.pi/6
        theta1, theta2 = theta + div, theta - div
        arrPnt1 = [int(target[0] + rad * math.cos(theta1)), int(target[1] + rad * math.sin(theta1))]
        arrPnt2 = [int(target[0] + rad * math.cos(theta2)), int(target[1] + rad * math.sin(theta2))]
        return [tuple(target), tuple(arrPnt1), tuple(arrPnt2)]

    def DrawArrow(self, source, target, theta, width):
        arrowHead = self.calcArrow(target, theta)
        pygame.draw.line(self.screen, BLACK, source, target, width)
        pygame.draw.polygon(self.screen, BLACK, arrowHead, 0)

    def DrawEdges(self):
        """plot all edges from graph object in window size"""
        wx, wy = self.win_x, self.win_y
        for edgekey, edge in self.graph.edges.items():
            src_x = math.floor(self.graph.verts[edge.srcInd].x)
            src_y = math.floor(self.graph.verts[edge.srcInd].y)
            tar_x = math.floor(self.graph.verts[edge.tarInd].x)
            tar_y = math.floor(self.graph.verts[edge.tarInd].y)
            lineWidth = edge.weight // 3
            if (lineWidth == 0): lineWidth = 1

            if src_x == tar_x and src_y == tar_y:
                circCent = self.Pnt2Pixel(src_x, src_y, wx, wy)
                circCent[0] -= 3 * self.nodeRad
                circLabel = [circCent[0], circCent[1] + 3 * self.nodeRad + 5]
                arrowHead = self.calcArrow(self.Pnt2Pixel(tar_x, tar_y, wx, wy), -math.pi / 2.5)
                pygame.draw.circle(self.screen, BLACK, circCent, 3 * self.nodeRad, lineWidth)
                pygame.draw.polygon(self.screen, BLACK, arrowHead, 0)
                self.message_edge_display(edgekey, circLabel, 0)
            else:
                theta = math.atan2(tar_y - src_y , tar_x - src_x)
                self.DrawArrow(self.Pnt2Pixel(src_x, src_y, wx, wy), self.Pnt2Pixel(tar_x, tar_y, wx, wy), theta, lineWidth)

                mid_x = (src_x + tar_x) // 2
                mid_y = (src_y + tar_y) // 2
                self.message_edge_display(edgekey, self.Pnt2Pixel(mid_x, mid_y, wx, wy), theta)

    def CycleGraph(self):
        """apply vetex repulsion and edge attration to graph"""
        ## Repulse vertices
        for vertV in self.graph.verts.values():
            for vertU in self.graph.verts.values():
                if (vertV != vertU):
                    Dx = vertV.x - vertU.x
                    Dy = vertV.y - vertU.y
                    dist = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)
                    if (dist < self.nodeRad): # if a vert is moved atop antoher => push the other vert away
                        vertU.x += random.randint(10,100)/100
                        vertU.y += random.randint(10,100)/100
                        Dx = vertV.x - vertU.x
                        Dy = vertV.y - vertU.y
                        dist = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)

                    r = 1/dist
                    theta = math.atan2(Dy,Dx)
                    self.dx[vertV.key] += r * math.cos(theta)
                    self.dy[vertV.key] += r * math.sin(theta)

        ## Attract edges
        for edge in self.graph.edges.values():
            Dx = self.graph.verts[edge.srcInd].x - self.graph.verts[edge.tarInd].x
            Dy = self.graph.verts[edge.srcInd].y - self.graph.verts[edge.tarInd].y
            r = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)
            theta = math.atan2(Dy,Dx)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            Mag = edge.weight * self.spr * r

            self.dx[edge.srcInd] += -Mag * cos_t
            self.dy[edge.srcInd] += -Mag * sin_t
            self.dx[edge.tarInd] +=  Mag * cos_t
            self.dy[edge.tarInd] +=  Mag * sin_t

        ### advance each vertex
        minx, maxx, miny, maxy = 0, 0, 0, 0
        for vert in self.graph.verts.values():
            vert.x += self.dx[vert.key]
            vert.y += self.dy[vert.key]
            if vert.x < minx: minx = vert.x
            if vert.x > maxx: maxx = vert.x
            if vert.y < miny: miny = vert.y
            if vert.y > maxy: maxy = vert.y

            # continual adjustment of window
            self.win_x = [minx - self.padding, maxx + self.padding]
            self.win_y = [miny - self.padding, maxy + self.padding]

    def RepluseVerts(self, vertV):
        for vertU in self.graph.verts.values():
            if (vertV != vertU):
                Dx = vertV.x - vertU.x
                Dy = vertV.y - vertU.y
                dist = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)
                if (dist < self.nodeRad): # if a vert is moved atop antoher => push the other vert away
                    vertU.x += random.randint(10,100)/100
                    vertU.y += random.randint(10,100)/100
                    Dx = vertV.x - vertU.x
                    Dy = vertV.y - vertU.y
                    dist = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)

                r = 1/dist
                theta = math.atan2(Dy,Dx)
                self.dx[vertV.key] += r * math.cos(theta)
                self.dy[vertV.key] += r * math.sin(theta)

    def AttractEdges(self, edge):
        Dx = self.graph.verts[edge.srcInd].x - self.graph.verts[edge.tarInd].x
        Dy = self.graph.verts[edge.srcInd].y - self.graph.verts[edge.tarInd].y
        r = math.pow(math.pow(Dx,2) + math.pow(Dy,2),0.5)
        theta = math.atan2(Dy,Dx)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        Mag = edge.weight * self.spr * r

        self.dx[edge.srcInd] += -Mag * cos_t
        self.dy[edge.srcInd] += -Mag * sin_t
        self.dx[edge.tarInd] +=  Mag * cos_t
        self.dy[edge.tarInd] +=  Mag * sin_t

    def reSizeWindow(self):
        minx, maxx, miny, maxy = 0, 0, 0, 0
        for vert in self.graph.verts.values():
            vert.x += self.dx[vert.key]
            vert.y += self.dy[vert.key]
            if vert.x < minx: minx = vert.x
            elif vert.x > maxx: maxx = vert.x
            if vert.y < miny: miny = vert.y
            elif vert.y > maxy: maxy = vert.y

            # continual adjustment of window
            self.win_x = [minx - self.padding, maxx + self.padding]
            self.win_y = [miny - self.padding, maxy + self.padding]

    def ThreadedCycleGraph(self):
        verts = (vert for vert in self.graph.verts.values())
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.RepluseVerts, verts)

        edges = (edge for edge in self.graph.edges.values())
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(self.AttractEdges, edges)

        self.reSizeWindow()

    def GrabVert(self):
        """detect mouse click on vertex and drag to user position"""
        if pygame.mouse.get_focused() == True:
            pygame.event.get()
            buttons = pygame.mouse.get_pressed()
            if buttons[0] == True: # left mouse button pressed
                mx,my = pygame.mouse.get_pos()

                for vkey in self.graph.verts.keys():
                    if self.caughtVert[vkey] == True:
                        wmx, wmy = self.Pixel2Pnt(mx, my, self.win_x, self.win_y)
                        self.graph.verts[vkey].x, self.graph.verts[vkey].y = wmx, wmy
                        break

                for vkey in self.graph.verts.keys():
                    wmx, wmy = self.Pixel2Pnt(mx, my, self.win_x, self.win_y)
                    vx, vy = self.graph.verts[vkey].x, self.graph.verts[vkey].y
                    distance = math.pow(math.pow(wmx - vx,2) + math.pow(wmy - vy,2),0.5)
                    if (distance <= self.nodeRad): # mouse pressed on vertex
                        self.caughtVert[vkey] = True
                        self.graph.verts[vkey].x, self.graph.verts[vkey].y = wmx, wmy
            else: # mouse button released => release captured vert
                for key in self.caughtVert.keys():
                    self.caughtVert[key] = False

    def RunGraph(self):
        clock = pygame.time.Clock()
        done = False
        while not done:
            clock.tick(60)

            for event in pygame.event.get(): # User did something
                if event.type == pygame.QUIT: # If user clicked close
                    done = True  # Flag that we are done so we exit this loop

            # Clear the screen and reset the screen background
            self.screen.fill(WHITE)

            # exponentially decay velocity of verticies
            for vertkey in self.graph.verts.keys():
                self.dx[vertkey] *= self.DecayFactor
                self.dy[vertkey] *= self.DecayFactor

            self.CycleGraph()
            # self.ThreadedCycleGraph()

            self.GrabVert()
            self.DrawEdges()
            self.DrawVerts()

            # Go ahead and update the screen with what has been drawn.
            pygame.display.flip()

        pygame.font.quit()
        pygame.quit()
