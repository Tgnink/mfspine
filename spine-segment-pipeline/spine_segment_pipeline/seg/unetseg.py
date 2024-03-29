
import numpy as np

from tqdm import tqdm
from ..cflow.blob import find_spheres, peakfilter, sphere_log
from . import segment
from skimage.morphology import remove_small_objects
from skimage.segmentation import watershed
from torchvision.transforms import ToTensor
from . import seg_base
def predict_2d_img(model,img):
    image=img.astype("float32")
    im=ToTensor()(image)#C H W
    # im=im.expand(1,256,256,1)
    im=im.unsqueeze(1)
    ypred=model.forward(im)
    return ypred[0].cpu().detach().numpy() 

def predict_single_img(model,img):
    """
    imgs: shape (x,y,c=1,None)
            shape(z,x,y,c=1,None)
    """

    cm=2**4
    ndim=img.ndim
    shape=img.shape
    padd=[(0,(cm-s%cm)%cm) for s in img.shape]
    if ndim==3:
        padd[0]=(0,0)
    img=np.pad(img,padd)
    # img=np.expand_dims(img,axis=-1).astype(np.float32)
    if ndim==2:#  H W
        img=np.expand_dims(img,axis=0).astype(np.float32) # to Z=1, H W
    imgns=[]
    spineprs=[]
    denprs=[]
    bgprs=[]
    # print(img.shape)
    for im in img:
        ypred=predict_2d_img(model,im) #soft max,sigmoid
        im=np.expand_dims(im,axis=0).astype(np.float32)
        #ypred=ypred
        mask = np.argmax(ypred, axis=0)
        spineprs.append(ypred[2])
        denprs.append(ypred[1])
        bgprs.append(ypred[0])
        imgns.append(mask)
    imgns=np.array(imgns) # label 0 1 2 mask
    imgns=np.squeeze(imgns)
    spineprs=np.array(spineprs)
    spineprs=np.squeeze(spineprs)
    denprs=np.array(denprs)
    denprs=np.squeeze(denprs)
    bgprs=np.array(bgprs)
    bgprs=np.squeeze(bgprs)
    # print(shape,imgns.shape)
    
    obj=[slice(0,s) for s in shape ]
    #print(imgns.shape,spineprs.shape,denprs.shape,obj)
    obj=tuple(obj)
    return imgns[obj],spineprs[obj],denprs[obj],bgprs[obj]
      

        
    

def predict_time_imgs(self,imgs): # T [Z] H W
    # print("img shape : ",img.shape)
    masks=[]
    spine_prs=[]
    den_prs=[]
    n_frames=imgs.shape[0]
    for i in tqdm(range(n_frames), desc='Processing'):
        img=imgs[i]
        mask,spineprs,denprs=predict_single_img(img)
        masks.append(mask)
        spine_prs.append(spineprs)
        den_prs.append(denprs)
    masks=np.array(masks)
    masks=np.squeeze(masks)    
    spine_prs=np.array(spine_prs)
    spine_prs=np.squeeze(spine_prs) 
    den_prs=np.array(den_prs)
    den_prs=np.squeeze(den_prs) 
    return masks,spine_prs,den_prs

def instance_unetmask_bypeak(spinepr,mask,searchbox,min_radius,spinesize_range=[4,800]):
    #outlayer:softmax
    #searchbox 2d,3d [25,25],[5,25,25]
    min_radius=int(min_radius)
    min_radius=min_radius if min_radius>1 else 3
    pr_corner=peakfilter(spinepr,min_radius,0,use_gaussian=True)*(mask)#*adth
    minspinesize,maxspinesize=spinesize_range
    spine_label=segment.label_instance_water(spinepr,pr_corner,mask, 
                                maxspinesize,searchbox=searchbox)


    spine_label=remove_small_objects(spine_label,min_size=minspinesize)
    return spine_label

def instance_unetmask_by_border(spinepr,mask,maskseed,spinesize_range=[4,800]):
    #outlayer sigmoid
    minspinesize,maxspinesize=spinesize_range
    mask2=mask & maskseed
    labels,num=seg_base.ndilable(mask2,2)
    labels=remove_small_objects(labels,minspinesize)
    
    spine_label=watershed(-spinepr,labels,mask=mask,connectivity=2)
    labels2=mask>spine_label
    labels2,num2=seg_base.ndilable(labels2,num+1)
    
    
    spine_label=remove_small_objects(spine_label,min_size=minspinesize)
    return spine_label+labels2