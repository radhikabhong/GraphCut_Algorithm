import numpy as np
import imageio
from copy import deepcopy
import sys
import networkx as nx
import random
from edmonds_karp import edmonds_karp
from matplotlib import pyplot as plt
import cv2

class GraphCut(object):
    
    def __init__(self,texture,rows,cols):
        self.overlapCols = 0
        self.overlapRows = 0
        self.texture = texture
        self.variance = np.var(texture)
        shape = texture.shape
        self.patchRows = shape[0]
        self.patchCols = shape[1]
        self.realRows = rows
        self.realCols = cols
        rows += self.patchRows
        cols += self.patchCols
        self.imRows = rows
        self.imCols = cols
        self.old = np.zeros((rows,cols,3),dtype = np.int)
        self.new = np.zeros((rows,cols,3),dtype = np.int)
        self.mask = np.zeros((rows,cols),dtype = np.int)
        self.overlap_zone = np.zeros((rows,cols),dtype = np.int)
        self.seams = np.zeros((rows,cols,2),dtype = np.int)
        self.init_value_seams = np.zeros((rows,cols,2),dtype = np.int)
        self.maxpixel = self.patchRows * 30
        self.minpixel = self.patchCols * 14
        self.border_mask = [self.imRows,0,self.imRows,0]
        self.index = 1
    

    def change_masking(self,t):
        maxi = min(t[0] + self.patchRows, self.imRows)
        maxj = min(t[1] + self.patchCols, self.imCols)
        self.mask[t[0]:maxi,t[1]:maxj] = np.ones((maxi-t[0],maxj-t[1]),dtype=np.int)
        if (t[0] < self.border_mask[0]):
            self.border_mask[0] = t[0]
        if(t[0]+self.patchRows > self.border_mask[1]):
            self.border_mask[1] = t[0]+self.patchRows
        if(t[1] < self.border_mask[2] ):
            self.border_mask[2] = t[1]
        if(t[1]+self.patchCols > self.border_mask[3]):
            self.border_mask[3] = t[1]+self.patchCols

    def change_seams_value(self,corner_overlap, corner,mask_seam):
        for i in range(self.patchRows):
            for j in range(self.patchCols):
                x_crt = corner[0] + i
                y_crt = corner[1] + j
                if(x_crt >= corner_overlap[0] and x_crt < corner_overlap[0]+self.overlapRows and y_crt >= corner_overlap[1] and y_crt < corner_overlap[1]+self.overlapCols ):
                    if(mask_seam[x_crt-corner_overlap[0]][y_crt-corner_overlap[1]] == 2):
                        self.init_value_seams[x_crt][y_crt][0] = i
                        self.init_value_seams[x_crt][y_crt][1] = j
                else:
                    self.init_value_seams[x_crt][y_crt][0] = i
                    self.init_value_seams[x_crt][y_crt][1] = j
    def initialize(self):
        t = [0,0]
        self.old[t[0]:t[0]+self.patchRows,t[1]:t[1]+self.patchCols] = self.texture[0:self.patchRows,0:self.patchCols]
        self.new= deepcopy(self.old)
        self.change_masking(t)
        self.change_seams_value(t,t,np.ones((self.patchRows,self.patchCols)))

    def number_masking(self,p):
        nums = 0
        for i in range(-1,2):
            for j in range(-1,2):
                if(p[0]+i >= 0 and p[0] < self.imRows and p[1]+j >= 0 and p[1]+j < self.imCols):
                    if(self.mask[p[0]+i][p[1]+j] == 0):
                        nums += 1
        return nums

    def number_overlap(self,p): 
        nums = 0
        for i in range(-1,2):
            for j in range(-1,2):
                if(p[0]+i >= 0 and p[0] < self.imRows and p[1]+j >= 0 and p[1]+j < self.imCols):
                    if(self.overlap_zone[p[0]+i][p[1]+j] == 0):
                        nums += 1
        return nums

    def change_overlap(self,t):
        self.overlap_zone = np.zeros((self.imRows,self.imCols),dtype=np.int)
        corner = [0,0]
        self.overlapRows = self.overlapCols = 0
        first = True
        n = 0
        for u in range(self.patchRows ):
            for v in range(self.patchCols):
                if(self.mask[t[0]+u][t[1]+v] == 1): 
                    self.overlap_zone[t[0]+u][t[1]+v] = 1
                    if(first):
                        corner[0] = t[0]+u
                        corner[1] = t[1]+v
                        first = False
                    if(n == 0):
                        self.overlapRows += 1
                    n += 1

            if(n != 0 and n > self.overlapCols):
                self.overlapCols = n
            n = 0
        for u in range(corner[0]-1,corner[0]+self.overlapRows):
            for v in range(corner[1]-1,corner[1]+self.overlapCols):
                if(self.overlap_zone[u][v] == 1):
                    if(self.number_overlap([u,v]) >= 1):
                        if(self.number_masking([u,v]) >= 1):
                            self.overlap_zone[u][v] = 2
                        else:
                            self.overlap_zone[u][v] = 3
        return corner

    def change_seams(self,corner,mask_seam, patch_index):
        found = False
        #print(mask_seam.size)
        for i in range(self.overlapRows):
            for j in range(self.overlapCols):
                self.seams[corner[0]+i][corner[1]+j][0] = 0
                self.seams[corner[0]+i][corner[1]+j][1] = 1
                found = False
                mask_val = mask_seam[i][j]
                if(i < mask_seam.shape[0] - 1 and found == False):
                    if(mask_seam[i+1][j] != mask_val and mask_seam[i+1][j] != 0):
                        self.seams[corner[0]+i][corner[1]+j][1] = 2
                        if(mask_val == 2):
                            self.seams[corner[0]+i][corner[1]+j][0] = patch_index
                        elif(mask_val == 1 and self.seams[corner[0]+i][corner[1]+j][0] == 0):
                            self.seams[corner[0]+i][corner[1]+j][0] = 1
                        found = True
                if(j < mask_seam.shape[1] - 1 and found == False):
                    if(mask_seam[i][j+1] != mask_val and mask_seam[i][j+1] != 0):
                        if(self.seams[corner[0]+i][corner[1]+j][1] == 2):
                            self.seams[corner[0]+i][corner[1]+j][1] = 3
                        else:
                            self.seams[corner[0]+i][corner[1]+j][1] = 4
                        if(mask_val == 2):
                            self.seams[corner[0]+i][corner[1]+j][0] = patch_index
                        elif(mask_val == 1 and self.seams[corner[0]+i][corner[1]+j][0] == 0):
                            self.seams[corner[0]+i][corner[1]+j][0] = 1
                        found = True

    def patching_placement(self):
        
        patching = np.zeros((self.realRows,self.realCols),dtype = np.float)
        tk = np.zeros((self.realCols, self.patchRows, self.patchCols, 3),dtype = np.float)
        msk = np.zeros((self.realCols,self.patchRows, self.patchCols))
        si = np.zeros((self.realRows, self.realCols))
        for i in range(self.realRows):
            w1 = min(self.patchRows,self.realRows-i)
            #print(i)
            for j in range(self.realCols):
                w2 = min(self.patchCols,self.realCols-j)
                msk[j][:] = np.zeros((self.patchRows, self.patchCols))
                a1 = self.texture[0:w1,0:w2]
                a2 = self.old[i:i+w1,j:j+w2]
                #print(a1.shape,a2.shape,self.old.shape,w2,j+w2,self.realCols)
                tk[j][0:w1,0:w2] = ( a1 -a2 )
                msk[j][0:w1,0:w2] = self.mask[i:i+w1,j:j+w2]
                si[i][j] = w1 * w2
            #print(i)
            for k in range(3):
                patching[i] += np.sum( (tk[:,:,:,k]*msk ) ** 2,axis = (1,2))
        patching /= si
        #print(i)
        #print(patching)
        patching = np.exp(-patching/ (0.3 * self.variance) ).reshape(-1)
        patching /= np.sum(patching)
        l = int(np.random.choice( self.realRows * self.realCols ,1,p = patching))
        #print(l)
        t = [0,0]
        t[0] = int(l/int(self.realCols))
        t[1] = int(l - self.realCols * t[0])
        #print(t)
        return t

    def edge_cost_calculate(self,x_crt,y_crt,x_adj,y_adj,A,B):
        new_crt = B[x_crt][y_crt]
        old_crt = A[x_crt][y_crt]
        new_adj = B[x_adj][y_adj]
        old_adj = A[x_adj][y_adj]
        r = abs(old_crt[0]-new_crt[0])+abs(old_adj[0]-new_adj[0])
        g = abs(old_crt[1]-new_crt[1])+abs(old_adj[1]-new_adj[1])
        b = abs(old_crt[2]-new_crt[2])+abs(old_adj[2]-new_adj[2])
        return (r+g+b)/3

    

    def minCut_calculate(self,t):

        nb_pixels = [0]
        #print(t)
        self.new[t[0]:t[0]+self.patchRows,t[1]:t[1]+self.patchCols] = self.texture[0:self.patchRows,0:self.patchCols]
        overlap_corner = self.change_overlap(t)
        nb_pixels[0] = np.sum(self.mask[t[0]:t[0]+self.patchRows,t[1]:t[1]+self.patchCols])
        #print(nb_pixels,overlap_corner)
        g = nx.Graph()

        mask_seam = np.zeros((self.overlapRows, self.overlapCols ),dtype = np.int)
        num = 2
        seam_supp = 0
        mat_num = np.zeros((self.overlapRows, self.overlapCols ),dtype = np.int)

        for i in range(self.overlapRows):
            for j in range(self.overlapCols):
                if(self.mask[overlap_corner[0]+i][overlap_corner[1]+j]==1):
                    
                    mat_num[i][j] = num
                    #print(overlap_corner[0]+i,overlap_corner[1]+j,i,j,mat_num[i][j])
                    num += 1
        num = 2

        for i in range(self.overlapRows):
            for j in range(self.overlapCols):
                x_crt = overlap_corner[0]+i
                y_crt = overlap_corner[1]+j

                down = False
                right = False

                if(self.mask[x_crt][y_crt]== 1):

                    if(self.seams[x_crt][y_crt][0] != 0):
                        if(self.seams[x_crt][y_crt][1] == 2 or self.seams[x_crt][y_crt][1] == 3):
                            if(self.overlap_zone[x_crt][y_crt] == 1 and self.mask[x_crt+1][y_crt] == 1):
                                down = True
                                seam_supp += 1
                                #g.add_node()
                                
                                s_As = self.init_value_seams[x_crt][y_crt]
                                t_As = s_As + np.array([1,0])
                                t_At = self.init_value_seams[x_crt+1][y_crt]
                                s_At = t_At - np.array([1,0])

                                color1 = abs(self.texture[s_As[0]][s_As[1]][0]-self.texture[s_At[0]][s_At[1]][0])+abs(self.texture[t_As[0]][t_As[1]][0]-self.texture[t_At[0]][t_At[1]][0])
                                color2 = abs(self.texture[s_As[0]][s_As[1]][1]-self.texture[s_At[0]][s_At[1]][1])+abs(self.texture[t_As[0]][t_As[1]][1]-self.texture[t_At[0]][t_At[1]][1])
                                color3 = abs(self.texture[s_As[0]][s_As[1]][2]-self.texture[s_At[0]][s_At[1]][2])+abs(self.texture[t_As[0]][t_As[1]][2]-self.texture[t_At[0]][t_At[1]][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(0,nb_pixels[0]+1+seam_supp,capacity=cost)

                                color1 = abs(self.texture[s_As[0]][s_As[1]][0]-self.new[x_crt][y_crt][0])+abs(self.texture[t_As[0]][t_As[1]][0]-self.new[x_crt+1][y_crt][0])
                                color2 = abs(self.texture[s_As[0]][s_As[1]][1]-self.new[x_crt][y_crt][1])+abs(self.texture[t_As[0]][t_As[1]][1]-self.new[x_crt+1][y_crt][1])
                                color3 = abs(self.texture[s_As[0]][s_As[1]][2]-self.new[x_crt][y_crt][2])+abs(self.texture[t_As[0]][t_As[1]][2]-self.new[x_crt+1][y_crt][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(mat_num[i][j],nb_pixels[0]+1+seam_supp, capacity=cost)

                                color1 = abs(self.new[x_crt][y_crt][0]-self.texture[s_At[0]][s_At[1]][0])+abs(self.new[x_crt+1][y_crt][0]-self.texture[t_At[0]][t_At[1]][0])
                                color2 = abs(self.new[x_crt][y_crt][1]-self.texture[s_At[0]][s_At[1]][1])+abs(self.new[x_crt+1][y_crt][1]-self.texture[t_At[0]][t_At[1]][1])
                                color3 = abs(self.new[x_crt][y_crt][2]-self.texture[s_At[0]][s_At[1]][2])+abs(self.new[x_crt+1][y_crt][2]-self.texture[t_At[0]][t_At[1]][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(mat_num[i+1][j],nb_pixels[0]+1+seam_supp, capacity=cost)

                        if(self.seams[x_crt][y_crt][1] == 4 or self.seams[x_crt][y_crt][1] == 3):
                            if(self.overlap_zone[x_crt][y_crt] == 1 and self.mask[x_crt][y_crt+1] == 1):

                                right = True

                                seam_supp += 1
                                #g.add_node()

                                s_As = self.init_value_seams[x_crt][y_crt]
                                t_As = s_As + np.array([0,1])
                                t_At = self.init_value_seams[x_crt][y_crt+1]
                                s_At = t_At - np.array([0,1])

                                color1 = abs(self.texture[s_As[0]][s_As[1]][0]-self.texture[s_At[0]][s_At[1]][0])+abs(self.texture[t_As[0]][t_As[1]][0]-self.texture[t_At[0]][t_At[1]][0])
                                color2 = abs(self.texture[s_As[0]][s_As[1]][1]-self.texture[s_At[0]][s_At[1]][1])+abs(self.texture[t_As[0]][t_As[1]][1]-self.texture[t_At[0]][t_At[1]][1])
                                color3 = abs(self.texture[s_As[0]][s_As[1]][2]-self.texture[s_At[0]][s_At[1]][2])+abs(self.texture[t_As[0]][t_As[1]][2]-self.texture[t_At[0]][t_At[1]][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(nb_pixels[0]+1+seam_supp,1, capacity=cost)

                                color1 = abs(self.texture[s_As[0]][s_As[1]][0]-self.new[x_crt][y_crt][0])+abs(self.texture[t_As[0]][t_As[1]][0]-self.new[x_crt][y_crt+1][0])
                                color2 = abs(self.texture[s_As[0]][s_As[1]][1]-self.new[x_crt][y_crt][1])+abs(self.texture[t_As[0]][t_As[1]][1]-self.new[x_crt][y_crt+1][1])
                                color3 = abs(self.texture[s_As[0]][s_As[1]][2]-self.new[x_crt][y_crt][2])+abs(self.texture[t_As[0]][t_As[1]][2]-self.new[x_crt][y_crt+1][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(mat_num[i][j],nb_pixels[0]+1+seam_supp, capacity=cost)

                                color1 = abs(self.new[x_crt][y_crt][0]-self.texture[s_At[0]][s_At[1]][0])+abs(self.new[x_crt][y_crt+1][0]-self.texture[t_At[0]][t_At[1]][0])
                                color2 = abs(self.new[x_crt][y_crt][1]-self.texture[s_At[0]][s_At[1]][1])+abs(self.new[x_crt][y_crt+1][1]-self.texture[t_At[0]][t_At[1]][1])
                                color3 = abs(self.new[x_crt][y_crt][2]-self.texture[s_At[0]][s_At[1]][2])+abs(self.new[x_crt][y_crt+1][2]-self.texture[t_At[0]][t_At[1]][2])
                                cost = (color1+color2+color3)/3
                                g.add_edge(mat_num[i][j+1],nb_pixels[0]+1+seam_supp, capacity=cost)

                    if(i < self.overlapRows-1 and self.mask[x_crt+1][y_crt] == 1 and down == False ):
                        x_adj = x_crt + 1
                        y_adj = y_crt
                        #print(x_crt,x_adj,y_crt,y_adj, self.old[x_crt][y_crt],self.old[x_adj][y_adj],self.new[x_crt][y_crt],self.new[x_adj][y_adj],self.texture[x_crt-t[0]][y_crt-t[1]])
                        cost = self.edge_cost_calculate(x_crt,y_crt,x_adj,y_adj,self.old,self.new)
                        #print(cost)
                        g.add_edge(mat_num[i][j],mat_num[i+1][j],capacity=cost)

                    if(j < self.overlapCols-1 and self.mask[x_crt][y_crt+1] == 1 and right == False ):
                        x_adj = x_crt
                        y_adj = y_crt + 1
                        
                        cost = self.edge_cost_calculate(x_crt,y_crt,x_adj,y_adj,self.old,self.new)
                        g.add_edge(mat_num[i][j],mat_num[i][j+1],capacity=cost)

                    if(self.overlap_zone[x_crt][y_crt] == 2):
                        g.add_edge(mat_num[i][j],1,capacity=1<<20)
                    if(self.overlap_zone[x_crt][y_crt] == 3):
                        g.add_edge(0,mat_num[i][j],capacity=1<<20)
    
        krt, partition = nx.minimum_cut(g,0,1,flow_func = edmonds_karp)

        # Code for Intermediate
        left, right = partition
        cutset = set()
        for u, nbrs in ((n, g[n]) for n in left):
            cutset.update((u, v) for v in nbrs if v in right)
        print(sorted(cutset))
        temp_graph=nx.DiGraph()
        temp_graph.add_edges_from(cutset)
        nx.draw_networkx(temp_graph)
        #plt.show()

        file = open("cutarray.txt","a")
        file.write(str(cutset))
        file.close()

        adj_matrix = nx.adjacency_matrix(g)
        file = open("Adjacency Matrix.txt","a")
        file.write(str(adj_matrix))
        file.close()

        #print(krt, partition)
        l = [0 for i in range(g.number_of_nodes())]
        for i in partition[1]:
            l[i] = 1
        for i in range(self.overlapRows):
            for j in range(self.overlapCols):
                x_crt = overlap_corner[0] + i
                y_crt = overlap_corner[1] + j
                if(self.overlap_zone[x_crt][y_crt] != 0):
                    if( l[mat_num[i][j]] == l[0]):
                        self.new[x_crt][y_crt] = self.old[x_crt][y_crt]
                        mask_seam[i][j] = 1
                    else:
                        mask_seam[i][j] = 2
        #print(mask_seam.shape)
        self.change_seams(overlap_corner,mask_seam,self.index)
        self.change_seams_value(overlap_corner,t,mask_seam)

        self.old = deepcopy(self.new)
        self.change_masking(t)
        self.overlap_zone = np.zeros((self.imRows,self.imCols),dtype=np.int)
        self.index += 1
    
    def patching_func(self):
        self.initialize()
        x = random.randint( int(1*self.patchRows/3), int(2*self.patchRows/3))
        y = 0
        while(y < self.realCols):
            while(x < self.realRows):
                self.minCut_calculate([x,y])
                x += random.randint( int(1*self.patchRows/3), int(2*self.patchRows/3))
            y += random.randint( int(2*self.patchCols/3), int(2*self.patchCols/3))
            x = 0
        for i in range(5):
            #print(i)
            t = self.patching_placement()
            self.minCut_calculate(t)
        return self.new[0:self.realRows,0:self.realCols]


if __name__ == '__main__':

    img = imageio.imread(sys.argv[1])
    scale_percent = 70  # percent of original size
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

    a = np.array(img,dtype=np.int)[:,:,0:3]
    graphcut = GraphCut(a,int(sys.argv[3]),int(sys.argv[4]))

    result = graphcut.patching_func()
    rst = result.astype('uint8')
    imageio.imwrite(sys.argv[2],rst)