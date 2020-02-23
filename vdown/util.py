# -*- coding: utf-8 -*-

'''
'''

import logging

logger = logging.getLogger('vdown')
handler = logging.StreamHandler()
logger.addHandler(handler)


def merge_files(file_list, save_path):
    with open(save_path, 'wb') as fp:
        for path in file_list:
            with open(path, 'rb') as fp_r:
                content = fp_r.read()
                fp.write(content)
