# -*- coding: utf-8 -*-

import json
import os
import logging

from completor import Completor, vim
from completor.compat import to_unicode
from completor.utils import echo

DIRNAME = os.path.dirname(__file__)
logger = logging.getLogger('completor')


class Jedi(Completor):
    filetype = 'python'
    trigger = (r'\w{3,}$|'
               r'[\w\)\]\}\'\"]+\.\w*$|'
               r'^\s*from\s+[\w\.]*(?:\s+import\s+(?:\w*(?:,\s*)?)*)?|'
               r'^\s*import\s+(?:[\w\.]*(?:,\s*)?)*')

    def _jedi_cmd(self, action):
        binary = self.get_option('python_binary') or 'python'
        cmd = [binary, os.path.join(DIRNAME, 'python_jedi.py')]
        return vim.Dictionary(
            cmd=cmd,
            ftype=self.filetype,
            is_daemon=True,
            is_sync=False,
        )

    def _yapf_cmd(self):
        if vim.current.buffer.options['modified']:
            echo('Save file to format.', severity='warn')
            return vim.Dictionary()
        binary = self.get_option('yapf_binary') or 'yapf'
        line_range = self.meta.get('range')
        if not line_range:
            return vim.Dictionary()
        cmd = [binary, '--in-place']
        start, end = line_range
        if start != end:
            cmd.extend(['--lines', '{}-{}'.format(start, end)])
        cmd.append(self.filename)
        return vim.Dictionary(
            cmd=cmd,
            ftype=self.filetype,
            is_daemon=False,
            is_sync=False,
        )

    def get_cmd_info(self, action):
        if action == b'format':
            return self._yapf_cmd()
        return self._jedi_cmd(action)

    def _is_comment(self):
        data = self.input_data.strip()
        if data.startswith('#'):
            return True

    def prepare_request(self, action):
        if action == b'complete' and self._is_comment():
            return ''
        line, _ = self.cursor
        col = len(self.input_data)
        self.request_emmited = True
        return json.dumps({
            'action': action.decode('ascii'),
            'line': line - 1,
            'col': col,
            'filename': self.filename,
            'input': self.input_data,
            'content': '\n'.join(vim.current.buffer[:])
        }) + '\n'

    def on_definition(self, data):
        return json.loads(to_unicode(data[0], 'utf-8'))

    on_signature = on_definition
    on_doc = on_definition

    def on_complete(self, data):
        return data

    def on_stream(self, action, data):
        try:
            v = json.loads(data)
        except Exception as e:
            logger.exception(e)
            return
        return self.on_data(action, v)
