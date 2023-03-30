import time
from collections import OrderedDict
from options.train_options import TrainOptions
from data.data_loader import CreateDataLoader
from models.models import create_model
import util.util as util
import os
import numpy as np
import torch
from torch.autograd import Variable
#from tensorboardX import SummaryWriter
import cv2
#writer = SummaryWriter('runs/G1G2')
SIZE=320
NC=14
def generate_label_plain(inputs):
    size = inputs.size()
    pred_batch = []
    for input in inputs:
        input = input.view(1, NC, 256,192)
        pred = np.squeeze(input.data.max(1)[1].cpu().numpy(), axis=0)
        pred_batch.append(pred)

    pred_batch = np.array(pred_batch)
    pred_batch = torch.from_numpy(pred_batch)
    label_batch = pred_batch.view(size[0], 1, 256,192)

    return label_batch

def generate_label_color(inputs, opt):
    label_batch = []
    for i in range(len(inputs)):
        label_batch.append(util.tensor2label(inputs[i], opt.label_nc))
    label_batch = np.array(label_batch)
    label_batch = label_batch * 2 - 1
    input_label = torch.from_numpy(label_batch)

    return input_label
def complete_compose(img,mask,label):
    label=label.cpu().numpy()
    M_f=label>0
    M_f=M_f.astype(np.int)
    M_f=torch.FloatTensor(M_f).cuda()
    masked_img=img*(1-mask)
    M_c=(1-mask.cuda())*M_f
    M_c=M_c+torch.zeros(img.shape).cuda()##broadcasting
    return masked_img,M_c,M_f

def compose(label,mask,color_mask,edge,color,noise):
    # check=check>0
    # print(check)
    masked_label=label*(1-mask)
    masked_edge=mask*edge
    masked_color_strokes=mask*(1-color_mask)*color
    masked_noise=mask*noise
    return masked_label,masked_edge,masked_color_strokes,masked_noise
def changearm(old_label):
    label=old_label
    arm1=torch.FloatTensor((data['label'].cpu().numpy()==9).astype(np.int))
    arm2=torch.FloatTensor((data['label'].cpu().numpy()==10).astype(np.int))
    noise=torch.FloatTensor((data['label'].cpu().numpy()==7).astype(np.int))
    label=label*(1-arm1)+arm1*8
    label=label*(1-arm2)+arm2*8
    label=label*(1-noise)+noise*8
    return label


###=========================================================================================

def initialize_Model():
    os.makedirs('sample',exist_ok=True)
    opt = TrainOptions().parse()
    # iter_path = os.path.join(opt.checkpoints_dir, opt.name, 'iter.txt')
    # if opt.continue_train:
    #     try:
    #         start_epoch, epoch_iter = np.loadtxt(iter_path , delimiter=',', dtype=int)
    #     except:
    #         start_epoch, epoch_iter = 1, 0
    #     print('Resuming from epoch %d at iteration %d' % (start_epoch, epoch_iter))        
    # else:    
    #     start_epoch, epoch_iter = 1, 0

    if opt.debug:
        opt.display_freq = 1
        opt.print_freq = 1
        opt.niter = 1
        opt.niter_decay = 0
        opt.max_dataset_size = 10

    model = create_model(opt)
    return model, opt
    
    #import test_init

###=========================================================================================
    
    
def generate_result(model, opt):

    data_loader = CreateDataLoader(opt)
    dataset = data_loader.load_data()
    dataset_size = len(data_loader)

    save_fake = True
    
    for data in dataset:
        
        mask_clothes = torch.FloatTensor((data['label'].cpu().numpy() == 8).astype(np.int))
        mask_fore = torch.FloatTensor((data['label'].cpu().numpy() > 0).astype(np.int))
        img_fore = data['image'] * mask_fore
        img_fore_wc = img_fore * mask_fore
        all_clothes_label = changearm(data['label'])

        ############## Forward Pass ######################
        # 여기가 각 데이터 경로 입력+ inference하는 line
        losses, fake_image, real_image, input_label,L1_loss,style_loss,clothes_mask,CE_loss,rgb,alpha= model(Variable(data['label'].cuda()),Variable(data['edge'].cuda()),Variable(img_fore.cuda()),Variable(mask_clothes.cuda())
                                                                                                            ,Variable(data['color'].cuda()),Variable(all_clothes_label.cuda()),Variable(data['image'].cuda()),Variable(data['pose'].cuda()) ,Variable(data['image'].cuda()) ,Variable(mask_fore.cuda()))

        a = generate_label_color(generate_label_plain(input_label), opt).float().cuda()
        b = real_image.float().cuda()
        c = fake_image.float().cuda()
        d=torch.cat([clothes_mask,clothes_mask,clothes_mask],1)
        combine = torch.cat([a[0],d[0],b[0],c[0],rgb[0]], 2).squeeze()
        # combine=c[0].squeeze()
        cv_img=(combine.permute(1,2,0).detach().cpu().numpy()+1)/2

        
        # import를 하면 import를 한 위치를 기준으로 현재 디렉토리가 결정된다.
        rgb=(cv_img*255).astype(np.uint8)            
        bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
        # n=str(step)+'.jpg'            
        cv2.imwrite('static/result/'+data['name'][0],bgr)
        
        #이것이 합성 이미지
        #return rgb
    
###=========================================================================================    
