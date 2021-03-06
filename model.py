import torch
import torch.nn as nn
import os

class ResBlock(nn.Module):
	def __init__(self, n_feats, kernel_size):
		super(ResBlock, self).__init__()

		self.resblock = nn.Sequential()
		self.resblock.add_module('conv_1', nn.Conv2d(n_feats, n_feats, kernel_size, padding=(kernel_size // 2)))
		self.resblock.add_module('relu', nn.ReLU())
		self.resblock.add_module('conv_2', nn.Conv2d(n_feats, n_feats, kernel_size, padding=(kernel_size // 2)))

	def forward(self, x):
		y = self.resblock(x)
		y += x
		return y

class ScaleBody(nn.Module):
	def __init__(self, in_channels, out_channels, n_feats, kernel_size, n_resblocks):
		super(ScaleBody, self).__init__()

		self.body = nn.Sequential()
		self.body.add_module('first_conv', nn.Conv2d(in_channels, n_feats, kernel_size, padding=(kernel_size // 2)))
		for i in range(n_resblocks):
			self.body.add_module('resblock_' + str(i), ResBlock(n_feats, kernel_size))
		self.body.add_module('last_conv', nn.Conv2d(n_feats, out_channels, kernel_size, padding=(kernel_size // 2)))

	def forward(self, x):
		y = self.body(x)
		return y

class Generator(nn.Module):
	def __init__(self, n_resblocks, n_feats, kernel_size, n_scales):
		super(Generator, self).__init__()

		self.n_scales = n_scales

		self.scales = nn.ModuleList([ScaleBody(3, 3, n_feats, kernel_size, n_resblocks)])
		for _ in range(1, self.n_scales):
			self.scales.append(ScaleBody(6, 3, n_feats, kernel_size, n_resblocks))

		self.upscalers = nn.ModuleList([])
		for _ in range(1, self.n_scales):
			self.upscalers.append(nn.Sequential(nn.Conv2d(3, 12, kernel_size, padding=(kernel_size // 2)), nn.PixelShuffle(2)))

	def forward(self, input_pyramid):
		for i in range(len(input_pyramid)):
			input_pyramid[i] -= 127

		output_pyramid = [None] * self.n_scales

		x = input_pyramid[0]
		for i in range(self.n_scales):
			output_pyramid[i] = self.scales[i](x)
			if i+1 < self.n_scales:
				upscaled = self.upscalers[i](output_pyramid[i])
				x = torch.cat((input_pyramid[i+1], upscaled), 1)

		for i in range(len(output_pyramid)):
			output_pyramid[i] = output_pyramid[i] + 127

		return output_pyramid

class Adversary(nn.Module):
	def __init__(self, n_feats, kernel_size):
		super(Adversary, self).__init__()

		self.adv = nn.Sequential(
			nn.Conv2d(3, n_feats//2, kernel_size, stride=1, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats//2, n_feats//2, kernel_size, stride=2, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats//2, n_feats, kernel_size, stride=1, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats, n_feats, kernel_size, stride=2, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats, n_feats*2, kernel_size, stride=1, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*2, n_feats*2, kernel_size, stride=4, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*2, n_feats*4, kernel_size, stride=1, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*4, n_feats*4, kernel_size, stride=4, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*4, n_feats*8, kernel_size, stride=1, padding=(kernel_size-1)//2, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*8, n_feats*8, 4, stride=4, padding=0, bias=False),
			nn.LeakyReLU(negative_slope=0.2),
			nn.Conv2d(n_feats*8, 1, 1, bias=False)
		)

	def forward(self, x):
		y = self.adv(x)
		return y