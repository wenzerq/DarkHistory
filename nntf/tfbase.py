""" Base classes for Neural Network transfer functions (NNTFs).
"""

import numpy as np
from tensorflow import keras

import sys
sys.path.append('..')

from config import load_data
from darkhistory.spec.spectrum import Spectrum
from darkhistory.spec.transferfunction import TransFuncAtRedshift

from nntf.utils import *


class TFBase:
    """ Transfer functions with action base class.
    
    Methods
    --------
    __call__ : Returns :class:`.Spectrum` when acting on :class:`.Spectrum`
    
    TransFuncAtRedshift : Returns :class:`.TransFuncAtRedshift` instance.
    """
    
    def __init__(self):
        self.abscs = [None, None] # set during init
        self.TF_shape = None      # set during init
        self.spec_type = None     # set during init
        self.rs = None # set during predict_TF
        self.TF = None # set during predict_TF
    
    def __call__(self, in_spec):
        """ Action on a Spectrum object. Requires self.TF, self.abscs,
        self.rs, and self.spec_type to be set. """
        if self.TF is None:
            raise ValueError('Run predict_TF first!')
        if self.spec_type == 'N':
            return Spectrum(
                self.abscs[1], np.dot(in_spec.N, self.TF),
                rs=self.rs, spec_type='N'
            )
        elif self.spec_type == 'dNdE':
            return Spectrum(
                self.abscs[1], np.dot(in_spec.dNdE, self.TF),
                rs=self.rs, spec_type='dNdE'
            )
    
    def TransFuncAtRedshift(self):
        """ Get TransFuncAtRedshift instance. Requires self.TF, self.abscs,
        self.rs, and self.spec_type to be set. """
        if self.TF is None:
            raise ValueError('Run predict_TF first!')
        return TransFuncAtRedshift(
            self.TF, in_eng=self.abscs[0], eng=self.abscs[1],
            rs=self.rs, spec_type=self.spec_type, with_interp_func=True
        )
    
        
class NNTFBase (TFBase):
    """ Neural Network transfer function (NNTF) base class. """
    
    def __init__(self, model_dir, TF_type):
        
        super().__init__()
        self.model = keras.models.load_model(model_dir)
        self.TF_type = TF_type
        self._init_helpers()   # define helpers
        self._init_abscs()     # define self.abscs
        self._init_spec_type() # define self.spec_type
        self.TF_shape = (len(self.abscs[0]), len(self.abscs[1]))
        self.io_abscs = np.log(self.abscs)
        
        self._init_mask()    # define self.mask (same for all of (rs, xH, xHe))
        self._pred_in_2D = []
        for ii in range(self.TF_shape[0]):
            for oi in range(self.TF_shape[1]):
                if self.mask[ii][oi]:
                    self._pred_in_2D.append( [self.io_abscs[0][ii], self.io_abscs[1][oi]] )
        self._pred_in_2D = np.array(self._pred_in_2D, dtype=np.float32)
        
    def _init_helpers(self):
        pass
        
    def _init_abscs(self):
        self.abscs = None
        
    def _init_spec_type(self):
        self.spec_type = None
        
    def _init_mask(self):
        self.mask = np.zeros(self.TF_shape)
        
        
    def predict_TF(self, **params):
        """ Core prediction function. Expect kwargs from rs, xH, xHe, E_arr depending on usage. """
        
        self.rs = params['rs']
        self._set_pred_in(**params)
        if len(self.pred_in) > 1e6:
            pred_out = self.model.predict(self.pred_in, batch_size=1e6)
        else:
            pred_out = self.model.predict_on_batch(self.pred_in)
        pred_out = np.array(pred_out).flatten()
        
        raw_TF = np.full(self.TF_shape, LOG_EPSILON)
        pred_out_i = 0
        for ii in range(self.TF_shape[0]):
            for oi in range(self.TF_shape[1]):
                if self.mask[ii][oi]:
                    raw_TF[ii][oi] = pred_out[pred_out_i]
                    pred_out_i += 1
        self.TF = np.exp(raw_TF)
        self._postprocess_TF(**params)
    
    def _set_pred_in(self, **params):
        self.pred_in = None
        
    def _postprocess_TF(self, **params):
        pass