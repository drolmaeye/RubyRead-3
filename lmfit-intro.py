from lmfit.models import LinearModel, PseudoVoigtModel
import numpy as np

r1 = PseudoVoigtModel(prefix='r1_')
r2 = PseudoVoigtModel(prefix='r2_')
bg = LinearModel()

ruby_fit = r1 + r2 + bg

print(ruby_fit, ruby_fit.param_names)


