######################################################################
# File: L2G.py
# Author: Jacob Miller
# Description: This file contains functions to setup the L2G algorithm 
# and calls the cpython code to compute the layout. 
######################################################################
import graph_tool.all as gt
import numpy as np 

def L2G(G: gt.Graph, k: int, a=10,weights=None,alpha=0.6):
    """
    Perform setup and call optimization for L2g.
    G: The graph to draw
    k: The number of neighbors from each vertex to influence the layout
    a: The length of walks that influence the layout
    weights: n x n matrix of weights; higher values make pairs more influential. If none, is computed based on number of walks
    alpha: hyperparameter for repulsion force. A higher value indicates more repulsion.
    """
    from modules.cython_l2g import L2G_opt 
    from modules.metrics import apsp 
    d = apsp(G,weights)
    w = find_neighbors(G,k,a)
    return L2G_opt(d.astype("double"),w.astype(np.int16),alpha=alpha)

def sum_diag_powers(L,a):
    print(sum(L ** p for p in range(1,a+1)))

def norm_counts(A: np.array, p: int):
    s = 0.1
    B = np.linalg.matrix_power(A,p)
    B = pow(s,p) * B 
    return B / np.max(B)

def find_neighbors_large(G,k=25,a=10,eps=0):
    A = gt.adjacency(G).toarray()
    L,Q = np.linalg.eigh(A)
    Lp = sum(pow(L,p) for p in range(1,a+1))
    A = np.matmul(np.matmul(Q,np.diag(Lp)),Q.T)
    return A

def find_neighbors_small(G,k,a,eps):
    A = gt.adjacency(G).toarray()
    mp = np.linalg.matrix_power
    A = sum([norm_counts(A,i) for i in range(1,a+1)])
    return A

def find_neighbors(G,k=5,a=5,eps=0):
    """
    Computes the weight matrix based on the number of walks between vertices. 
    Further detail described in accompanying paper: https://arxiv.org/abs/2308.16403
    """
    if G.num_vertices() > 1000:
        A = find_neighbors_large(G,k,a,eps)
    else: A = find_neighbors_small(G,k,a,eps)

    B = np.argsort(A,axis=1)
    w = np.zeros(A.shape,dtype=np.int16)
    for i in range(len(A)):
        A_star = B[i][::-1][:k+1]
        for v in A_star:
            if A[i][v] == 0: break
            if i != v and v:
                w[i,v] = 1 
                w[v,i] = 1

    return w

def k_nearest(d,k=7):
    """
    Finds a weight matrix based on the k-nearest neighbors.
    """
    
    w = np.zeros_like(d)
    for i in range(w.shape[0]):
        ind = set( np.argsort(d[i])[1:k+1] )
        for j in ind: 
            w[i][j] = 1
            w[j][i] = 1 
    
    return w

def diffusion_weights(d,a=5, k = 20, sigma=1):
    """
    Finds a weight matrix based on information diffusion through the network.
    """

    #Transform distance matrix
    diff = np.exp( -(d**2) / (sigma **2) )
    diff /= np.sum(diff,axis=0)

    #Sum powers from 1 to a
    mp = np.linalg.matrix_power
    A = sum( pow(0.05,i) * mp(diff,i) for i in range(1,a+1) )

    #Find k largest points for each row 
    Neighbors = set()
    for i in range(diff.shape[0]):
        args = np.argsort(A[i])[::-1][1:k+1]
        for j in args:
            Neighbors.add( (int(i),int(j)) )

    #Set pairs to 1
    w = np.zeros_like(diff)
    for i,j in Neighbors:
        w[i,j] = 1
        w[j,i] = 1
    return w
