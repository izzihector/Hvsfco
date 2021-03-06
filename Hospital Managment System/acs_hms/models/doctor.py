# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PhysicianSpecialty(models.Model):
    _name = 'physician.specialty'
    _description = "Physician Specialty"

    code = fields.Char(string='Code')
    name = fields.Char(string='Specialty', required=True, translate=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class PhysicianDegree(models.Model):
    _name = 'physician.degree'
    _description = "Physician Degree"

    name = fields.Char(string='Degree')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!'),
    ]


class Physician(models.Model):
    _name = 'hms.physician'
    _description = "Physician"
    _inherits = {'res.users': 'user_id'}

    user_id = fields.Many2one('res.users',string='Related User', required=True,
        ondelete='cascade', help='User-related data of the physician')
    code = fields.Char(string='Physician ID', default='/')
    degree_ids = fields.Many2many('physician.degree', 'physician_rel_education', 'physician_ids','degree_ids', string='Degree')
    specialty = fields.Many2one('physician.specialty', ondelete='set null', string='Specialty', help='Specialty Code')
    government_id = fields.Char(string='Government ID')
    website = fields.Char(string='Website')
    consul_service = fields.Many2one('product.product', ondelete='restrict', string='Consultation Service')
    followup_service = fields.Many2one('product.product', ondelete='restrict', string='Followup Service')
    is_primary_surgeon = fields.Boolean(string='Primary Surgeon')
    is_consultation_doctor = fields.Boolean(string='Consultation Physician')
    signature = fields.Binary('Signature')

    @api.model
    def create(self, values):
        if values.get('code','/') == '/':
            values['code'] = self.env['ir.sequence'].next_by_code('hms.physician')
        values['login'] = values['email']
        return super(Physician, self).create(values)