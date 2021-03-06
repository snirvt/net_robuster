from copy import deepcopy
import re
import torch
from torch import tensor,Tensor

from deap_utils import save_activation_location, replace_model_activations, activation_module, DyanmicNameActivationClass
from deap_utils import replace_model_activations_2

from deap_net import get_model_performance, network_score

import random

class DeapEvolution():
    def __init__(self, model, pset, train_dataloader, validation_dataloader,epsilon=0.2):
        self.model = model
        self.pset = pset
        self.train_dataloader = train_dataloader
        self.validation_dataloader = validation_dataloader
        self.epsilon = epsilon

    def set_model(self, model):
        self.model = model

    def update_model_AF(self, layer_dict, AF, mapper_s):
        # AF_module = activation_module(AF)

        # str_ind = str(AF)
        # func, code, lambda_str_code = self.get_fixed_terminal_lambda(str_ind)
        # AF_module = activation_module(func, code, lambda_str_code)
        DNAC = DyanmicNameActivationClass('temp_name')
        DNAC.__name__ = str(AF)
        AF_module = DNAC(AF)
        replace_model_activations_2(layer_dict, AF_module, mapper_s)


    def get_fixed_terminal_lambda(self,code):
        # p = '[-]?[\d]+[.,\d]+|[-]?[\d]*[.][\d]+|[-]?[\d]+'
        p = '[-]?[\d]*[.][\d]+|[-]?[\d]+'
        alterd_code = deepcopy(code)
        if re.search(p, alterd_code) is not None:
            for catch in reversed(list(re.finditer(p, alterd_code))):
                # print(catch[0]) # catch is a match object
                alterd_code = alterd_code[:catch.start()]  + 'repeat(' + alterd_code[catch.start():catch.end()]  + ',x)' + alterd_code[catch.end():]

        args = ",".join(arg for arg in self.pset.arguments)
        lambda_str_code = "lambda {args}: {code}".format(args=args, code=alterd_code)
        self.pset.context['repeat'] = lambda scalar, x: Tensor([scalar]).repeat(x.shape) # every terminal will be reshaped to x
        return eval(lambda_str_code, self.pset.context, {}), code, lambda_str_code



    def train_neural_network(self, net, epsilon):
        try:
            # loss, _ = get_model_performance(temp_model, self.train_dataloader, sample_size=256)
            loss, acc = network_score(net = net, train_loader = self.train_dataloader,
             val_loader = self.validation_dataloader, epsilon=epsilon, sample_size=256)
        except:
            print('exception in train_neural_network')
            return torch.tensor([float('inf')])
        return loss

    def evaluate_AF_coop(self, model, individual, mapper_s, debug = False):
        # global model
        temp_model = deepcopy(model)
        temp_layer_dict = {}
        save_activation_location(temp_model, temp_layer_dict)
        # func = toolbox.compile(expr=individual)
        str_ind = str(individual)
        if 'x' not in str_ind:
            print('no x in individual')
            return (float('inf'),), temp_model 

        func, code, lambda_str_code = self.get_fixed_terminal_lambda(str_ind)
        # func_module = activation_module(func, code, lambda_str_code)
        DNAC = DyanmicNameActivationClass('temp_name')
        DNAC.__name__ = str(individual)
        func_module = DNAC(func)

        replace_model_activations_2(temp_layer_dict, func_module, mapper_s)
        # if len(best_coop) > 0:
        #     print('hello')
        # replace_model_activations_2(temp_layer_dict, func_module, mapper_s)
        if debug:
            return (random.random(),), temp_model
        print(str_ind)
        loss = self.train_neural_network(temp_model, self.epsilon)
        return (loss,), temp_model



    def evaluate_AF_single_restart(self,individual):
        # global model
        temp_model = deepcopy(self.model)
        temp_layer_dict = {}
        save_activation_location(temp_model, temp_layer_dict)
        # func = toolbox.compile(expr=individual)
        str_ind = str(individual)
        if 'x' not in str_ind:
            print('no x in individual')
            return torch.tensor([float('inf')])


        func, lambda_str_code = self.get_fixed_terminal_lambda(str_ind)
        func_module = activation_module(func)

        replace_model_activations(temp_layer_dict, [func_module]*len(temp_layer_dict), range(len(temp_layer_dict)))
        print(str_ind)
        loss = self.train_neural_network(temp_model)
        return (loss,)

