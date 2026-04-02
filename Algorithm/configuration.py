import json
import os

class Config_JSON(object):
    def __init__(self,filename = 'config.json'):
        self.configDict = {}
        self.filename = filename
        if os.path.isfile(self.filename):
            with open(filename,'r') as f:
                self.configDict = json.loads(f.read())
                f.close()
    def set(self,key,value):
        self.configDict[key] = value
    def get(self,key):
        if key in self.configDict:
            return self.configDict[key]
        else:
            return None
    def save(self):
        with open(self.filename,'w') as f:
            f.write(json.dumps(self.configDict))
            f.close()