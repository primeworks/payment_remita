# -*- coding: utf-8 -*-
try:
    import simplejson as json
except ImportError:
    import json

import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class RemitaController(http.Controller):
    _return_url = '/payment/remita/return'
    _cancel_url = '/payment/remita/cancel'
    _exception_url = '/payment/remita/error'
    _reject_url = '/payment/remita/reject'

    @http.route([
        '/payment/remita/return',
        '/payment/remita/cancel',
        '/payment/remita/error',
        '/payment/remita/reject',
    ], type='http', auth='none')
    def remita_return(self, **post):
        """ Remita."""
        _logger.info('Remita: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'remita', context=request.context)
        return_url = post.pop('return_url', '')
        if not return_url:
            data ='' + post.pop('ADD_RETURNDATA', '{}').replace("'", "\"")
            print data
            custom = json.loads(data)
            return_url = custom.pop('return_url', '/')
        return werkzeug.utils.redirect(return_url)

