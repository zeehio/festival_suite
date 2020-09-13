"""Trainining script for Tacotron speech synthesis model.

usage: train.py [options]

options:
    --conf=<json>             Path of configuration file (json).
    --gpu-id=<N>               ID of the GPU to use [default: 0]
    --exp-dir=<dir>           Experiment directory
    --checkpoint-dir=<dir>    Directory where to save model checkpoints [default: checkpoints].
    --checkpoint-path=<name>  Restore model from checkpoint path if given.
    --hparams=<parmas>        Hyper parameters [default: ].
    --log-event-path=<dir>    Log Path [default: exp/log_tacotronOne]
    -h, --help                Show this help message and exit
"""
import os, sys
from docopt import docopt
args = docopt(__doc__)
print("Command line args:\n", args)
gpu_id = args['--gpu-id']
print("Using GPU ", gpu_id)
os.environ["CUDA_VISIBLE_DEVICES"]=gpu_id
import copy

from collections import defaultdict

### This is not supposed to be hardcoded #####
FALCON_DIR = os.environ.get('FALCONDIR')
sys.path.append(FALCON_DIR)
##############################################
from utils.misc import *
from utils import audio
from utils.plot import plot_alignment
from tqdm import tqdm, trange
from util import *
from model import TacotronOneSeqwiseMultispeaker as Tacotron
from model import sgd_maml

import json

import torch
from torch.utils import data as data_utils
from torch.autograd import Variable
from torch import nn
from torch import optim
import torch.backends.cudnn as cudnn
from torch.utils import data as data_utils
import numpy as np

from torch import autograd
#from torchsummary import summary

from os.path import join, expanduser

import tensorboard_logger
from tensorboard_logger import *
from hyperparameters import hparams, hparams_debug_string

vox_dir ='vox'

global_step = 0
global_epoch = 0
use_cuda = torch.cuda.is_available()
if use_cuda:
    cudnn.benchmark = False
use_multigpu = None

fs = hparams.sample_rate



def phi_eval(loader, model):
    criterion = nn.L1Loss()
    linear_dim = model.linear_dim
    for (x, spk, input_lengths, mel, y) in loader:

            # Sort by length
            sorted_lengths, indices = torch.sort(
                input_lengths.view(-1), dim=0, descending=True)
            sorted_lengths = sorted_lengths.long().numpy()
        
            x, spk, mel, y = x[indices], spk[indices], mel[indices], y[indices]

            # Feed data
            x, spk, mel, y = Variable(x), Variable(spk), Variable(mel), Variable(y)
            if use_cuda:
                x, spk, mel, y = x.cuda(), spk.cuda(), mel.cuda(), y.cuda()
             
            mel_outputs, linear_outputs, attn = model(x, spk, mel, input_lengths=sorted_lengths)

            # Loss
            mel_loss = criterion(mel_outputs, mel)
            n_priority_freq = int(3000 / (fs * 0.5) * linear_dim)
            linear_loss = 0.5 * criterion(linear_outputs, y) \
                + 0.5 * criterion(linear_outputs[:, :, :n_priority_freq],
                                  y[:, :, :n_priority_freq])
            loss = mel_loss + linear_loss

            # You prolly should not return here
            return loss 


def train(model, model_copy, theta_loader, phi_loader, optimizer, optimizer_maml,
          init_lr=0.002,
          checkpoint_dir=None, checkpoint_interval=None, nepochs=None,
          clip_thresh=1.0):
    model.train()
    if use_cuda:
        model = model.cuda()
    linear_dim = model.linear_dim

    criterion = nn.L1Loss()

    global global_step, global_epoch
    while global_epoch < nepochs:
        h = open(logfile_name, 'a')
        running_loss = 0.
        for step, (x, spk, input_lengths, mel, y) in tqdm(enumerate(theta_loader)):
          #print("At update number ", step)       
          #with autograd.detect_anomaly(): 
          
            # Decay learning rate
            current_lr = learning_rate_decay(init_lr, global_step)
            for param_group in optimizer.param_groups:
                param_group['lr'] = current_lr

            model_clone = copy.deepcopy(model)
            optimizer_maml = optim.SGD(params = model_clone.parameters(), lr=0.01)
            optimizer_maml.zero_grad()
            optimizer.zero_grad()

            # Sort by length
            sorted_lengths, indices = torch.sort(
                input_lengths.view(-1), dim=0, descending=True)
            sorted_lengths = sorted_lengths.long().numpy()

            x, spk, mel, y = x[indices], spk[indices], mel[indices], y[indices]

            # Feed data
            x, spk, mel, y = Variable(x), Variable(spk), Variable(mel), Variable(y)
            if use_cuda:
                x, spk, mel, y = x.cuda(), spk.cuda(), mel.cuda(), y.cuda()

            # Multi GPU Configuration
            if use_multigpu:
               outputs,  r_, o_ = data_parallel_workaround(model, (x, mel))
               mel_outputs, linear_outputs, attn = outputs[0], outputs[1], outputs[2]
 
            else:
                mel_outputs, linear_outputs, attn = model(x, spk, mel, input_lengths=sorted_lengths)

            # Loss
            mel_loss = criterion(mel_outputs, mel)
            n_priority_freq = int(3000 / (fs * 0.5) * linear_dim)
            linear_loss = 0.5 * criterion(linear_outputs, y) \
                + 0.5 * criterion(linear_outputs[:, :, :n_priority_freq],
                                  y[:, :, :n_priority_freq])
            loss = mel_loss + linear_loss

            if global_step > 0 and global_step % hparams.save_states_interval == 0:
                save_states(
                    global_step, mel_outputs, linear_outputs, attn, y,
                    None, checkpoint_dir)
                #visualize_phone_embeddings(model, checkpoint_dir, global_step)

            if global_step > 0 and global_step % checkpoint_interval == 0:
                save_checkpoint(
                    model, optimizer, global_step, checkpoint_dir, global_epoch)

            # Update
            #grad = torch.autograd.grad(loss, model.parameters())
            #fast_weights = list(map(lambda p: p[1] - current_lr * p[0], zip(grad, model.parameters())))
            #print(fast_weights)
            #sys.exit()
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(
                 model.parameters(), clip_thresh)
            optimizer_maml.step()
            
            #fast_weights = optimizer_maml.step_maml()
            #for (fwg, mg) in list(zip(fast_weights, model.parameters())):
            #    for (fwp, mp) in list(zip(fwg, mg)):
                    #print("FWP: ", fwp.shape)
                    #print("MP: ", mp.shape) 
            #        assert mp.shape == fwp.shape
            #        mp.data = fwp.data 
            #for i in range(len(fast_weights_params)):
            #    model_copy[i].data[:] = fast_weights_params[i].data[:]
            #print("Copied the model")
            #sys.exit()

            optimizer.zero_grad()
            model.last_linear = model_clone.last_linear
            phi_loss = phi_eval(phi_loader, model_clone)
            phi_loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(
                 model.parameters(), clip_thresh)
            optimizer.step()

            # Logs
            log_value("loss", float(loss.item()), global_step)
            log_value("mel loss", float(mel_loss.item()), global_step)
            log_value("linear loss", float(linear_loss.item()), global_step)
            log_value("gradient norm", grad_norm, global_step)
            log_value("learning rate", current_lr, global_step)
            log_histogram("Last Linear Weights", model.last_linear.weight.detach().cpu(), global_step)
            global_step += 1
            running_loss += loss.item()

        averaged_loss = running_loss / (len(theta_loader))
        log_value("loss (per epoch)", averaged_loss, global_epoch)
        h.write("Loss after epoch " + str(global_epoch) + ': '  + format(running_loss / (len(theta_loader))) + '\n')
        h.close() 
        #sys.exit()

        global_epoch += 1


if __name__ == "__main__":

    exp_dir = args["--exp-dir"]
    checkpoint_dir = args["--exp-dir"] + '/checkpoints'
    checkpoint_path = args["--checkpoint-path"]
    log_path = args["--exp-dir"] + '/tracking'
    conf = args["--conf"]
    hparams.parse(args["--hparams"])

    # Override hyper parameters
    if conf is not None:
        with open(conf) as f:
            hparams.parse_json(f.read())

    os.makedirs(exp_dir, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)
    os.makedirs(log_path, exist_ok=True)
    logfile_name = log_path + '/logfile'
    h = open(logfile_name, 'w')
    h.close()

    # Vocab size
    with open(vox_dir + '/' + 'etc/ids_phones.json') as  f:
       ph_ids = json.load(f)

    with open(vox_dir + '/' + 'etc/ids_speakers.json') as  f:
       spk_ids = json.load(f)

    ph_ids = dict(ph_ids)
    spk_ids = dict(spk_ids)


    phidsdict_file = checkpoint_dir + '/ids_phones.json'
    with open(phidsdict_file, 'w') as outfile:
       json.dump(ph_ids, outfile)

    spkidsdict_file = checkpoint_dir + '/ids_speakers.json'
    with open(spkidsdict_file, 'w') as outfile:
       json.dump(spk_ids, outfile)


    # fnames_file, desc_file, feat_name, feats_dict=None, spk_dict=None
    feats_name = 'phones'
    theta_X_train = categorical_datasource( fnames_file = vox_dir + '/' + 'fnames.train.awb', 
                                      desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                                      feat_name = feats_name, 
                                      feats_dict = ph_ids)
    phi_X_train = categorical_datasource( fnames_file = vox_dir + '/' + 'fnames.train.rms', 
                                      desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                                      feat_name = feats_name, 
                                      feats_dict = ph_ids)


    feats_name = 'speaker'
    theta_spk_train = categorical_datasource( fnames_file = vox_dir + '/' + 'fnames.train.awb', 
                                      desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                                      feat_name = feats_name, 
                                      feats_dict = ph_ids,
                                      spk_dict = spk_ids)
    phi_spk_train = categorical_datasource( fnames_file = vox_dir + '/' + 'fnames.train.rms', 
                                      desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                                      feat_name = feats_name, 
                                      feats_dict = ph_ids,
                                      spk_dict = spk_ids)


    # fnames_file, desc_file, feat_name
    feats_name = 'lspec'
    theta_Y_train = float_datasource(fnames_file = vox_dir + '/' + 'fnames.train.awb', 
                               desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                               feat_name = feats_name)
    phi_Y_train = float_datasource(fnames_file = vox_dir + '/' + 'fnames.train.rms', 
                               desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                               feat_name = feats_name)

    feats_name = 'mspec'
    theta_Mel_train = float_datasource(fnames_file = vox_dir + '/' + 'fnames.train.awb', 
                               desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                               feat_name = feats_name)
    phi_Mel_train = float_datasource(fnames_file = vox_dir + '/' + 'fnames.train.rms', 
                               desc_file = vox_dir + '/' + 'etc/falcon_feats.desc', 
                               feat_name = feats_name)
    # Dataset and Dataloader setup
    thetaset = MultispeakerDataset(theta_X_train, theta_spk_train, theta_Mel_train, theta_Y_train)
    phiset = MultispeakerDataset(phi_X_train, phi_spk_train, phi_Mel_train, phi_Y_train)

    theta_loader = data_utils.DataLoader(
        thetaset, batch_size=hparams.batch_size,
        num_workers=hparams.num_workers, shuffle=True,
        collate_fn=collate_fn_spk, pin_memory=hparams.pin_memory)

    phi_loader = data_utils.DataLoader(
        phiset, batch_size=hparams.batch_size,
        num_workers=hparams.num_workers, shuffle=True,
        collate_fn=collate_fn_spk, pin_memory=hparams.pin_memory)


    # Model
    model = Tacotron(n_vocab=1+ len(ph_ids),
                     num_spk=2,
                     embedding_dim=256,
                     mel_dim=hparams.num_mels,
                     linear_dim=hparams.num_freq,
                     r=hparams.outputs_per_step,
                     padding_idx=hparams.padding_idx,
                     use_memory_mask=hparams.use_memory_mask,
                     )
    model = model.cuda()

    model_copy = copy.deepcopy(model)

    #model = DataParallelFix(model)
    print(model)
    print(list(model.parameters()))
    for name, module in model.named_children():
        print(name)

    optimizer = optim.Adam(model.parameters(),
                           lr=hparams.initial_learning_rate, betas=(
                               hparams.adam_beta1, hparams.adam_beta2),
                           weight_decay=hparams.weight_decay)
    optimizer_maml = sgd_maml(params = model.parameters(), lr=0.01)

    # Load checkpoint
    if checkpoint_path:
        print("Load checkpoint from: {}".format(checkpoint_path))
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint["state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer"])
        try:
            global_step = checkpoint["global_step"]
            global_epoch = checkpoint["global_epoch"]
        except:
            # TODO
            pass

    # Setup tensorboard logger
    tensorboard_logger.configure(log_path)

    print(hparams_debug_string())

    # Train!
    try:
        train(model, model_copy, theta_loader, phi_loader, optimizer, optimizer_maml,
              init_lr=hparams.initial_learning_rate,
              checkpoint_dir=checkpoint_dir,
              checkpoint_interval=hparams.checkpoint_interval,
              nepochs=hparams.nepochs,
              clip_thresh=hparams.clip_thresh)
    except KeyboardInterrupt:
        save_checkpoint(
            model, optimizer, global_step, checkpoint_dir, global_epoch)

    print("Finished")
    sys.exit(0)


