import math
import torch
from torch import nn

class ScaleW:
    """
    Scale the weight of the module by a constant factor.
    """
    def __init__(self, name):
        self.name = name
    
    def scale(self, module):
        weight = getattr(module, self.name + '_orig')
        fan_in = weight.data.size(1) * weight.data[0][0].numel()
        
        return weight * math.sqrt(2 / fan_in)
    
    @staticmethod
    def apply(module, name):
        '''
        Apply runtime scaling to specific module
        '''
        hook = ScaleW(name)
        weight = getattr(module, name)
        module.register_parameter(name + '_orig', nn.Parameter(weight.data))
        del module._parameters[name]
        module.register_forward_pre_hook(hook)
    
    def __call__(self, module, whatever):
        weight = self.scale(module)
        setattr(module, self.name, weight)

def scale_module(module, name='weight'):
    ScaleW.apply(module, name)
    return module

class SLinear(nn.Module):
    """Scaled Linear layer."""
    def __init__(self, dim_in, dim_out):
        super().__init__()

        linear = nn.Linear(dim_in, dim_out)
        linear.weight.data.normal_()
        linear.bias.data.zero_()
        
        self.linear = scale_module(linear)

    def forward(self, x):
        return self.linear(x)

class SConv2d(nn.Module):
    """Scaled Conv2d layer."""
    def __init__(self, *args, **kwargs):
        super().__init__()

        conv = nn.Conv2d(*args, **kwargs)
        conv.weight.data.normal_()
        conv.bias.data.zero_()
        
        self.conv = scale_module(conv)

    def forward(self, x):
        return self.conv(x)


class PixelNorm(nn.Module):
    """Pixelwise feature vector normalization."""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return x * torch.rsqrt(torch.mean(x ** 2, dim=1, keepdim=True) + 1e-8)
    

class FC_A(nn.Module):
    '''
    Learned affine transform "A" to transform the latent vector w into a style vector y
    '''
    def __init__(self, dim_latent, n_channel):
        super().__init__()
        self.transform = SLinear(dim_latent, n_channel * 2)
        # "the biases associated with ys that we initialize to one"
        self.transform.linear.bias.data[:n_channel] = 1
        self.transform.linear.bias.data[n_channel:] = 0

    def forward(self, w):
        # Gain scale factor and bias with:
        style = self.transform(w).unsqueeze(2).unsqueeze(3)
        return style
    
class AdaIN(nn.Module):
    """
    Adaptive instance normalization layer.
    
    Parameters:
    ----------
    n_channel : int
        Number of input channels.
    """
    def __init__(self, n_channel):
        super().__init__()
        self.norm = nn.InstanceNorm2d(n_channel)
        
    def forward(self, image, style):
        factor, bias = style.chunk(2, 1)
        result = self.norm(image)
        result = result * factor + bias  
        return result


class Scale_B(nn.Module):
    def __init__(self, n_channel):
        super().__init__()
        self.weight = nn.Parameter(torch.zeros((1, n_channel, 1, 1)))
    
    def forward(self, noise):
        result = noise * self.weight
        return result 

    
def compute_gradient_penalty(D, real_samples, fake_samples, level, alpha, device):
    """Calculates the gradient penalty loss for WGAN GP"""
    batch_size = real_samples.shape[0]

    # generate random epsilon
    epsilon = torch.rand((batch_size, 1, 1, 1)).to(device)

    # create the merge of both real and fake samples
    merged = epsilon * real_samples + ((1 - epsilon) * fake_samples)
    merged.requires_grad_(True)

    # forward pass
    op = D(merged, level, alpha)

    # perform backward pass from op to merged for obtaining the gradients
    gradient = torch.autograd.grad(
        outputs=op,
        inputs=merged,
        grad_outputs=torch.ones_like(op),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]

    gradient = gradient.view(gradient.shape[0], -1)

    return ((gradient.norm(p=2, dim=1) - 1) ** 2).mean()
