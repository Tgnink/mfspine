

import matplotlib.pyplot as plt
import numpy as np
import torch
from skimage.filters.thresholding import (threshold_isodata, threshold_li,
                                          threshold_local, threshold_mean,
                                          threshold_minimum,
                                          threshold_multiotsu,
                                          threshold_niblack, threshold_otsu,
                                          threshold_triangle, threshold_yen)
from skimage.io import imread
from skimage.util import montage
from skimage.util.shape import view_as_blocks, view_as_windows
from torch.utils.data import DataLoader

from train.dataset.dataloader import  OrigionDatasetUnet2D

from train.trainers.trainer import Trainer
from train.networks import unetplusplus
from train.trainers.device import set_use_gpu
import matplotlib
import colorsys
import os
from glob import glob

import colorcet as cc
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.widgets import MultiCursor

from spinelib.seg import unetseg
from utils import file_base
from utils.basic_wrap import Logger, logit
from utils.file_base import file_list
# from PIL import Image
# from skimage.segmentation import watershed,morphological_chan_vese
from utils.yaml_config import YAMLConfig

from train.networks import get_network


# from torchsummary import summary
def showims(*ims,**kwargs):
    labels=kwargs.get("labels",None)
    fig,axes=plt.subplots(1,len(ims),sharex=True,sharey=True)
    # print(im1.shape)
    for i,im in enumerate(ims):
        #print(im.shape)
        np.dtype
        if  "int" in im.dtype.__repr__() and len(np.unique(im))<900:
            cmap=LinearSegmentedColormap.from_list("isolum",cc.glasbey)
            axes[i].imshow(im,interpolation='none',cmap=cmap)
        else:
            axes[i].imshow(im,interpolation='none',cmap="gray")
        if i < len(labels):
            axes[i].set_title(labels[i])
    # axes[1].imshow(im2,interpolation='none')
    # axes[2].imshow(im3,interpolation='none')
    multi = MultiCursor(fig.canvas, axes, color='r', lw=1, horizOn=True, vertOn=True)
    plt.show()
class Predict():
    def setting(self, configuration: YAMLConfig = None,use_gpu=True):

        if configuration == None:
            self.configuration = configuration
            return

        self.configuration = configuration

        dict_a = self.configuration.config["Path"]
        dict_b = self.configuration.config["Training"]
        dict_c = self.configuration.config["Data"]

        self.__dict__.update(dict_a)
        self.__dict__.update(dict_b)
        self.__dict__.update(dict_c)
        self.ori_path=os.path.abspath(self.ori_path)
        if "z" in self.axes:
            self.imgshape = (self.input_sizez, self.input_sizexy,
                             self.input_sizexy,1)
        else:
            self.imgshape = (self.input_sizexy, self.input_sizexy,1)
       
        self.logger=Logger(os.path.join(os.path.abspath(self.log_path),"train_info.log"))
    
        self.initial_gpu(use_gpu)
        self.inital_model()
        self.initial_allfunc()
        
    def initial_gpu(self,use_gpu):
        device,ngpu,ncpu=set_use_gpu(use_gpu)
        self.use_gpu=use_gpu
        self.device=device
        self.ngpu=ngpu
        self.ncpu=ncpu    
               
    def load_weight(self,denovo,premodel):
        #-----------------------#
        #   Load model weights  #
        #-----------------------#
        if denovo is False:
            checkpoint_save_path = premodel
            # 模型参数保存路径
            if not checkpoint_save_path:
                # find neweat weight file
                paths=file_base.file_list_bytime(self.model_path,".pth")
                checkpoint_save_path=paths[-1] if paths else ""   
            if checkpoint_save_path and os.path.exists(checkpoint_save_path):
                state = torch.load(checkpoint_save_path)
                self.model.load_state_dict(state["model"])
                #self.start_epoch=state["epoch"]
                #self.history.datas=state["history"]
                self.model.eval()
                self.logger.logger.info(
                    "\n==============LOAD PRETRAINED model==============\n"+
                    checkpoint_save_path+
                    "\n=================================================\n"
                )
    def initial_allfunc(self):
        pass
        # #--- INSTANCE---#
        # iname=self.instance["name"]
        # ikwargs=self.instance["kwargs"]
        # self.ins=get_instancefunc(iname,ikwargs)
    def inital_model(self):
        network_type = self.Network["name"]
        netkwarg=self.Network["kwargs"]
        #num_classes=self.num_classes
        # add_num=0
        # if "dis" in self.save_suffix:
        #     add_num=1
        # if "unet2d" == network_type:
        #     self.model =UNet2d(num_classes+add_num,1)
        # elif "unet++"==network_type:
        #     self.model=NestedUNet(num_classes+add_num,1)
        self.model=get_network(network_type,netkwarg)
       # self.model.load_network_set(self.network_info)
        self.model.to(self.device)
        #summary(self.model,(1,self.input_sizexy,self.input_sizexy))
        # self.show_train_info()
        
        # self.initial_loss()
    def test_epoch(self,valid_dataloader,model):

        # switch to evaluate mode
        model.eval()
        with torch.no_grad():
            
            
            for image, label in valid_dataloader:
                image = image.to(self.device)
                label = label.to(self.device)
                image=image.squeeze()
                # compute output
                # self.model.predict_2d_img(image)
                mask,spineprs,denprs,bgprs=unetseg.predict_single_img(self.model,image)
                #output = model(image)[0]#.cpu().data.numpy()
                #print(image.shape)
           
                showims(image.squeeze(),label[0,0],bgprs,denprs,spineprs,mask)



    
    @logit("error.log")
    def predict(self,premodel="",data=None):
        """_summary_

        Args:
            premodel (str, optional): _description_. Defaults to "".
            data (_type_, optional): Data None: use test folder, show and compare result ;Data folder/imagefile, show predict reshult. Defaults to None.

        Raises:
            Exception: _description_
        """
        if self.configuration is None:
            raise Exception('Please set Yaml configuration first!')
        #-----------------------#
        #  config load  #
        #-----------------------#
        ori_path=self.ori_path
        suffix=self.save_suffix # seg,spine,den
        num_classes=self.num_class
        log_dir=self.log_path
        model=self.model
        train_trainform=None#get_train_tranform()
        self.load_weight(False,premodel)
        if data is None:
            #self.enhance_border=True if "border" in self.save_suffix else False
            test_datast=OrigionDatasetUnet2D(ori_path + "/test",suffix,num_classes,iteration=0,des="test",transform=train_trainform)
            test_dataloader = DataLoader(test_datast,batch_size = 1,shuffle=False)
            self.test_epoch(test_dataloader,model)
        elif isinstance(data,list) and os.path.isdir(data[0]): # img folder, lab folder 
            
            imgfiles = glob(data[0]+'/*.tif')
            labelfiles = glob(data[1]+'/*.tif')
            pairs=file_base.pair_files(imgfiles,labelfiles,suffix=data[2])
            for img,lab in pairs:
                # print(img)
                lab=imread(lab)
                img=imread(img)
                
                ypred=model.predict_2d_img(img)
                showims(img,lab,ypred[0],ypred[1],ypred[2])
        elif isinstance(data,list) and os.path.isfile(data[0]): #imgfile list
            for im in data:
                #lab=imread(data[1])
                img=imread(im).astype("float32")
                ypred=model.predict_2d_img(img)
                showims(img,lab,ypred[0],ypred[1],ypred[2])
        elif os.path.isdir(data): # img dir
            imgfiles = glob(data+'/*.tif')
           
            for img in imgfiles:
                print(img)
               
                img=imread(img).astype("float32")
                ypred=model.predict_2d_img(img)
                showims(img,ypred[0],ypred[1],ypred[2])
        else: # filename
            img=imread(data).astype("float32")
            # self.ins.device="cpu"
            ins,prob,mask=model.off_predict(img)
            # ypred=model.predict_2d_img(img)
            # from spinelib.seg import unetseg
            # if "dis" in self.save_suffix:
                
            #     spine_label=unetseg.instance_unetmask_by_dis(model,img,th=0.15,spinesize_range=[4,800])
            # else:
            #     mask,spinepr,denpr,bgpr=unetseg.predict_single_img(model,img)
            #     if model.out_layer=="sigmoid":
            #         spine_label=unetseg.instance_unetmask_by_border(spinepr,mask==2,bgpr=bgpr,th=0.009,spinesize_range=[4,800])
            #     else:
            #         spine_label=unetseg.instance_unetmask_bypeak(spinepr,mask,searchbox=[15,15],min_radius=5,spinesize_range=[4,800])
            
            # showims(img,ypred[0],ypred[1],ypred[2],spine_label)
            showims(img,ins,mask,labels=["img","ins","mask"])
            
        
def showtwo(im1,im2):
    fig,axes=plt.subplots(1,2,sharex=True,sharey=True)
    print(im1.shape)
    axes[0].imshow(im1)
    axes[1].imshow(im2)
    plt.show()

def split_patches(img,cropsize):
    imgpad=np.pad(img,[(0,s%c) for s,c in zip(img.shape,cropsize)])
    splitshape=[s//c for s,c in zip(imgpad.shape,cropsize)]
    B = view_as_blocks(imgpad, cropsize)
    print(B.shape)
    B=B.reshape(-1,*cropsize)
    return B,splitshape
def merge_patches(B,splitshape):
    arr_out = montage(B,grid_shape=splitshape)
    return arr_out
def predict_dir(modelpath=r"D:\spine\spinesoftware\myspine\models\M2d_den\modelep010-loss0.023.h5"):
    hsv_tuples = [(x / num_classes, 1., 1.) for x in range(num_classes)]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))
    model=unet.UNet2D()
    model.build(input_shape =(4,256,256,1))
    model.load_weights(modelpath)

    imgdir=r"C:\Users\ZLY\Desktop\Train\4D\deconvole_2D_one"


        
    imglist=file_list(imgdir)
    for imgf in imglist:
        print(imgf)
        img=imread(imgf)
        imgs,splitshape=split_patches(img,cropsize=(256,256))
        imgsn=[]
        for im in imgs:
            im=im.reshape(1,256,256,1).astype(np.float32)
            ppr=model.predict(im)[0]
            pr = ppr.argmax(axis=-1)
            imgsn.append(pr)
        imgn=merge_patches(imgsn,splitshape)
        imgn=imgn[0:img.shape[0],0:img.shape[1]]


        # res=np.max(out,axis=-1)
        showtwo(img,imgn)
    # print(out)
def predict_movie(imgf=r"D:\spine\Train\4D\deconvolve_2D\MAX_decon_20211111-24D.tif",
          modelpath=r"D:/spine/spinesoftware/myspine/models/M2d_den\modelep008-loss0.013.h5"):
    imgs=imread(imgf)
    model=unet.UNet2D()

    model.build(input_shape =(4,512,512,1))
    model.load_weights(modelpath)
    print("img shape : ",imgs.shape)
    imgns=[]
    for img in imgs:
        img=img.reshape(1,512,512,1).astype(np.float32)
        print(img.shape)
        ppr=model.predict(img)[0]
        pr = ppr.argmax(axis=-1)
        imgn = ppr.argmax(axis=-1)
        # imgss,splitshape=split_patches(img,cropsize=(256,256))
        # imgsn=[]
        # for im in imgss:
        #     im=im.reshape(1,256,256,1).astype(np.float32)
        #     ppr=model.predict(im)[0]
        #     pr = ppr.argmax(axis=-1)
        #     imgsn.append(pr)
        # imgn=merge_patches(imgsn,splitshape)
        # imgn=imgn[0:img.shape[0],0:img.shape[1]]
        imgns.append(imgn)
    return imgns,imgs
def predict_4D(imgf=r"D:\data\Train\4D\deconvolve_4D\decon_20211111-24D.tif",
          modelpath=r"D:/spine/spinesoftware/myspine/models/M2d_seg\modelep104-loss0.047.h5"):
    imgss=imread(imgf)[:1]
    adth=imgss[0]>threshold_otsu(imgss[0])
    # adth=morphological_chan_vese(imgss[0],20,adth,1,1,2)
    model=unet.UNet2D()

    model.build(input_shape =(4,512,512,1))
    model.load_weights(modelpath)
    print("img shape : ",imgss.shape)
    imgnss=[]
    for imgs in imgss:
        
        imgns=[]
        prs=[]
        for img in imgs:
            img=img.reshape(1,512,512,1).astype(np.float32)
            ppr=model.predict(img)[0]
            imgn = ppr.argmax(axis=-1)
            prs.append(ppr[...,2])
            
            # imgss,splitshape=split_patches(img,cropsize=(256,256))
            # imgsn=[]
            # for im in imgss:
            #     im=im.reshape(1,256,256,1).astype(np.float32)
            #     ppr=model.predict(im)[0]
            #     pr = ppr.argmax(axis=-1)
            #     imgsn.append(pr)
            # imgn=merge_patches(imgsn,splitshape)
            # imgn=imgn[0:img.shape[0],0:img.shape[1]]
            imgns.append(imgn)
        imgns=np.array(imgns)
        mask=np.max(imgs,axis=0)[None,...]
        mask=mask.reshape(1,512,512,1).astype(np.float32)
        ppr=model.predict(mask)[0]
        mask = ppr.argmax(axis=-1)==1
        mask=np.tile(mask,(imgns.shape[0],1,1))
        imgns[(imgns==2)*mask]=0
    imgnss.append(imgns)    
    return imgnss,imgss,prs,adth,mask
# a,b,c,d,e=predict_4D()
# viewer=napari.Viewer()
# viewer.add_image(np.array(b))
# viewer.add_image(np.array(c))
# viewer.add_image(np.array(e))
# viewer.add_image(np.array(d*a))
# viewer.add_labels(np.array(a))
# napari.run()
# from utils import yaml_config
# configfile=r"config\defalut_2d_seg.yaml"
# predictmodel = Predict()
# default_configuration=yaml_config.YAMLConfig(
#         configfile
#         )
# predictmodel.setting(default_configuration,use_gpu=False)
# # predictmodel.load_weight(False,"premodel")