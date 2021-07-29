"""
"""

import os

MOD_PATH, _ = os.path.split(os.path.abspath(__file__))

def get(name):
    """Returns private/public keypair for given service name
    """
    privatePath = MOD_PATH + "/%s.private" % name
    publicPath = MOD_PATH + "/%s.public" % name
    with open(privatePath, 'r') as f:
        privateKey = f.read().strip()
    with open(publicPath, 'r') as f:
        publicKey = f.read().strip()
    return privateKey, publicKey
