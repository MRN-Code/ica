import numpy as np
## Global constants
eps = 1e-18
MAX_W = 1e8
anneal = 0.9
MAX_STEP = 500
MIN_LRATE = 1e-6
W_STOP = 1e-6
## Common functions
def PCAwhiten(X,Ncomp, verbose = False):
    """ data Whitening 
    *Input 
    X : 2d data matrix of observations by variables
    Ncomp: Number of components to retain 
    *Output 
    Xwhite : Whitened X
    white : whitening matrix (Xwhite = np.dot(white,X))
    dewhite : dewhitening matrix (X = np.dot(dewhite,Xwhite))
    """
    u, s, v = np.linalg.svd(X,full_matrices=False)
    if verbose: 
        print("PCA whitening: %.2f%% retained variance"%(100*(sum(s[:Ncomp])/sum(s))))
    u = u[:,:Ncomp]
    v = v[:Ncomp,:]
    s = s[:Ncomp]
    white   = np.dot(np.diag((s+eps)**(-1)),u.T)
    dewhite = np.dot(u,np.diag(s))
    Xwhite = v
    return (Xwhite,white,dewhite)

def indUpdate(W1,Xwhite1,bias1,lrate1, startW1):
    """ Update rule for infomax
    This function recieves parameters to update W1 
    * Input 
    W1: square mixing matrix
    Xwhite1: whitened data
    bias1: current estimated bias
    lrate1: current learning rate
    startW1: in case update blows up it will start again from startW1
    * Output
    W1: updated mixing matrix
    bias: updated bias
    error1: flag to indicate if any error occurred while upating
    lrate1: updated learning rate
    """
    Nvox1 = Xwhite1.shape[1]
    Ncomp1 = Xwhite1.shape[0]
    block1 = int(np.floor(np.sqrt(Nvox1/3)))
    Ib1 = np.ones((1,block1))
    I1 = np.eye(Ncomp1)
    error1 = 0
    permute1 = np.random.permutation(Nvox1)
    for tt in range(0,Nvox1,block1):
        if(tt+block1<Nvox1):
            tt2 = tt+block1
        else:
            tt2 = Nvox1
            block1 = Nvox1 -tt
                
        U1 = np.dot(W1,Xwhite1[:,permute1[tt:tt2]]) +\
             np.dot(bias1, Ib1[:,0:block1])
        Y1 = 1/(1+np.exp(-U1))
        W1 = W1 + lrate1*np.dot(block1*I1 + \
                                np.dot(1-2*Y1, U1.T), W1)
        bias1 = (bias1.T + lrate1*(1-2*Y1).sum(axis=1)).T
        # Checking if W blows up
        if np.isnan(np.sum(W1)) or np.max(np.abs(W1))>MAX_W:
            print "Numeric error! restarting with lower learning rate"
            error1=1
            lrate1 = lrate1 * anneal
            W1 = startW1
            bias1 = np.zeros((Ncomp1,1))
            
            if lrate1 > 1e-6 and \
               np.linalg.matrix_rank(Xwhite1)<Ncomp1:
                print("Data 1 is rank defficient"
                      ". I cannot compute "+
                      str(Ncomp1)+ " components.")
                return (np.nan)
                
            if lrate1 < 1e-6:
                print("Weight matrix may"
                      " not be invertible...")
                return (np.nan)
            break
        
    return(W1,bias1,error1,lrate1) 


# infomax1: single modality infomax
def infomax1(Xwhite, verbose = False):
    "Computes ICA infomax in whitened data"
    Ncomp = Xwhite.shape[0]
    # Initialization
    W = np.eye(Ncomp)
    startW = W
    oldW = startW
    lrate = 0.005/np.log(Ncomp)
    bias = np.zeros((Ncomp,1))
    if(verbose):
        print("Beginning ICA training...")
    step=1
    
    while (step<MAX_STEP):

        (W,bias,error,lrate) = indUpdate(W,Xwhite,bias,lrate,startW)
        if error==0:
            
            wtchange = W - oldW
            oldW = W
            change = np.sum(wtchange**2)
            
            if step == 1:    # initializing variables
                oldwtchange = wtchange
                oldchange = change
            
            if step>2:
                angleDelta = np.arccos(np.sum(oldwtchange*wtchange)/(np.sqrt(change*oldchange)+eps))
                angleDelta = angleDelta*180/np.pi
                if angleDelta >60:
                    lrate = lrate*anneal
                    oldwtchange = wtchange
                    oldchange = change
                if (verbose and step%10==0) or change<W_STOP:
                    print("Step %d: Lrate %.1e," 
                          "Wchange %.1e,"
                          "Angle %.2f"%(step,lrate,
                                       change,angleDelta))
                    
            # Stopping rule
            if step>2 and change<W_STOP:
                step = MAX_STEP

            step = step+1
        else:
            step = 1
    
    A = np.linalg.pinv(W)
    S = np.dot(W,Xwhite)
                
    return (A, S, W)


## Single modality ICA               
def ica1(X,Ncomp, verbose = True):
    if verbose: print("Whitening data...")
    Xwhite, white, dewhite  = PCAwhiten(X,Ncomp)
    if verbose: print("Done.")
    if verbose: print("Running INFOMAX-ICA ...")
    A, S, W = infomax1(Xwhite,verbose)
    A =  np.dot(dewhite,A)
    if verbose: print("Done.")
    return (A, S)
    

