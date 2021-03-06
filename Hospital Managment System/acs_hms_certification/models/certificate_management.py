# -*- encoding: utf-8 -*-

import babel
import base64
import copy
import datetime
import dateutil.relativedelta as relativedelta
import logging

import functools
import lxml
from werkzeug import urls

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools import pycompat

from odoo.tools.safe_eval import safe_eval
import dateutil.relativedelta as relativedelta


try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
    mako_safe_template_env = copy.copy(mako_template_env)
    mako_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")



 
class CertificateTag(models.Model):
    _name = "certificate.tag"
    _description = "Certificate Tags"

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class CertificateManagement(models.Model):
    _name = 'certificate.management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Certificate Management'

    name = fields.Char(string='Sequence', required=True, readonly=True, default='New', copy=False)
    patient_id = fields.Many2one('hms.patient', string='Patient', ondelete="restrict", 
        help="Patient whose certificate to be attached", 
        states={'done': [('readonly', True)]})
    physician_id = fields.Many2one('hms.physician',string='Doctor', ondelete="restrict", 
        help="Doctor ho provided certificate with the patient", 
        states={'done': [('readonly', True)]})
    date = fields.Date('Date', readonly="True", default=fields.Date.today, 
        states={'done': [('readonly', True)]})
    certificate_content = fields.Html('Certificate Content', 
        states={'done': [('readonly', True)]})
    state = fields.Selection([
            ('draft','Draft'),
            ('done','Done')
        ], 'Status', default="draft", track_visibility='onchange', 
        states={'done': [('readonly', True)]}) 
    template_id = fields.Many2one('certificate.template', string="Certificate Template", ondelete="restrict", 
        states={'done': [('readonly', True)]})
    tag_ids = fields.Many2many('certificate.tag', 'certificate_tag_rel', 'certificate_id', 'tag_id', 
        string='Tags', help="Classify and analyze your Certificates", 
        states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company',default=lambda self: self.env.user.company_id.id) 


    @api.multi
    def action_done(self):
        self.name = self.env['ir.sequence'].next_by_code('certificate.management')
        self.state = 'done'

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id:
            mako_env = mako_safe_template_env #if self.env.context.get('safe') else mako_template_env
            template = mako_env.from_string(tools.ustr(self.template_id.certificate_content))

            variables = {
                'format_date': lambda date, format=False, context=self._context: format_date(self.env, date, format),
                'format_tz': lambda dt, tz=False, format=False, context=self._context: format_tz(self.env, dt, tz, format),
                'format_amount': lambda amount, currency, context=self._context: format_amount(self.env, amount, currency),
                'user': self.env.user,
                'ctx': self._context,  # context kw would clash with mako internals
            }

            variables['object'] = self
            self.certificate_content = template.render(variables)

    @api.multi
    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can only delete in draft'))
        return super(CertificateManagement, self).unlink()


class CertificateTemplate(models.Model):
    _name = 'certificate.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Certificate Template'

    name = fields.Char("Template")
    certificate_content = fields.Html('Certificate Content')


class ACSPatient(models.Model):
    _inherit = 'hms.patient' 

    @api.multi
    def action_open_certificate(self):
        action = self.env.ref('acs_hms_certification.action_certificate_management').read()[0]
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id}
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: