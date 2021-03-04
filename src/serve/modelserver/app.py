import io
import json

import numpy as np
import torch
from flask import Flask, Response, jsonify, request, send_file
from PIL import Image

from src.models.utils import model_setup
from src.models.utils.configuration import AttrDict

#import zlib


app = Flask(__name__)

### load models into memory
channel_configuration_name = 'all'
inference_funcs = {}

for model_name in ['linear','unet','simplecnn']:
    opt = {
        'model': model_name,
        'device': 'cpu',
        'model_folder': f'src/models/checkpoints/{model_name}/', # TODO different channel configuration means different model
        'max_tile_size': 256,
        'num_class': 3,
        'channel_configuration' : channel_configuration_name,
        'num_channels': len(model_setup.CHANNELS_CONFIGURATIONS[channel_configuration_name]),
    }
    opt = AttrDict.from_nested_dicts(opt)
    inference_funcs[model_name] = model_setup.model_inference_fun(opt)
    
N_CHANNELS = len(model_setup.CHANNELS_CONFIGURATIONS[opt.channel_configuration])


def get_prediction(image_bytes,model):
    arr = np.frombuffer(image_bytes, dtype=np.float32).reshape(N_CHANNELS,256,256)
    tensor = torch.Tensor(arr).unsqueeze(0)
    Y_h = inference_funcs[model](tensor)
    return torch.argmax(Y_h,dim=1).squeeze().numpy().astype(np.uint8)


@app.route("/")
def hello():
    """ A <hello world> route to test server functionality. """
    return "Hello World ModelServer!"


@app.route('/<model>/predict', methods=['POST'])
def predict(model):
    print ('predict',model)
    if request.method == 'POST':
        data = request.data
        Y_h = get_prediction(image_bytes=data,model=model)
        
        ### this works!
        #buf = io.BytesIO()
        #np.save(buf, Y_h)
        #buf.seek(0)
        
        ### let's try encrypting
        buf = io.BytesIO()
        np.savez_compressed(buf, Y_h=Y_h)
        buf.seek(0)
        
    
        return send_file(
                buf,
                as_attachment = True,
                attachment_filename = f'arr.npz',
                mimetype = 'application/octet_stream'
            )


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)