from odoo import fields, models


class EcoChallenge(models.Model):
    _name = 'eco.challenge'
    _description = 'EcoSphere Challenge'

    name = fields.Char(required=True)
    description = fields.Text()
    start_date = fields.Date()
    end_date = fields.Date()
    active = fields.Boolean(default=True)
