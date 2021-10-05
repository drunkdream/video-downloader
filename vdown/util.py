# -*- coding: utf-8 -*-

"""
"""

import logging
import os

from Crypto.Cipher import AES

logger = logging.getLogger("vdown")
handler = logging.StreamHandler()
logger.addHandler(handler)


def aes_decode(data, key):
    """AES解密
    :param key:  密钥（16.32）一般16的倍数
    :param data:  要解密的数据
    :return:  处理好的数据
    """
    cryptor = AES.new(key, AES.MODE_CBC, key)
    plain_text = cryptor.decrypt(data)
    return plain_text.rstrip(b"\0")


def merge_files(file_list, save_path):
    with open(save_path, "wb") as fp:
        for path in file_list:
            if not os.path.exists(path):
                logger.warn("File %s not exist" % path)
                break
            with open(path, "rb") as fp_r:
                content = fp_r.read()
                fp.write(content)
