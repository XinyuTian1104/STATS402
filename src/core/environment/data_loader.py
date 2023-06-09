import os

import numpy as np
import pandas as pd
import torch
from PIL import Image

FEATURE_TS_LEN = 16


class DataLoader(object):
    def __init__(self, data_path='/Users/crinstaniev/Courses/STATS402/data', train=False):
        train_data_path = os.path.join(data_path, 'train_data')
        test_data_path = os.path.join(data_path, 'test_data')

        if train:
            self.data_path = train_data_path
        else:
            self.data_path = test_data_path

        # calculate number of collections
        self.num_collections = len(os.listdir(self.data_path))
        self.collection_names = os.listdir(self.data_path)
        
        self.time_series_buffer = None
        self.feature_buffer = None
        self.current_collection_id = None
        
        self.current_timestep = FEATURE_TS_LEN
        
        self.reload_flag = True
        
        # remove .DS_Store
        if '.DS_Store' in self.collection_names:
            self.collection_names.remove('.DS_Store')
            self.num_collections -= 1
            
    def _get_timeseries_length(self):
        return len(self.time_series_buffer)
            
    def bump_timestep(self):
        self.current_timestep += 1
        # print('current timestep:', self.current_timestep)
        # print('timeseries length:', self._get_timeseries_length())
        # print('current collection id:', self.current_collection_id)
        if self.current_timestep >= self._get_timeseries_length() - 1:
            self.current_timestep = FEATURE_TS_LEN
            self.current_collection_id += 1
            self.reload_flag = True
            return True
        return False
        
    def load_collection_features(self, collection_id):
        self._flush(collection_id)
        
        if self.feature_buffer is None:
            collection_name = self._collection_id_to_name(collection_id)
            collection_path = os.path.join(self.data_path, collection_name)
            
            # load description.txt
            description_path = os.path.join(collection_path, 'description.txt')
            with open(description_path, 'r') as f:
                description = f.read()
            
            # load image with RGB channels
            image_path = os.path.join(collection_path, 'image.png')
            image = Image.open(image_path).convert('RGB')
            image = np.array(image) # convert to numpy array
    
            # stretch image to 224x224
            image = np.array(Image.fromarray(image).resize((224, 224)))
            
            # convert to tensor with shape (1, channels, height, width)
            image = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0).type(torch.float32)
            
            # load time_series.json with pandas
            ts_payload = np.zeros((1, FEATURE_TS_LEN, 5), dtype=np.float32)
            for i in range(FEATURE_TS_LEN):
                payload = self.load_time_series(collection_id, i)
                for j in range(5):
                    ts_payload[0, i, j] = payload[j]
                
            # convert to tensor with shape (1, timesteps, num_features)
            time_series = torch.from_numpy(ts_payload).type(torch.float32)
            
            self.feature_buffer = (description, image, time_series)
        
        return self.feature_buffer
    
    def load_time_series(self, collection_id, timestep=None):
        self._flush(collection_id)
            
        if timestep is not None:
            payload = self.time_series_buffer.iloc[timestep]
            payload = payload[['floorEth', 'floorUsd', 'salesCount', 'volumeEth', 'volumeUsd']]
            payload = payload.to_numpy()
            return payload
        
        payloads = np.zeros((FEATURE_TS_LEN, 5), dtype=np.float32)
        for i in range(self.current_timestep, self.current_timestep - FEATURE_TS_LEN, -1):
            payload = self.time_series_buffer.iloc[i]
            payload = payload[['floorEth', 'floorUsd', 'salesCount', 'volumeEth', 'volumeUsd']]
            payload = payload.to_numpy().astype(np.float32)
            payloads[self.current_timestep - i] = payload
        payloads = payloads.astype(np.float32)
        payloads = torch.from_numpy(payloads).type(torch.float32).unsqueeze(0)
        
        done = self.bump_timestep()
        
        return payloads, done
        
    
    def _collection_id_to_name(self, collection_id):
        return self.collection_names[collection_id]
    
    def _flush(self, collection_id):
        if self.current_collection_id is None \
            or collection_id != self.current_collection_id \
                or self.current_timestep == FEATURE_TS_LEN:
            self.time_series_buffer = None
            self.feature_buffer = None
            self.current_collection_id = collection_id
            self.reload_flag = True
        
        if self.reload_flag: 
            self.current_collection_id = collection_id
            collection_name = self._collection_id_to_name(collection_id)
            collection_path = os.path.join(self.data_path, collection_name)  
                
            # load time_series.json with pandas
            time_series_path = os.path.join(collection_path, 'time_series.json')
            time_series = pd.read_json(time_series_path)
            self.time_series_buffer = time_series
            
            self.reload_flag = False
        return
    
    def __len__(self):
        return self.num_collections
            
        
            