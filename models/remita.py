# -*- coding: utf-'8' "-*-"
from hashlib import sha1
from hashlib import sha512
#import hashlib
import logging
import urlparse
import urllib2
import json
from time import gmtime, strftime

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_remita.controllers.main import RemitaController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class AcquirerRemita(osv.Model):
    _inherit = 'payment.acquirer'
    merchantID = 0
    apikey = 0

    def _get_remita_urls(self, cr, uid, environment, context=None):
        """ Remita URLs
        """
        if environment == 'prod':
            return {
                'remita_form_url': 'https://login.remita.net/remita/ecomm/init.reg',
            }
        else:
            return {
                'remita_form_url': 'http://www.remitademo.net/remita/ecomm/init.reg',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerRemita, self)._get_providers(cr, uid, context=context)
        providers.append(['remita', 'Remita'])
        return providers

    _columns = {
        'brq_websitekey': fields.char('Merchant ID', required_if_provider='remita'),
        'brq_secretkey': fields.char('API Key', required_if_provider='remita'),
        'brq_servicetypeid': fields.char('Service Type ID', required_if_provider='remita'),
    }

    def _remita_generate_digital_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shakey out
        :param string inout: 'in' (openerp contacting remita) or 'out' (remita
                             contacting openerp).
        :param dict values: transaction values

        :return string: shasign
        """
    

        assert inout in ('in', 'out')
        assert acquirer.provider == 'remita'

        keys = "add_returndata Brq_amount Brq_culture Brq_currency Brq_invoicenumber Brq_return Brq_returncancel Brq_returnerror Brq_returnreject brq_test Brq_websitekey".split()

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        values = dict(values or {})

        if inout == 'out':
            if 'BRQ_SIGNATURE' in values:
                del values['BRQ_SIGNATURE']
            items = sorted((k.upper(), v) for k, v in values.items())
            sign = ''.join('%s=%s' % (k, v) for k, v in items)
        else:
            sign = ''.join('%s=%s' % (k,get_value(k)) for k in keys)
        #Add the pre-shared secret key at the end of the signature
        sign = sign + acquirer.brq_secretkey
        if isinstance(sign, str):
            sign = urlparse.parse_qsl(sign)
        shasign = sha1(sign).hexdigest()
        
        s2 = ""
        seq2 = (str(acquirer.brq_servicetypeid), str(acquirer.brq_secretkey), str(acquirer.brq_websitekey))
        
        hash_object2 = sha512(s2.join(seq2))
        
        hex_dig2 = hash_object2.hexdigest()
        shasign = hex_dig2
        return shasign


    def remita_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)
        
        #print "{'return_url': '%s'}"% tx_values['return_url']
        #ret_url = "{'return_url': '%s'}"% tx_values['return_url']
        #ret_url2 = "{'return_url': '%s'}"% urlparse.urljoin(base_url, RemitaController._return_url)
        ret_url3 = urlparse.urljoin(base_url, RemitaController._return_url)
        #print ret_url
        s = ""
        seq = (str(acquirer.brq_websitekey), acquirer.brq_servicetypeid, str(tx_values['reference']), str(tx_values['amount']), ret_url3, str(acquirer.brq_secretkey));
        print s.join(seq)
        #print dict.keys(tx_values)
        
        
        AcquirerRemita.merchantID = acquirer.brq_websitekey
        
        AcquirerRemita.apikey = acquirer.brq_secretkey
        
        hash_object = sha512(s.join(seq))
        hex_dig = hash_object.hexdigest()
        #print(hex_dig)
        
        #hashd = sha512(str(25479164430731SO0022320.0{'return_url': '/shop/payment/validate'}1946))
        #print hashd
        
        hash = hex_dig
        #print hash
        #print tx_values

        remita_tx_values = dict(tx_values)
        remita_tx_values.update({
            'Brq_websitekey': acquirer.brq_websitekey,
            'Brq_hash': hash,
            'Brq_api': acquirer.brq_secretkey,
            'Brq_servicetype': acquirer.brq_servicetypeid,
            'Brq_amount': tx_values['amount'],
            'Brq_currency': tx_values['currency'] and tx_values['currency'].name or '',
            'Brq_invoicenumber': tx_values['reference'],
            'brq_test': False if acquirer.environment == 'prod' else True,
           #'Brq_return': '%s' % ret_url,
            'Brq_return': '%s' % urlparse.urljoin(base_url, RemitaController._return_url),
            'Brq_returncancel': '%s' % urlparse.urljoin(base_url, RemitaController._cancel_url),
            'Brq_returnerror': '%s' % urlparse.urljoin(base_url, RemitaController._exception_url),
            'Brq_returnreject': '%s' % urlparse.urljoin(base_url, RemitaController._reject_url),
            'Brq_culture': (partner_values.get('lang') or 'en_US').replace('_', '-'),
        })
        print remita_tx_values
        #print remita_tx_values.get('return_url')
        if remita_tx_values.get('return_url'):
            remita_tx_values['add_returndata'] = {'return_url': '%s' % remita_tx_values.pop('return_url')}
        else: 
            remita_tx_values['add_returndata'] = ''
        remita_tx_values['Brq_signature'] = self._remita_generate_digital_sign(acquirer, 'in', remita_tx_values)
        return partner_values, remita_tx_values

    def remita_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_remita_urls(cr, uid, acquirer.environment, context=context)['remita_form_url']

class TxRemita(osv.Model):
    _inherit = 'payment.transaction'

    # Remita status
    _remita_valid_tx_status = "01"
    _remita_pending_tx_status = "021"
    _remita_cancel_tx_status = "012"
    _remita_error_tx_status = "02"
    _remita_reject_tx_status = "022"

    _columns = {
         'remita_txnid': fields.char('RRR'),
    }
    

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    def _remita_form_get_tx_from_data(self, cr, uid, data, context=None):
        """ Given a data dict coming from remita, verify it and find the related
        transaction record. """
        #Use RRR to pull in more info from Remita
        #acquirer = self.browse(cr, uid, id, context=context)
        #merchantID = remita_tx_values.get('Brq_websitekey')
        RRR = data.get('RRR')
        #print RRR
        
        orderID = data.get('orderID')
        #print orderID
        
        merchantID2 = AcquirerRemita.merchantID
        apikey2 = AcquirerRemita.apikey
        
        s2 = ""
        seq2 = (str(RRR), str(apikey2), str(merchantID2))

        hash_object2 = sha512(s2.join(seq2))

        hex_dig2 = hash_object2.hexdigest()
        #print hex_dig2
        
        response = urllib2.urlopen('http://www.remitademo.net/remita/ecomm/%s/%s/%s/json/status.reg' % (str(merchantID2), str(RRR), str(hex_dig2)))
        myTx = json.load(response)
        #print myTx
        #print "Hello AA"

#        reference, pay_id, shasign = data.get('memo'), data.get('RRR'), data.get('merchant_ref')
        reference, pay_id, shasign = orderID, data.get('RRR'), hex_dig2
        
        if not reference or not pay_id or not shasign:
            #        if not reference:
            error_msg = 'Remita: received data with missing reference (%s) or pay_id (%s) or shashign (%s)' % (reference, pay_id, shasign)
            _logger.error(error_msg)
            raise ValidationError(error_msg)
#
        tx_ids = self.search(cr, uid, [('reference', '=', reference)], context=context)
        if not pay_id:
            error_msg = 'Remita: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        tx = self.pool['payment.transaction'].browse(cr, uid, tx_ids[0], context=context)

        #verify shasign
#        shasign_check = self.pool['payment.acquirer']._remita_generate_digital_sign(tx.acquirer_id, 'out' ,data)
#        if shasign_check.upper() != shasign.upper():
#            error_msg = 'Remita: invalid shasign, received %s, computed %s, for data %s' % (shasign, shasign_check, data)
#            _logger.error(error_msg)
#            raise ValidationError(error_msg)

        return tx

   
    def _remita_form_validate(self, cr, uid, tx, data, context=None):
        
        #Use RRR to pull in more info from Remita
        RRR = data.get('RRR')
        print RRR
        
        orderID = data.get('orderID')
        print orderID
        
        merchantID2 = AcquirerRemita.merchantID
        apikey2 = AcquirerRemita.apikey
        
        s2 = ""
        seq2 = (str(RRR), str(apikey2), str(merchantID2))
        
        hash_object2 = sha512(s2.join(seq2))
        
        hex_dig2 = hash_object2.hexdigest()
        
        
        response = urllib2.urlopen('http://www.remitademo.net/remita/ecomm/%s/%s/%s/json/status.reg' % (str(merchantID2), str(RRR), str(hex_dig2)))
        myTx = json.load(response)
        print myTx
        #Pull out the confirmations from the RRR
        status_code = myTx['status']
        print status_code
        print str(self._remita_valid_tx_status)
        if status_code in str(self._remita_valid_tx_status):
            #        if data.get('RRR'):
            # Adding more detail to the final form
            _logger.info('Validated Paypal payment for tx %s: set as done' % (orderID))
            tx.write({
                'state': 'done',
                'remita_txnid': data.get('RRR'),
                'date_validate': myTx['transactiontime'],
            })
            return True
        elif status_code in str(self._remita_pending_tx_status):
            tx.write({
                'state': 'pending',
                'remita_txnid': data.get('RRR'),
            })
            return True
        elif status_code in str(self._remita_cancel_tx_status):
            tx.write({
                'state': 'cancel',
                'remita_txnid': data.get('RRR'),
            })
            return True
        else:
            error = 'Remita: feedback error'
            _logger.info(error)
            tx.write({
                'state': 'error',
                'state_message': error,
                'remita_txnid': data.get('RRR'),
            })
            return False
